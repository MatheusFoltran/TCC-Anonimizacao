# l-diversidade distinta (distintos>=l) e entropia (mais restritiva:
# -sum(p_s*log(p_s))>=log(l)). Blocos multi-atributo, ver definicoes.py.
from pathlib import Path
import sys
import json
import math

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.modelos.l_diversidade.definicoes import (
        SENSIVEL_COLUNAS, L_VALUES, RESULTADOS_DIR, BLOCOS_PATH, RESUMO_PATH,
        calcular_estatisticas_bloco,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, round_seguro, caminho_relativo
else:
    from .definicoes import (
        SENSIVEL_COLUNAS, L_VALUES, RESULTADOS_DIR, BLOCOS_PATH, RESUMO_PATH,
        calcular_estatisticas_bloco,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, round_seguro, caminho_relativo


def avaliar_l(stats_bloco: pd.DataFrame, l: int) -> dict:
    # l só entra aqui, como corte sobre distintos/entropia já calculados em
    # calcular_estatisticas_bloco — dá pra varrer L_VALUES sem recalcular.
    grupos_total = int(len(stats_bloco))
    registros_total = int(stats_bloco["tamanho_bloco"].sum())

    def _resumo(mask: pd.Series) -> dict:
        grupos_abaixo_l = int(mask.sum())
        registros_abaixo_l = int(stats_bloco.loc[mask, "tamanho_bloco"].sum())
        return {
            "grupos_abaixo_l": grupos_abaixo_l,
            "percentual_grupos_abaixo_l": percentual(grupos_abaixo_l, grupos_total),
            "registros_abaixo_l": registros_abaixo_l,
            "percentual_registros_abaixo_l": percentual(registros_abaixo_l, registros_total),
        }

    limiar_entropia = math.log(l)  # entropia máxima de l valores igualmente prováveis
    return {
        "l": l,
        "distinta": _resumo(stats_bloco["distintos"] < l),
        "entropia": {"limiar_log_l": round(limiar_entropia, 6), **_resumo(stats_bloco["entropia"] < limiar_entropia)},
    }


def montar_resumo_atributo(stats_bloco: pd.DataFrame, total_registros_entrada: int, sensivel_col: str) -> dict:
    registros_avaliados = int(stats_bloco["tamanho_bloco"].sum())
    l_efetivo = stats_bloco["l_efetivo"]

    por_l = []
    for l in L_VALUES:
        por_l.append(avaliar_l(stats_bloco, l))

    return {
        "atributo_sensivel": sensivel_col,
        "total_registros_avaliados": registros_avaliados,
        "total_registros_nulos_excluidos": total_registros_entrada - registros_avaliados,
        "total_grupos": int(len(stats_bloco)),
        "distribuicao_distintos": {
            str(k): int(v) for k, v in stats_bloco["distintos"].value_counts().sort_index().items()
        },
        "l_efetivo_medio": round_seguro(l_efetivo.mean(), len(l_efetivo)),
        "l_efetivo_minimo": round_seguro(l_efetivo.min(), len(l_efetivo)),
        "por_l": por_l,
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

        print(f"[{sensivel_col}] l-diversidade — {len(stats_bloco)} blocos avaliados.")
        for item in resumo_atributo["por_l"]:
            print(
                f"  l={item['l']}: distinta {item['distinta']['percentual_registros_abaixo_l']}% abaixo | "
                f"entropia {item['entropia']['percentual_registros_abaixo_l']}% abaixo"
            )

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
