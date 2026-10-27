# NCP_t: custo fixo por registro (ncp_comum.py) + NCP_MAXIMO como
# penalidade de supressão simulada, trocando o critério de conformidade
# para emd_do_bloco <= t (t-proximidade). |D| = total AVALIADO por
# atributo (exclui nulos), não a base inteira.
from pathlib import Path
import sys

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.modelos.t_proximidade.definicoes import SENSIVEL_COLUNAS, T_VALUES, estatisticas_por_registro
from src.utils.comum import get_input_path, carregar_csv, normalizar_qi_sensivel, salvar_resumo_json, exportar_xlsx, caminho_relativo
from src.metricas.ncp.ncp_comum import montar_dominios, ncp_por_registro, calcular_ncp

RESULTADOS_DIR = base_dir / "resultados"
RESUMO_PATH = RESULTADOS_DIR / "resumo_ncp_t.json"
NCP_POR_T_PATH = RESULTADOS_DIR / "ncp_por_t.csv"


def calcular_ncp_t(ncp_fixo: pd.Series, emd: pd.Series, t: float) -> dict:
    return {"t": t, **calcular_ncp(ncp_fixo, emd <= t)}


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
        emd_registro = estatisticas_por_registro(df, sensivel_col)
        mask_valido = emd_registro.notna()

        ncp_fixo = ncp_fixo_todos.loc[mask_valido]
        emd_valido = emd_registro.loc[mask_valido]

        por_t = []
        for t in T_VALUES:
            por_t.append(calcular_ncp_t(ncp_fixo, emd_valido, t))
        resumo_atributo = {
            "atributo_sensivel": sensivel_col,
            "total_registros_avaliados": int(mask_valido.sum()),
            "total_registros_nulos_excluidos": int((~mask_valido).sum()),
            "por_t": por_t,
        }
        resumo_por_atributo.append(resumo_atributo)
        for item in por_t:
            linhas_csv.append({"atributo_sensivel": sensivel_col, **item})

        print(f"[{sensivel_col}] NCP_t -- {resumo_atributo['total_registros_avaliados']} registros avaliados.")
        for item in por_t:
            print(f"  t={item['t']}: NCP={item['ncp']:,} (norm={item['ncp_normalizado']})")

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "descricao": (
            "NCP (Xu et al., KDD'06) generalizado: mesmo custo fixo por "
            "registro do NCP_k (src/metricas/ncp/ncp_k.py), trocando o criterio "
            "de conformidade para emd_do_bloco <= t (t-proximidade). |D| e "
            "o total AVALIADO por atributo sensivel (exclui nulos), nao o "
            "total da base inteira."
        ),
        "por_atributo_sensivel": resumo_por_atributo,
    }
    salvar_resumo_json(resumo, RESUMO_PATH)

    ncp_por_t = pd.DataFrame(linhas_csv)
    ncp_por_t.to_csv(NCP_POR_T_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(ncp_por_t, NCP_POR_T_PATH.with_suffix(".xlsx"))

    print(f"Saida resumo: {RESUMO_PATH}")
    print(f"Saida ncp_por_t: {NCP_POR_T_PATH}")
    print(f"Saida ncp_por_t (xlsx): {NCP_POR_T_PATH.with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()
