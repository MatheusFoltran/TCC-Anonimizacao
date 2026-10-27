# Avaliação de t-proximidade para EVOLUCAO/CLASSI_FIN sobre blocos QI puro:
# viola quando emd > t (oposto da l-diversidade, onde é "abaixo" que viola).
from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.modelos.t_proximidade.definicoes import (
        SENSIVEL_COLUNAS, T_VALUES, RESULTADOS_DIR, BLOCOS_PATH, RESUMO_PATH,
        calcular_estatisticas_bloco,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, round_seguro, caminho_relativo
else:
    from .definicoes import (
        SENSIVEL_COLUNAS, T_VALUES, RESULTADOS_DIR, BLOCOS_PATH, RESUMO_PATH,
        calcular_estatisticas_bloco,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, round_seguro, caminho_relativo


def avaliar_t(stats_bloco: pd.DataFrame, t: float) -> dict:
    grupos_total = int(len(stats_bloco))
    registros_total = int(stats_bloco["tamanho_bloco"].sum())

    # t só entra aqui, como corte sobre a EMD já calculada (calcular_
    # estatisticas_bloco) — por isso dá pra varrer vários valores de t
    # (T_VALUES) sem recalcular a EMD a cada vez.
    mask_viola = stats_bloco["emd"] > t
    grupos_viola_t = int(mask_viola.sum())
    registros_viola_t = int(stats_bloco.loc[mask_viola, "tamanho_bloco"].sum())

    return {
        "t": t,
        "grupos_viola_t": grupos_viola_t,
        "percentual_grupos_viola_t": percentual(grupos_viola_t, grupos_total),
        "registros_viola_t": registros_viola_t,
        "percentual_registros_viola_t": percentual(registros_viola_t, registros_total),
    }


def montar_resumo_atributo(stats_bloco: pd.DataFrame, total_registros_entrada: int, sensivel_col: str) -> dict:
    registros_avaliados = int(stats_bloco["tamanho_bloco"].sum())
    emd = stats_bloco["emd"]

    por_t = []
    for t in T_VALUES:
        por_t.append(avaliar_t(stats_bloco, t))

    return {
        "atributo_sensivel": sensivel_col,
        "total_registros_avaliados": registros_avaliados,
        "total_registros_nulos_excluidos": total_registros_entrada - registros_avaliados,
        "total_grupos": int(len(stats_bloco)),
        "distribuicao_distintos": {
            str(k): int(v) for k, v in stats_bloco["distintos"].value_counts().sort_index().items()
        },
        "emd_media": round_seguro(emd.mean(), len(emd)),
        "emd_mediana": round_seguro(emd.median(), len(emd)),
        "emd_maxima": round_seguro(emd.max(), len(emd)),
        "por_t": por_t,
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = get_input_path()
    df_entrada = carregar_csv(input_path)

    blocos_por_atributo = []
    resumo_por_atributo = []
    for sensivel_col in SENSIVEL_COLUNAS:
        stats_bloco = calcular_estatisticas_bloco(df_entrada, sensivel_col).reset_index()
        stats_bloco.insert(0, "atributo_sensivel", sensivel_col)
        blocos_por_atributo.append(stats_bloco)

        resumo_atributo = montar_resumo_atributo(stats_bloco, len(df_entrada), sensivel_col)
        resumo_por_atributo.append(resumo_atributo)

        print(f"[{sensivel_col}] t-proximidade — {len(stats_bloco)} blocos avaliados (EMD media {resumo_atributo['emd_media']}).")
        for item in resumo_atributo["por_t"]:
            print(f"  t={item['t']}: {item['percentual_registros_viola_t']}% dos registros violam t-proximidade")

    blocos_todos = pd.concat(blocos_por_atributo, ignore_index=True)
    blocos_todos.to_csv(BLOCOS_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(blocos_todos, BLOCOS_PATH.with_suffix(".xlsx"))

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "total_registros_entrada": len(df_entrada),
        "por_atributo_sensivel": resumo_por_atributo,
    }
    with RESUMO_PATH.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    print(f"Saida blocos: {BLOCOS_PATH}")
    print(f"Saida blocos (xlsx): {BLOCOS_PATH.with_suffix('.xlsx')}")
    print(f"Saida resumo: {RESUMO_PATH}")


if __name__ == "__main__":
    main()
