# Generaliza/suprime, roda o funil de identificação e gera candidatos.csv
# com nao_atinge_k{k} por K_VALUES — entrada padrão dos outros módulos.
import sys
from pathlib import Path

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.nucleo import (
    COLUNAS_BASE_OBRIGATORIAS,
    executar_pipeline,
    montar_candidatos,
)
from src.utils.comum import salvar_resumo_json, exportar_xlsx, caminho_relativo
from src.tecnicas.generalizacao_supressao import aplicar_generalizacao_supressao
from src.tecnicas.regionais_pr import IBGE_TO_REGIONAL_PR


K_VALUES = [2, 3, 4, 5]


def analise_qi_base(tamanhos: pd.Series) -> dict:
    # Estatísticas do agrupamento por QI que independem de k (só o limiar de
    # comparação muda). Recebe tamanhos (value_counts da chave por QI).
    if tamanhos.empty:
        maior_grupo = 0
    else:
        maior_grupo = int(tamanhos.max())

    return {
        "grupos_total": int(len(tamanhos)),
        "distribuicao_tamanho_grupos": {str(tam): int(v) for tam, v in tamanhos.value_counts().sort_index().items()},
        "maior_grupo": maior_grupo,
    }


def analise_k_anon(chave: pd.Series, tamanhos: pd.Series, k: int) -> dict:
    # Estatísticas que dependem do valor de k (quantos grupos/registros não
    # atingem o limiar).
    tamanhos_por_registro = chave.map(tamanhos)
    grupos_abaixo_k = int((tamanhos < k).sum())
    registros_abaixo_k = int((tamanhos_por_registro < k).sum())

    return {
        "grupos_abaixo_k": grupos_abaixo_k,
        "registros_abaixo_k": registros_abaixo_k,
        "percentual_registros_abaixo_k": round((registros_abaixo_k / len(chave) * 100.0), 4)
        if len(chave)
        else 0.0,
    }


def marcar_nao_atinge_k(df: pd.DataFrame, chave: pd.Series, tamanhos: pd.Series, k_values: list[int]) -> tuple[pd.DataFrame, dict[int, dict]]:
    # Generalização já aplicada. Adiciona uma coluna nao_atinge_k{k} por
    # valor de k em k_values (True para registros em grupos < k, sem
    # removê-los).
    tamanhos_por_registro = chave.map(tamanhos)

    df = df.copy()
    info_por_k = {}
    for k in k_values:
        mask_abaixo = tamanhos_por_registro < k
        df[f"nao_atinge_k{k}"] = mask_abaixo
        registros_abaixo_k = int(mask_abaixo.sum())
        info_por_k[k] = {
            "registros_nao_atingem_k": registros_abaixo_k,
            "percentual_nao_atingem_k": round(registros_abaixo_k / len(df) * 100.0, 4)
            if len(df)
            else 0.0,
        }
    return df, info_por_k


def main() -> None:
    resultados_dir = base_dir / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)

    input_path = project_dir / "base_filtrada" / "dados_filtro_base.csv"
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_path}")

    df_base = pd.read_csv(input_path, sep=";", dtype=str, low_memory=False)
    df_base.columns = [c.strip().replace('"', "") for c in df_base.columns]

    colunas_analise = ["DT_NOTIFIC", "DT_SIN_PRI", "EVOLUCAO", "CLASSI_FIN"]
    obrigatorias = COLUNAS_BASE_OBRIGATORIAS + colunas_analise
    faltantes = [c for c in obrigatorias if c not in df_base.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatorias ausentes na base: {faltantes}")

    df_base = aplicar_generalizacao_supressao(df_base, IBGE_TO_REGIONAL_PR)

    # O funil (grupo_id, dispersão, confiança) independe de k; o k só entra na
    # marcação nao_atinge_k{k} logo abaixo.
    df_pipeline, resumos_funil = executar_pipeline(df_base.copy())

    # chave_etapa_3 é a chave por QI, já calculada dentro de executar_pipeline.
    chave_qi = df_pipeline["chave_etapa_3"]
    tamanhos_qi = chave_qi.value_counts(dropna=False)

    # Uma coluna nao_atinge_k{k} para cada valor de K_VALUES, usadas pelos
    # módulos seguintes (homogeneidade, l-diversidade).
    df_pipeline, info_marcacao_por_k = marcar_nao_atinge_k(df_pipeline, chave_qi, tamanhos_qi, K_VALUES)

    candidatos = montar_candidatos(df_pipeline)

    # Propaga id_grupo de volta para TODOS os registros via grupo_id.
    # grupos de tamanho 1 ficam com id_grupo = NaN.
    grupo_para_id = (
        candidatos.drop_duplicates("grupo_id")
        .set_index("grupo_id")["id_grupo"]
        .to_dict()
    )
    df_pipeline["id_grupo"] = df_pipeline["grupo_id"].map(grupo_para_id).astype("Int64")

    # Ordena: grupos multi-registro primeiro (por id_grupo), grupos de tamanho 1 ao final
    if df_pipeline["id_grupo"].notna().any():
        max_id = int(df_pipeline["id_grupo"].dropna().max())
    else:
        max_id = 0
    df_pipeline["_sort_id"] = df_pipeline["id_grupo"].fillna(max_id + 1)
    df_todos = df_pipeline.sort_values("_sort_id", kind="stable").drop(columns=["_sort_id"])

    colunas_saida = [
        "id_grupo",
        "DT_NASC",
        "CO_MUN_RES",
        "CS_SEXO",
        "CS_RACA",
        "CO_MUN_NOT",
        "EVOLUCAO",
        "CLASSI_FIN",
        "tamanho_grupo",
        *[f"nao_atinge_k{k}" for k in K_VALUES],
        "confianca_mesma_pessoa",
        "inconsistente_obito",
        "posterior_a_obito",
        "conflito_obito_grupo",
        "dispersao_dt_sin",
        "dispersao_dt_notific",
    ]
    colunas_saida = [c for c in colunas_saida if c in df_todos.columns]

    candidatos_path = resultados_dir / "candidatos.csv"
    df_todos[colunas_saida].to_csv(candidatos_path, sep=";", index=False)

    candidatos_xlsx_path = resultados_dir / "candidatos.xlsx"
    exportar_xlsx(df_todos[colunas_saida], candidatos_xlsx_path)

    distribuicao_tamanho = (
        df_pipeline.groupby("grupo_id").size().value_counts().sort_index().astype("int64").to_dict()
    )

    print(f"K-anonimato concluido para k={K_VALUES}.")
    print(f"  Total registros (incluindo grupos de tamanho 1): {len(df_todos)}")
    print("  Saida candidatos:", candidatos_path)
    print("  Saida candidatos (xlsx):", candidatos_xlsx_path)

    # Campos que independem de k (QI base, funil, distribuição de grupos) ficam
    # no topo; "por_k" traz só o que varia com k.
    resumo_final = {
        "arquivo_entrada": caminho_relativo(input_path),
        "total_registros": int(len(df_pipeline)),
        "total_grupos": int(df_pipeline["grupo_id"].nunique()),
        "registros_candidatos": int(len(candidatos)),
        "percentual_registros_candidatos": round((len(candidatos) / len(df_pipeline) * 100.0), 4)
        if len(df_pipeline)
        else 0.0,
        "etapas_funil": resumos_funil,
        "analise_qi_base": analise_qi_base(tamanhos_qi),
        "analise_grupos": {
            "distribuicao_tamanho_grupos": {str(tam): int(v) for tam, v in distribuicao_tamanho.items()},
        },
        "por_k": [
            {
                "k": k,
                "analise_k": analise_k_anon(chave_qi, tamanhos_qi, k),
                "marcacao_abaixo_k": info_marcacao_por_k[k],
            }
            for k in K_VALUES
        ],
    }

    resumo_path = resultados_dir / "resumo.json"
    salvar_resumo_json(resumo_final, resumo_path)

    for item in resumo_final["por_k"]:
        print(f"  Registros nao atingem k={item['k']}: {item['marcacao_abaixo_k']['registros_nao_atingem_k']}")
    print("  Saida resumo:", resumo_path)


if __name__ == "__main__":
    main()
