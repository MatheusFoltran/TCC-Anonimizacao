# DM_k (dm_k.py) generalizado: conformidade olha o bloco QI+outro-sensivel
# (Def. 4.6), mas a penalidade usa o tamanho do bloco QI puro. |D| = total
# AVALIADO por atributo (exclui nulos), nao a base inteira.
from pathlib import Path
import sys
import math

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.modelos.l_diversidade.definicoes import SENSIVEL_COLUNAS, L_VALUES, estatisticas_por_registro
from src.utils.comum import get_input_path, carregar_csv, salvar_resumo_json, exportar_xlsx, caminho_relativo

RESULTADOS_DIR = base_dir / "resultados"
RESUMO_PATH = RESULTADOS_DIR / "resumo_dm_l.json"
DM_POR_L_PATH = RESULTADOS_DIR / "dm_por_l.csv"


def calcular_dm(tamanho_bloco_qi: pd.Series, mask_conforme: pd.Series) -> dict:
    total = int(len(tamanho_bloco_qi))
    penalidade = tamanho_bloco_qi.where(mask_conforme, total)
    dm = int(penalidade.sum())
    dm_maximo = total * total
    return {
        "dm": dm,
        "dm_maximo_teorico": dm_maximo,
        "dm_normalizado": round(dm / dm_maximo, 6),
    }


def calcular_dm_l(tamanho_bloco_qi: pd.Series, distintos: pd.Series, entropia: pd.Series, l: int) -> dict:
    limiar_entropia = math.log(l)  # entropia maxima de l valores igualmente provaveis
    return {
        "l": l,
        "limiar_log_l": round(limiar_entropia, 6),
        "distinta": calcular_dm(tamanho_bloco_qi, distintos >= l),
        "entropia": calcular_dm(tamanho_bloco_qi, entropia >= limiar_entropia),
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = get_input_path()
    df = carregar_csv(input_path)
    df["tamanho_grupo"] = df["tamanho_grupo"].astype(int)

    resumo_por_atributo = []
    linhas_csv = []
    for sensivel_col in SENSIVEL_COLUNAS:
        distintos, entropia = estatisticas_por_registro(df, sensivel_col)
        mask_valido = distintos.notna()

        tamanho_bloco_qi = df.loc[mask_valido, "tamanho_grupo"]
        distintos_validos = distintos.loc[mask_valido]
        entropia_validos = entropia.loc[mask_valido]

        por_l = []
        for l in L_VALUES:
            por_l.append(calcular_dm_l(tamanho_bloco_qi, distintos_validos, entropia_validos, l))
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

        print(f"[{sensivel_col}] DM_l -- {resumo_atributo['total_registros_avaliados']} registros avaliados.")
        for item in por_l:
            print(
                f"  l={item['l']}: distinta DM={item['distinta']['dm']:,} (norm={item['distinta']['dm_normalizado']}) | "
                f"entropia DM={item['entropia']['dm']:,} (norm={item['entropia']['dm_normalizado']})"
            )

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "descricao": (
            "DM (Bayardo & Agrawal, 2005) generalizado: mesmo bloco QI puro "
            "e penalidade do DM_k (src/metricas/dm/dm_k.py), trocando o criterio "
            "de conformidade para distintos/entropia do bloco QI+outro-"
            "atributo-sensivel (Def. 4.6, l-diversidade) do registro. |D| e "
            "o total AVALIADO por atributo sensivel (exclui nulos), nao o "
            "total da base inteira."
        ),
        "por_atributo_sensivel": resumo_por_atributo,
    }
    salvar_resumo_json(resumo, RESUMO_PATH)

    dm_por_l = pd.DataFrame(linhas_csv)
    dm_por_l.to_csv(DM_POR_L_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(dm_por_l, DM_POR_L_PATH.with_suffix(".xlsx"))

    print(f"Saida resumo: {RESUMO_PATH}")
    print(f"Saida dm_por_l: {DM_POR_L_PATH}")
    print(f"Saida dm_por_l (xlsx): {DM_POR_L_PATH.with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()
