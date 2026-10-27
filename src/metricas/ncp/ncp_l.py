# NCP_l: custo fixo por registro (ncp_comum.py) + NCP_MAXIMO como
# penalidade de supressão simulada, trocando o critério de conformidade
# pra distintos/entropia do bloco QI+outro-atributo-sensível (Def. 4.6,
# l-diversidade). |D| = total AVALIADO por atributo (exclui nulos), não a
# base inteira.
from pathlib import Path
import sys
import math

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.modelos.l_diversidade.definicoes import SENSIVEL_COLUNAS, L_VALUES, estatisticas_por_registro
from src.utils.comum import get_input_path, carregar_csv, normalizar_qi_sensivel, salvar_resumo_json, exportar_xlsx, caminho_relativo
from src.metricas.ncp.ncp_comum import montar_dominios, ncp_por_registro, calcular_ncp

RESULTADOS_DIR = base_dir / "resultados"
RESUMO_PATH = RESULTADOS_DIR / "resumo_ncp_l.json"
NCP_POR_L_PATH = RESULTADOS_DIR / "ncp_por_l.csv"


def calcular_ncp_l(ncp_fixo: pd.Series, distintos: pd.Series, entropia: pd.Series, l: int) -> dict:
    limiar_entropia = math.log(l)  # entropia maxima de l valores igualmente provaveis
    return {
        "l": l,
        "limiar_log_l": round(limiar_entropia, 6),
        "distinta": calcular_ncp(ncp_fixo, distintos >= l),
        "entropia": calcular_ncp(ncp_fixo, entropia >= limiar_entropia),
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = get_input_path()
    df = carregar_csv(input_path)
    df = normalizar_qi_sensivel(df)

    dominio, tamanho_no = montar_dominios()
    ncp_fixo_todos = ncp_por_registro(df, dominio, tamanho_no)

    resumo_por_atributo = []
    linhas_csv = []
    for sensivel_col in SENSIVEL_COLUNAS:
        distintos, entropia = estatisticas_por_registro(df, sensivel_col)
        mask_valido = distintos.notna()

        ncp_fixo = ncp_fixo_todos.loc[mask_valido]
        distintos_validos = distintos.loc[mask_valido]
        entropia_validos = entropia.loc[mask_valido]

        por_l = []
        for l in L_VALUES:
            por_l.append(calcular_ncp_l(ncp_fixo, distintos_validos, entropia_validos, l))
        resumo_atributo = {
            "atributo_sensivel": sensivel_col,
            "total_registros_avaliados": int(mask_valido.sum()),
            "total_registros_nulos_excluidos": int((~mask_valido).sum()),
            "por_l": por_l,
        }
        resumo_por_atributo.append(resumo_atributo)
        for item in por_l:
            linhas_csv.append({"atributo_sensivel": sensivel_col, "l": item["l"], "metodo": "distinta", **item["distinta"]})
            linhas_csv.append({"atributo_sensivel": sensivel_col, "l": item["l"], "metodo": "entropia", **item["entropia"]})

        print(f"[{sensivel_col}] NCP_l -- {resumo_atributo['total_registros_avaliados']} registros avaliados.")
        for item in por_l:
            print(
                f"  l={item['l']}: distinta NCP={item['distinta']['ncp']:,} (norm={item['distinta']['ncp_normalizado']}) | "
                f"entropia NCP={item['entropia']['ncp']:,} (norm={item['entropia']['ncp_normalizado']})"
            )

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "descricao": (
            "NCP (Xu et al., KDD'06) generalizado: mesmo custo fixo por "
            "registro do NCP_k (src/metricas/ncp/ncp_k.py), trocando o criterio "
            "de conformidade para distintos/entropia do bloco QI+outro-"
            "atributo-sensivel (Def. 4.6, l-diversidade). |D| e o total "
            "AVALIADO por atributo sensivel (exclui nulos), nao o total da "
            "base inteira."
        ),
        "por_atributo_sensivel": resumo_por_atributo,
    }
    salvar_resumo_json(resumo, RESUMO_PATH)

    ncp_por_l = pd.DataFrame(linhas_csv)
    ncp_por_l.to_csv(NCP_POR_L_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(ncp_por_l, NCP_POR_L_PATH.with_suffix(".xlsx"))

    print(f"Saida resumo: {RESUMO_PATH}")
    print(f"Saida ncp_por_l: {NCP_POR_L_PATH}")
    print(f"Saida ncp_por_l (xlsx): {NCP_POR_L_PATH.with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()
