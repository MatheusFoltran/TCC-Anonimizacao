# DM_k (dm_k.py) generalizado: troca "tamanho_bloco >= k" por
# "emd_do_bloco <= t". |D| = total AVALIADO por atributo (exclui nulos),
# nao a base inteira.
from pathlib import Path
import sys

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.modelos.t_proximidade.definicoes import SENSIVEL_COLUNAS, T_VALUES, estatisticas_por_registro
from src.utils.comum import get_input_path, carregar_csv, salvar_resumo_json, exportar_xlsx, caminho_relativo

RESULTADOS_DIR = base_dir / "resultados"
RESUMO_PATH = RESULTADOS_DIR / "resumo_dm_t.json"
DM_POR_T_PATH = RESULTADOS_DIR / "dm_por_t.csv"


def calcular_dm_t(tamanho_bloco_qi: pd.Series, emd: pd.Series, t: float) -> dict:
    total = int(len(tamanho_bloco_qi))
    penalidade = tamanho_bloco_qi.where(emd <= t, total)
    dm = int(penalidade.sum())
    dm_maximo = total * total
    return {
        "t": t,
        "dm": dm,
        "dm_maximo_teorico": dm_maximo,
        "dm_normalizado": round(dm / dm_maximo, 6),
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = get_input_path()
    df = carregar_csv(input_path)
    df["tamanho_grupo"] = df["tamanho_grupo"].astype(int)

    resumo_por_atributo = []
    linhas_csv = []
    for sensivel_col in SENSIVEL_COLUNAS:
        emd_registro = estatisticas_por_registro(df, sensivel_col)
        mask_valido = emd_registro.notna()

        tamanho_bloco_qi = df.loc[mask_valido, "tamanho_grupo"]
        emd_valido = emd_registro.loc[mask_valido]

        por_t = []
        for t in T_VALUES:
            por_t.append(calcular_dm_t(tamanho_bloco_qi, emd_valido, t))
        resumo_atributo = {
            "atributo_sensivel": sensivel_col,
            "total_registros_avaliados": int(mask_valido.sum()),
            "total_registros_nulos_excluidos": int((~mask_valido).sum()),
            "por_t": por_t,
        }
        resumo_por_atributo.append(resumo_atributo)
        for item in por_t:
            linhas_csv.append({"atributo_sensivel": sensivel_col, **item})

        print(f"[{sensivel_col}] DM_t -- {resumo_atributo['total_registros_avaliados']} registros avaliados.")
        for item in por_t:
            print(f"  t={item['t']}: DM={item['dm']:,} (norm={item['dm_normalizado']})")

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "descricao": (
            "DM (Bayardo & Agrawal, 2005) generalizado: mesmo bloco QI puro "
            "e penalidade do DM_k (src/metricas/dm/dm_k.py), trocando o criterio "
            "de conformidade para emd_do_bloco <= t (t-proximidade). |D| e o "
            "total AVALIADO por atributo sensivel (exclui nulos), nao o "
            "total da base inteira."
        ),
        "por_atributo_sensivel": resumo_por_atributo,
    }
    salvar_resumo_json(resumo, RESUMO_PATH)

    dm_por_t = pd.DataFrame(linhas_csv)
    dm_por_t.to_csv(DM_POR_T_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(dm_por_t, DM_POR_T_PATH.with_suffix(".xlsx"))

    print(f"Saida resumo: {RESUMO_PATH}")
    print(f"Saida dm_por_t: {DM_POR_T_PATH}")
    print(f"Saida dm_por_t (xlsx): {DM_POR_T_PATH.with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()
