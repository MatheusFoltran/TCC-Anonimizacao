# Compara distribuição LOCAL x GLOBAL de blocos já l-diversos (L_MINIMO) —
# pega desbalanceamento que a l-diversidade não pega (ex.: 50/50 vs 99/1).
from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.assimetria.definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, L_MINIMO, RAZOES_RISCO,
        BASE_ASSIMETRIA_PATH, RESUMO_BASE_ASSIMETRIA_PATH,
        get_input_path, normalizar, montar_chave_bloco, outro_atributo, validar_colunas,
    )
    from src.utils.comum import carregar_csv, exportar_xlsx, percentual, round_seguro, caminho_relativo
else:
    from .definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, L_MINIMO, RAZOES_RISCO,
        BASE_ASSIMETRIA_PATH, RESUMO_BASE_ASSIMETRIA_PATH,
        get_input_path, normalizar, montar_chave_bloco, outro_atributo, validar_colunas,
    )
    from src.utils.comum import carregar_csv, exportar_xlsx, percentual, round_seguro, caminho_relativo


def montar_base_atributo(df: pd.DataFrame, sensivel_col: str) -> pd.DataFrame:
    # Uma linha por (bloco, valor presente no bloco), só para blocos com
    # distintos >= L_MINIMO. p_local/p_global/razao_risco medem o quanto a
    # distribuição do bloco diverge da distribuição global para esse valor.
    validar_colunas(df, sensivel_col)
    df = normalizar(df.copy())
    df = df[df[sensivel_col].notna()].copy()
    p_global = df[sensivel_col].value_counts(normalize=True)

    outro_col = outro_atributo(sensivel_col)
    df["chave_bloco"] = montar_chave_bloco(df, sensivel_col)

    contagens = (
        df.groupby(["chave_bloco", sensivel_col]).size().rename("contagem_local").reset_index()
    )
    contagens["tamanho_bloco"] = contagens.groupby("chave_bloco")["contagem_local"].transform("sum")
    contagens["distintos"] = contagens.groupby("chave_bloco")["chave_bloco"].transform("size")
    contagens = contagens[contagens["distintos"] >= L_MINIMO].copy()

    contagens["p_local"] = contagens["contagem_local"] / contagens["tamanho_bloco"]
    contagens["p_global"] = contagens[sensivel_col].map(p_global)
    contagens["razao_risco"] = contagens["p_local"] / contagens["p_global"]

    qi_por_bloco = df.drop_duplicates("chave_bloco")[["chave_bloco"] + QI_COLUNAS + [outro_col]]
    resultado = contagens.merge(qi_por_bloco, on="chave_bloco", how="left")
    resultado = resultado.rename(columns={sensivel_col: "valor_sensivel", outro_col: "atributo_conhecido_valor"})
    resultado.insert(0, "atributo_sensivel", sensivel_col)
    resultado.insert(1, "atributo_conhecido", outro_col)

    colunas_saida = (
        ["atributo_sensivel", "chave_bloco"] + QI_COLUNAS
        + ["atributo_conhecido", "atributo_conhecido_valor", "valor_sensivel",
           "tamanho_bloco", "distintos", "contagem_local", "p_local", "p_global", "razao_risco"]
    )
    return resultado[colunas_saida]


def montar_resumo_atributo(base_atributo: pd.DataFrame, total_registros_entrada: int, sensivel_col: str) -> dict:
    total_blocos = int(base_atributo["chave_bloco"].nunique())
    razao = base_atributo["razao_risco"]

    # Percentual de registros (não de linhas bloco-valor) cujo próprio valor
    # sensível tem razao_risco >= cada patamar de RAZOES_RISCO. Cada linha é
    # ponderada por contagem_local, o que aplica o critério de sucesso de
    # busca.py a todos os blocos l-diversos, e não só aos alvos sorteados.
    total_registros_avaliados = int(base_atributo["contagem_local"].sum())
    por_razao = []
    for r in RAZOES_RISCO:
        registros_risco_elevado = int(base_atributo.loc[razao >= r, "contagem_local"].sum())
        por_razao.append({
            "razao_minima": r,
            "registros_risco_elevado": registros_risco_elevado,
            "percentual_registros_risco_elevado": percentual(registros_risco_elevado, total_registros_avaliados),
        })

    return {
        "atributo_sensivel": sensivel_col,
        "total_registros_entrada": total_registros_entrada,
        "total_blocos_l_diversos": total_blocos,
        "total_linhas_bloco_valor": int(len(base_atributo)),
        "distribuicao_distintos": {
            str(k): int(v)
            for k, v in base_atributo.drop_duplicates("chave_bloco")["distintos"].value_counts().sort_index().items()
        },
        "razao_risco_media": round_seguro(razao.mean(), len(razao)),
        "razao_risco_mediana": round_seguro(razao.median(), len(razao)),
        "razao_risco_p90": round_seguro(razao.quantile(0.9), len(razao)),
        "razao_risco_max": round_seguro(razao.max(), len(razao)),
        "total_registros_avaliados": total_registros_avaliados,
        "por_razao": por_razao,
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = get_input_path()
    df_entrada = carregar_csv(input_path)

    bases_por_atributo = []
    resumo_por_atributo = []
    for sensivel_col in SENSIVEL_COLUNAS:
        base_atributo = montar_base_atributo(df_entrada, sensivel_col)
        bases_por_atributo.append(base_atributo)

        resumo_atributo = montar_resumo_atributo(base_atributo, len(df_entrada), sensivel_col)
        resumo_por_atributo.append(resumo_atributo)

        print(
            f"[{sensivel_col}] {resumo_atributo['total_blocos_l_diversos']} blocos l-diversos (l>={L_MINIMO}) — "
            f"razao_risco media {resumo_atributo['razao_risco_media']} | p90 {resumo_atributo['razao_risco_p90']} | max {resumo_atributo['razao_risco_max']}"
        )

    base_todos = pd.concat(bases_por_atributo, ignore_index=True)
    base_todos.to_csv(BASE_ASSIMETRIA_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(base_todos, BASE_ASSIMETRIA_PATH.with_suffix(".xlsx"))

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "total_registros_entrada": len(df_entrada),
        "l_minimo": L_MINIMO,
        "razoes_avaliadas": RAZOES_RISCO,
        "por_atributo_sensivel": resumo_por_atributo,
    }
    with RESUMO_BASE_ASSIMETRIA_PATH.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    print(f"Saida base: {BASE_ASSIMETRIA_PATH}")
    print(f"Saida base (xlsx): {BASE_ASSIMETRIA_PATH.with_suffix('.xlsx')}")
    print(f"Saida resumo: {RESUMO_BASE_ASSIMETRIA_PATH}")


if __name__ == "__main__":
    main()
