# k_max_satisfeito por bloco x t-proximidade: blocos maiores (k_max alto)
# tendem a ter EMD menor, mas a violacao nao desaparece nem nos maiores.
import sys
from pathlib import Path
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.modelos.t_proximidade.definicoes import (
        SENSIVEL_COLUNAS, T_VALUES, RESULTADOS_DIR,
        ANALISE_COMPARATIVA_K_PATH, RESUMO_ANALISE_COMPARATIVA_K_PATH,
        calcular_estatisticas_bloco,
    )
    from src.modelos.t_proximidade.avaliacao import avaliar_t
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, round_seguro
else:
    from .definicoes import (
        SENSIVEL_COLUNAS, T_VALUES, RESULTADOS_DIR,
        ANALISE_COMPARATIVA_K_PATH, RESUMO_ANALISE_COMPARATIVA_K_PATH,
        calcular_estatisticas_bloco,
    )
    from .avaliacao import avaliar_t
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, round_seguro


def _k_max_de_tamanho(tamanho: pd.Series) -> pd.Series:
    # Maior k satisfeito pelo bloco, limitado a [1, 5] (mesmo criterio da
    # analise equivalente em homogeneidade).
    return tamanho.astype(int).clip(lower=1, upper=5).rename("k_max_satisfeito")


def agregar_por_k_max(stats_bloco: pd.DataFrame) -> pd.DataFrame:
    stats_bloco = stats_bloco.copy()
    stats_bloco["k_max_satisfeito"] = _k_max_de_tamanho(stats_bloco["tamanho_bloco"])

    rows = []
    for k_max in sorted(stats_bloco["k_max_satisfeito"].unique()):
        sub = stats_bloco[stats_bloco["k_max_satisfeito"] == k_max]
        emd = sub["emd"]

        label = "k=1" if k_max == 1 else f"k_max={k_max}"

        for t in T_VALUES:
            resultado_t = avaliar_t(sub, t)
            rows.append({
                "k_max_satisfeito":         k_max,
                "label":                    label,
                "grupos_total":             int(len(sub)),
                "registros_total":          int(sub["tamanho_bloco"].sum()),
                "emd_media":                round_seguro(emd.mean(), len(emd)),
                "emd_mediana":              round_seguro(emd.median(), len(emd)),
                "t":                        t,
                "grupos_viola_t":           resultado_t["grupos_viola_t"],
                "percentual_grupos_viola_t": resultado_t["percentual_grupos_viola_t"],
                "registros_viola_t":        resultado_t["registros_viola_t"],
                "percentual_registros_viola_t": resultado_t["percentual_registros_viola_t"],
            })
    return pd.DataFrame(rows)


def montar_resumo_atributo(tabela: pd.DataFrame, total_registros_avaliados: int, sensivel_col: str) -> dict:
    por_k_max = []
    for k_max in sorted(tabela["k_max_satisfeito"].unique()):
        sub = tabela[tabela["k_max_satisfeito"] == k_max]
        primeira = sub.iloc[0]

        por_t = []
        for _, r in sub.iterrows():
            por_t.append({
                "t":                             float(r["t"]),
                "grupos_viola_t":                int(r["grupos_viola_t"]),
                "percentual_grupos_viola_t":     float(r["percentual_grupos_viola_t"]),
                "registros_viola_t":             int(r["registros_viola_t"]),
                "percentual_registros_viola_t":  float(r["percentual_registros_viola_t"]),
            })

        por_k_max.append({
            "k_max_satisfeito": int(k_max),
            "label":            primeira["label"],
            "grupos_total":     int(primeira["grupos_total"]),
            "registros_total":  int(primeira["registros_total"]),
            "emd_media":        float(primeira["emd_media"]),
            "emd_mediana":      float(primeira["emd_mediana"]),
            "por_t":            por_t,
        })

    return {
        "atributo_sensivel": sensivel_col,
        "total_registros_avaliados": total_registros_avaliados,
        "por_k_max": por_k_max,
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = get_input_path()
    df_entrada = carregar_csv(input_path)

    tabelas = []
    resumo_por_atributo = []
    for sensivel_col in SENSIVEL_COLUNAS:
        stats_bloco = calcular_estatisticas_bloco(df_entrada, sensivel_col).reset_index()
        tabela = agregar_por_k_max(stats_bloco)
        total_registros_avaliados = int(stats_bloco["tamanho_bloco"].sum())
        resumo_por_atributo.append(montar_resumo_atributo(tabela, total_registros_avaliados, sensivel_col))

        tabela.insert(0, "atributo_sensivel", sensivel_col)
        tabelas.append(tabela)

        print(f"Analise comparativa [{sensivel_col}] — EMD/violacao de t-proximidade por k_max_satisfeito:")
        print()
        print(tabela.drop(columns="atributo_sensivel").to_string(index=False))
        print()

    tabela_todos = pd.concat(tabelas, ignore_index=True)
    tabela_todos.to_csv(ANALISE_COMPARATIVA_K_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(tabela_todos, ANALISE_COMPARATIVA_K_PATH.with_suffix(".xlsx"))

    resumo = {
        "descricao": (
            "Para cada nivel de protecao k (k_max_satisfeito = maior k que o bloco QI puro "
            "satisfaz), mostra a EMD media/mediana do bloco e o percentual de blocos/registros "
            "que violam a t-proximidade em cada limiar de t avaliado. "
            "k_max=1 representa blocos de tamanho 1 (fora do escopo pratico da t-proximidade, "
            "mas incluidos para completude). "
            "Blocos com k_max alto ainda violando a t-proximidade em limiares permissivos "
            "confirmam que k-anonimato (tamanho de bloco) e t-proximidade (distancia à "
            "distribuicao global) sao dimensoes independentes."
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
