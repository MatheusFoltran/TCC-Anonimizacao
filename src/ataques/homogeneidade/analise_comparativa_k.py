# k_max_satisfeito por registro x homogeneidade: grupos grandes ainda
# homogêneos refutam a suficiência do k-anonimato sozinho.
import sys
from pathlib import Path
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.homogeneidade.definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR,
        ANALISE_COMPARATIVA_K_PATH, RESUMO_ANALISE_COMPARATIVA_K_PATH,
        get_input_path, carregar_csv, normalizar, montar_chave_qi,
    )
    from src.utils.comum import exportar_xlsx, percentual
else:
    from .definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR,
        ANALISE_COMPARATIVA_K_PATH, RESUMO_ANALISE_COMPARATIVA_K_PATH,
        get_input_path, carregar_csv, normalizar, montar_chave_qi,
    )
    from src.utils.comum import exportar_xlsx, percentual


def _k_max_de_tamanho(tamanho: pd.Series) -> pd.Series:
    # Maior k satisfeito pelo grupo, limitado a [1, 5].
    return tamanho.astype(int).clip(lower=1, upper=5).rename("k_max_satisfeito")


def enriquecer(df: pd.DataFrame, sensivel_col: str) -> pd.DataFrame:
    df = normalizar(df.copy())
    df["chave_qi"] = montar_chave_qi(df)

    tam = df["tamanho_grupo"].astype(str).str.strip().astype(int)
    df["k_max_satisfeito"] = _k_max_de_tamanho(tam)

    grp = df.groupby("chave_qi")[sensivel_col]
    df["homogeneo"] = (
        (~df[sensivel_col].isna().groupby(df["chave_qi"]).transform("any")) &
        (grp.transform("nunique") == 1)
    )
    return df


def agregar_por_k_max(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k_max in sorted(df["k_max_satisfeito"].unique()):
        sub = df[df["k_max_satisfeito"] == k_max]
        sub_hom = sub[sub["homogeneo"]]

        grupos_total = sub["chave_qi"].nunique()
        grupos_hom   = sub_hom["chave_qi"].nunique()

        if k_max == 1:
            label = "k=1"
        else:
            label = f"k_max={k_max}"

        rows.append({
            "k_max_satisfeito":       k_max,
            "label":                  label,
            "registros_total":        len(sub),
            "grupos_total":           grupos_total,
            "registros_homogeneos":   len(sub_hom),
            "grupos_homogeneos":      grupos_hom,
            "pct_registros_hom":      percentual(len(sub_hom), len(sub), 2),
            "pct_grupos_hom":         percentual(grupos_hom, grupos_total, 2),
        })
    return pd.DataFrame(rows)


def montar_resumo_atributo(tabela: pd.DataFrame, total_registros: int, sensivel_col: str) -> dict:
    total_hom = int(tabela["registros_homogeneos"].sum())

    rows_json = []
    for _, r in tabela.iterrows():
        rows_json.append({
            "k_max_satisfeito":     int(r["k_max_satisfeito"]),
            "label":                r["label"],
            "registros_total":      int(r["registros_total"]),
            "grupos_total":         int(r["grupos_total"]),
            "registros_homogeneos": int(r["registros_homogeneos"]),
            "grupos_homogeneos":    int(r["grupos_homogeneos"]),
            "pct_registros_hom":    float(r["pct_registros_hom"]),
            "pct_grupos_hom":       float(r["pct_grupos_hom"]),
        })

    return {
        "atributo_sensivel": sensivel_col,
        "total_registros": total_registros,
        "total_registros_homogeneos": total_hom,
        "pct_total_homogeneos": percentual(total_hom, total_registros, 2),
        "por_nivel_k": rows_json,
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

    input_path = get_input_path()
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {input_path}. Execute 'make k' primeiro.")

    df_base = carregar_csv(input_path)

    tabelas = []
    resumo_por_atributo = []
    for sensivel_col in SENSIVEL_COLUNAS:
        df = enriquecer(df_base, sensivel_col)
        tabela = agregar_por_k_max(df)
        resumo_por_atributo.append(montar_resumo_atributo(tabela, len(df), sensivel_col))

        tabela.insert(0, "atributo_sensivel", sensivel_col)
        tabelas.append(tabela)

        print(f"Analise comparativa [{sensivel_col}] — vulnerabilidade por k_max_satisfeito:")
        print()
        print(tabela.drop(columns="atributo_sensivel").to_string(index=False))
        print()

    tabela_todos = pd.concat(tabelas, ignore_index=True)
    tabela_todos.to_csv(ANALISE_COMPARATIVA_K_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(tabela_todos, ANALISE_COMPARATIVA_K_PATH.with_suffix(".xlsx"))

    resumo = {
        "descricao": (
            "Para cada nivel de protecao k (k_max_satisfeito = maior k que o grupo satisfaz), "
            "mostra quantos registros e grupos sao vulneraveis ao ataque de homogeneidade "
            "(atributo sensivel identico em todos os registros do grupo). "
            "k_max=1 representa grupos de tamanho 1 — trivialmente identificaveis sem ataque. "
            "Grupos com k_max alto ainda homogeneos provam que k-anonimato nao elimina o risco."
        ),
        "por_atributo_sensivel": resumo_por_atributo,
    }
    with RESUMO_ANALISE_COMPARATIVA_K_PATH.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    print(f"Saida CSV:  {ANALISE_COMPARATIVA_K_PATH}")
    print(f"Saida CSV (xlsx): {ANALISE_COMPARATIVA_K_PATH.with_suffix('.xlsx')}")
    print(f"Saida JSON: {RESUMO_ANALISE_COMPARATIVA_K_PATH}")


if __name__ == "__main__":
    main()
