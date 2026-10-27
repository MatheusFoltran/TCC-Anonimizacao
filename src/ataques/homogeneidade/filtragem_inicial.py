from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.homogeneidade.definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, K_VALUES, RESULTADOS_DIR,
        BASE_HOMOGENEA_PATH, RESUMO_BASE_HOMOGENEA_PATH,
        get_input_path, carregar_csv, normalizar, montar_chave_qi, validar_colunas,
    )
    from src.utils.comum import exportar_xlsx, percentual, caminho_relativo
else:
    from .definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, K_VALUES, RESULTADOS_DIR,
        BASE_HOMOGENEA_PATH, RESUMO_BASE_HOMOGENEA_PATH,
        get_input_path, carregar_csv, normalizar, montar_chave_qi, validar_colunas,
    )
    from src.utils.comum import exportar_xlsx, percentual, caminho_relativo


def filtrar_grupos_homogeneos(df: pd.DataFrame, sensivel_col: str = "EVOLUCAO") -> pd.DataFrame:
    # Grupo QI puro (não o bloco multi-atributo da l-diversidade) homogêneo em sensivel_col: sem nulos, um único valor.
    validar_colunas(df, sensivel_col)
    df = normalizar(df.copy())
    df["chave_qi"] = montar_chave_qi(df)

    grupo_sensivel  = df.groupby("chave_qi")[sensivel_col]
    grupo_tem_nulo  = df[sensivel_col].isna().groupby(df["chave_qi"]).transform("any")
    grupo_distintos = grupo_sensivel.transform("nunique")
    grupo_tamanho   = grupo_sensivel.transform("size").astype("int64")

    mask = (~grupo_tem_nulo) & (grupo_distintos == 1)
    df_filtrado = df[mask].copy()
    df_filtrado["tamanho_grupo_qi"] = grupo_tamanho[mask]
    df_filtrado["valor_sensivel"] = df_filtrado[sensivel_col]
    df_filtrado.insert(0, "atributo_sensivel", sensivel_col)

    colunas_nao_atinge = [c for c in df_filtrado.columns if c.startswith("nao_atinge_k")]
    colunas_saida = ["atributo_sensivel"] + QI_COLUNAS + ["valor_sensivel", "tamanho_grupo_qi"]
    colunas_extras = colunas_nao_atinge + [
        "tamanho_grupo", "confianca_mesma_pessoa", "inconsistente_obito",
        "dispersao_dt_sin", "dispersao_dt_notific",
    ]
    colunas_saida += [c for c in colunas_extras if c in df_filtrado.columns]

    return df_filtrado[colunas_saida + ["chave_qi"]]


def _breakdown_por_k(df_homogeneo: pd.DataFrame, mask_tamanho_1: pd.Series, k: int, sensivel_col: str) -> dict:
    coluna_k = f"nao_atinge_k{k}"
    if coluna_k in df_homogeneo.columns:
        mask_nao_atinge = df_homogeneo[coluna_k].astype(str).str.lower().isin(["true", "1"])
        mask_satisfaz = (~mask_nao_atinge) & (~mask_tamanho_1)
        mask_pequeno  = mask_nao_atinge & (~mask_tamanho_1)
    else:
        mask_satisfaz = ~mask_tamanho_1
        mask_pequeno  = pd.Series(False, index=df_homogeneo.index)

    return {
        "k": k,
        "grupos_abaixo_k": {
            "registros": int(mask_pequeno.sum()),
            "grupos": int(df_homogeneo.loc[mask_pequeno, "chave_qi"].nunique()),
            "descricao": f"Grupos com tamanho entre 2 e k-1 — nao satisfazem k={k}, suprimidos em sistemas reais",
        },
        "grupos_satisfazem_k": {
            "registros": int(mask_satisfaz.sum()),
            "grupos": int(df_homogeneo.loc[mask_satisfaz, "chave_qi"].nunique()),
            "descricao": f"Grupos com tamanho >= k={k} — satisfazem k-anonimato e ainda tem {sensivel_col} homogenea (vulnerabilidade real do modelo)",
        },
    }


def montar_resumo_atributo(df_entrada: pd.DataFrame, df_homogeneo: pd.DataFrame, k_values: list[int], sensivel_col: str) -> dict:
    total_entrada = int(len(df_entrada))
    total_homogeneo = int(len(df_homogeneo))
    resumo = {
        "atributo_sensivel": sensivel_col,
        "total_registros_homogeneos": total_homogeneo,
        "total_grupos_homogeneos": int(df_homogeneo["chave_qi"].nunique()),
        "percentual_registros_vulneraveis": percentual(total_homogeneo, total_entrada),
        "distribuicao_valor_sensivel_unico": {
            str(ev): int(v)
            for ev, v in df_homogeneo["valor_sensivel"].value_counts().to_dict().items()
        },
    }

    if "tamanho_grupo_qi" in df_homogeneo.columns:
        tam = df_homogeneo["tamanho_grupo_qi"].astype(str).str.strip()
        mask_tamanho_1 = tam == "1"

        # Grupos de tamanho 1 não dependem de k; só grupos_abaixo_k e
        # grupos_satisfazem_k variam com k.
        por_k = []
        for k in k_values:
            por_k.append(_breakdown_por_k(df_homogeneo, mask_tamanho_1, k, sensivel_col))

        resumo["breakdown_vulnerabilidade"] = {
            "grupos_tamanho_1": {
                "registros": int(mask_tamanho_1.sum()),
                "grupos": int(df_homogeneo.loc[mask_tamanho_1, "chave_qi"].nunique()),
                "descricao": "Registros unicos — trivialmente identificaveis sem necessidade de ataque de homogeneidade",
            },
            "por_k": por_k,
        }

    if "confianca_mesma_pessoa" in df_homogeneo.columns:
        resumo["distribuicao_confianca_grupos_homogeneos"] = {
            str(c): int(v)
            for c, v in df_homogeneo.groupby("chave_qi")["confianca_mesma_pessoa"]
            .first()
            .value_counts()
            .to_dict()
            .items()
        }
    return resumo


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

    entrada = get_input_path()
    if not entrada.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {entrada}. Rode 'make k' primeiro.")

    df_entrada = carregar_csv(entrada)

    blocos_por_atributo = []
    resumo_por_atributo = []
    for sensivel_col in SENSIVEL_COLUNAS:
        df_homogeneo = filtrar_grupos_homogeneos(df_entrada, sensivel_col)
        blocos_por_atributo.append(df_homogeneo)
        resumo_por_atributo.append(
            montar_resumo_atributo(df_entrada, df_homogeneo, K_VALUES, sensivel_col)
        )
        print(f"[{sensivel_col}]: {len(df_homogeneo)} registros vulneraveis, {df_homogeneo['chave_qi'].nunique()} grupos homogeneos.")

    base_homogenea = pd.concat(blocos_por_atributo, ignore_index=True)
    base_homogenea.to_csv(BASE_HOMOGENEA_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(base_homogenea, BASE_HOMOGENEA_PATH.with_suffix(".xlsx"))

    resumo = {
        "arquivo_entrada": caminho_relativo(entrada),
        "total_registros_entrada": len(df_entrada),
        "por_atributo_sensivel": resumo_por_atributo,
    }
    with RESUMO_BASE_HOMOGENEA_PATH.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    print(f"  Saida CSV: {BASE_HOMOGENEA_PATH}")
    print(f"  Saida XLSX: {BASE_HOMOGENEA_PATH.with_suffix('.xlsx')}")
    print(f"  Saida resumo: {RESUMO_BASE_HOMOGENEA_PATH}")


if __name__ == "__main__":
    main()
