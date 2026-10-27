# Datas de sintoma/notificação muito próximas num grupo QI -> provável
# duplicata da mesma pessoa; se o grupo é homogêneo no sensível, o valor
# vaza com alta confiança. Inconsistência de óbito (sempre EVOLUCAO): ver
# "criterios" em montar_resumo_inconsistencia.
import sys
from pathlib import Path
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.homogeneidade.definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR, get_input_path,
        ATAQUE_CONFIANCA_PATH, ATAQUE_INCONSISTENCIA_PATH, RESUMO_ATAQUE_CONFIANCA_PATH,
        carregar_csv, normalizar, montar_chave_qi,
    )
    from src.utils.comum import exportar_xlsx
    from src.nucleo import THRESHOLDS_DT_SIN, THRESHOLDS_DT_NOTIFIC
else:
    from .definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR, get_input_path,
        ATAQUE_CONFIANCA_PATH, ATAQUE_INCONSISTENCIA_PATH, RESUMO_ATAQUE_CONFIANCA_PATH,
        carregar_csv, normalizar, montar_chave_qi,
    )
    from src.utils.comum import exportar_xlsx
    from src.nucleo import THRESHOLDS_DT_SIN, THRESHOLDS_DT_NOTIFIC


def _checar_homogeneidade_sensivel(df: pd.DataFrame, sensivel_col: str) -> pd.DataFrame:
    df = normalizar(df.copy())
    df["chave_qi"] = montar_chave_qi(df)

    grupo_sensivel = df.groupby("chave_qi")[sensivel_col]
    grupo_tem_nulo = df[sensivel_col].isna().groupby(df["chave_qi"]).transform("any")
    grupo_distintos = grupo_sensivel.transform("nunique")
    grupo_unico = grupo_sensivel.transform("first")

    df["homogeneo"] = (~grupo_tem_nulo) & (grupo_distintos == 1)
    df["valor_sensivel_unico"] = grupo_unico
    return df


def executar_ataque_confianca(df: pd.DataFrame, sensivel_col: str) -> pd.DataFrame:
    # Vulnerável se confianca_mesma_pessoa == "alta" E o atributo sensível
    # é homogêneo no grupo.
    if "confianca_mesma_pessoa" not in df.columns:
        raise ValueError(
            "Coluna 'confianca_mesma_pessoa' ausente. "
            "Execute k_anonimato.py primeiro para gerar o arquivo de entrada."
        )
    if sensivel_col not in df.columns:
        raise ValueError(f"Coluna {sensivel_col} nao encontrada.")

    df = _checar_homogeneidade_sensivel(df, sensivel_col)
    mask = (df["confianca_mesma_pessoa"] == "alta") & df["homogeneo"]
    df_vulneravel = df[mask].copy()
    df_vulneravel["tipo_ataque"] = "confianca_temporal_homogeneidade"
    df_vulneravel.insert(0, "atributo_sensivel", sensivel_col)
    return df_vulneravel


def executar_ataque_inconsistencia(df: pd.DataFrame) -> pd.DataFrame:
    # Registros com inconsistência de óbito (ver cabeçalho do módulo).
    if "inconsistente_obito" not in df.columns:
        raise ValueError(
            "Coluna 'inconsistente_obito' ausente. "
            "Execute k_anonimato.py primeiro para gerar o arquivo de entrada."
        )

    mask = df["inconsistente_obito"].astype(str).str.lower().isin(["true", "1"])
    df_inc = df[mask].copy()
    df_inc = normalizar(df_inc)
    df_inc["chave_qi"] = montar_chave_qi(df_inc)
    df_inc["tipo_ataque"] = "inconsistencia_obito"
    return df_inc


def montar_resumo_confianca_atributo(df_confianca_attr: pd.DataFrame, sensivel_col: str) -> dict:
    n = int(len(df_confianca_attr))

    if n:
        grupos = int(df_confianca_attr["chave_qi"].nunique())
    else:
        grupos = 0

    dist = {}
    if n and "valor_sensivel_unico" in df_confianca_attr.columns:
        dist = {
            str(v): int(c)
            for v, c in df_confianca_attr["valor_sensivel_unico"].value_counts().to_dict().items()
        }
    return {
        "atributo_sensivel": sensivel_col,
        "registros_vulneraveis": n,
        "grupos_vulneraveis": grupos,
        "distribuicao_valor_sensivel_revelado": dist,
    }


def montar_resumo_inconsistencia(df_inconsistencia: pd.DataFrame) -> dict:
    n = int(len(df_inconsistencia))

    if n:
        grupos = int(df_inconsistencia["chave_qi"].nunique())
    else:
        grupos = 0

    dist = {}
    if n and "EVOLUCAO" in df_inconsistencia.columns:
        dist = {
            str(ev): int(v)
            for ev, v in df_inconsistencia["EVOLUCAO"].value_counts().to_dict().items()
        }

    n_posterior = n_conflito = n_ambos = 0
    if n and "posterior_a_obito" in df_inconsistencia.columns and "conflito_obito_grupo" in df_inconsistencia.columns:
        mask_pos = df_inconsistencia["posterior_a_obito"].astype(str).str.lower().isin(["true", "1"])
        mask_conf = df_inconsistencia["conflito_obito_grupo"].astype(str).str.lower().isin(["true", "1"])
        n_posterior = int(mask_pos.sum())
        n_conflito = int(mask_conf.sum())
        n_ambos = int((mask_pos & mask_conf).sum())

    return {
        "descricao": (
            "Registros com inconsistencia de obito: o proprio registro sendo posterior "
            "a um obito do seu grupo (posterior_a_obito, por registro — prova de pessoa "
            "diferente do obito), ou o grupo ter causas de obito conflitantes "
            "(conflito_obito_grupo, por grupo). Esses padroes revelam informacao sobre "
            "o desfecho indiretamente. Sempre calculado sobre EVOLUCAO, independente do "
            "atributo sensivel avaliado."
        ),
        "criterios": {
            "posterior_a_obito": "DT_NOTIFIC do registro > min(DT_NOTIFIC onde EVOLUCAO in {2,3} no grupo) — por registro",
            "conflito_obito_grupo": "any(EVOLUCAO==2) AND any(EVOLUCAO==3) no mesmo grupo — por grupo, propagado a todos os registros do grupo",
            "flag_final": "inconsistente_obito = posterior_a_obito OR conflito_obito_grupo",
        },
        "registros_vulneraveis": n,
        "grupos_vulneraveis": grupos,
        "registros_por_criterio": {
            "posterior_a_obito": n_posterior,
            "conflito_obito_grupo": n_conflito,
            "ambos": n_ambos,
        },
        "distribuicao_evolucao": dist,
    }


def salvar_resumo(
    total_registros_candidatos: int,
    confianca_por_atributo: list[tuple[str, pd.DataFrame]],
    df_inconsistencia: pd.DataFrame,
    output_json: Path,
) -> None:
    t_sin = THRESHOLDS_DT_SIN
    t_not = THRESHOLDS_DT_NOTIFIC

    resumo_confianca_por_atributo = []
    for col, df in confianca_por_atributo:
        resumo_confianca_por_atributo.append(montar_resumo_confianca_atributo(df, col))

    resumo = {
        "total_registros_candidatos": total_registros_candidatos,
        "ataque_confianca_temporal": {
            "descricao": (
                "Grupos com confianca temporal alta (DT_SIN e DT_NOTIFIC muito proximas) "
                "e atributo sensivel homogeneo. O k-anonimato efetivo desses grupos e "
                "aproximadamente 1, pois os k registros provavelmente sao do mesmo individuo."
            ),
            "criterio_confianca_alta": {
                "score_minimo": 2,
                "thresholds_dt_sin_dias": {
                    "score_3": f"dispersao <= {t_sin[0]}",
                    "score_2": f"dispersao <= {t_sin[1]}",
                    "score_1": f"dispersao <= {t_sin[2]}",
                    "score_0": f"dispersao <= {t_sin[3]}",
                    "score_-1": f"dispersao > {t_sin[3]}",
                },
                "thresholds_dt_notific_dias": {
                    "score_3": f"dispersao <= {t_not[0]}",
                    "score_2": f"dispersao <= {t_not[1]}",
                    "score_1": f"dispersao <= {t_not[2]}",
                    "score_0": f"dispersao <= {t_not[3]}",
                    "score_-1": f"dispersao > {t_not[3]}",
                },
                "score_final": "min(score_dt_sin, score_dt_notific) - penalidade_tamanho",
            },
            "por_atributo_sensivel": resumo_confianca_por_atributo,
        },
        "ataque_inconsistencia_obito": montar_resumo_inconsistencia(df_inconsistencia),
    }
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

    entrada = get_input_path()
    if not entrada.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {entrada}. Rode 'make k' primeiro.")
    df = carregar_csv(entrada)

    try:
        df_inconsistencia = executar_ataque_inconsistencia(df)
    except ValueError as e:
        print(f"[AVISO] ataque inconsistencia: {e}")
        df_inconsistencia = pd.DataFrame()

    if len(df_inconsistencia):
        df_inconsistencia.to_csv(ATAQUE_INCONSISTENCIA_PATH, sep=";", index=False, encoding="utf-8")
        exportar_xlsx(df_inconsistencia, ATAQUE_INCONSISTENCIA_PATH.with_suffix(".xlsx"))

    confianca_por_atributo = []
    for sensivel_col in SENSIVEL_COLUNAS:
        try:
            df_confianca = executar_ataque_confianca(df, sensivel_col=sensivel_col)
        except ValueError as e:
            print(f"[AVISO] [{sensivel_col}] - ataque confianca: {e}")
            df_confianca = pd.DataFrame()
        confianca_por_atributo.append((sensivel_col, df_confianca))

    dfs_confianca_nao_vazios = []
    for _, df_c in confianca_por_atributo:
        if len(df_c):
            dfs_confianca_nao_vazios.append(df_c)

    if dfs_confianca_nao_vazios:
        df_confianca_todos = pd.concat(dfs_confianca_nao_vazios, ignore_index=True)
    else:
        df_confianca_todos = pd.DataFrame()

    if len(df_confianca_todos):
        df_confianca_todos.to_csv(ATAQUE_CONFIANCA_PATH, sep=";", index=False, encoding="utf-8")
        exportar_xlsx(df_confianca_todos, ATAQUE_CONFIANCA_PATH.with_suffix(".xlsx"))

    salvar_resumo(len(df), confianca_por_atributo, df_inconsistencia, RESUMO_ATAQUE_CONFIANCA_PATH)

    if len(df_inconsistencia):
        grupos_inconsistencia = int(df_inconsistencia["chave_qi"].nunique())
    else:
        grupos_inconsistencia = 0
    print(f"Ataque inconsistencia obito: {len(df_inconsistencia)} registros vulneraveis ({grupos_inconsistencia} grupos)")

    for sensivel_col, df_c in confianca_por_atributo:
        if len(df_c):
            grupos_c = int(df_c["chave_qi"].nunique())
        else:
            grupos_c = 0
        print(f"[{sensivel_col}] Ataque confianca temporal: {len(df_c)} registros vulneraveis ({grupos_c} grupos)")
    print(f"Saida resumo: {RESUMO_ATAQUE_CONFIANCA_PATH}")


if __name__ == "__main__":
    main()
