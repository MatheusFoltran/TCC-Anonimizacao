# Consolida DM e NCP, a partir dos resumos de dm_k/l/t.py e ncp_k/l/t.py,
# nos 4 pontos de referencia comparados no relatorio: k-anonimato (k=2),
# l-diversidade distinta (l=2), t-proximidade (t=0,2) e l-diversidade
# entropia (l=2).
from pathlib import Path
import sys
import json
import math

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.utils.comum import SENSIVEL_COLUNAS, exportar_xlsx, salvar_resumo_json

RESULTADOS_DIR = base_dir / "resultados"
RESUMO_PATH = RESULTADOS_DIR / "resumo_comparativo.json"
COMPARATIVO_PATH = RESULTADOS_DIR / "comparativo.csv"

K_REFERENCIA = 2
L_REFERENCIA = 2
T_REFERENCIA = 0.2


def _carregar(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}. Execute 'make dm dm-l dm-t ncp ncp-l ncp-t' primeiro.")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _valor_k(resumo_k: dict, metrica: str, k: int) -> float:
    # dm_k/ncp_k nao sao por atributo sensivel (bloco QI puro).
    for item in resumo_k["depois"]["por_k"]:
        if item["k"] == k:
            return item[f"{metrica}_normalizado"]
    raise ValueError(f"k={k} nao encontrado em {metrica}_k.")


def _valor_l(resumo_l: dict, metrica: str, l: int, variante: str, atributo: str) -> float:
    for item_atributo in resumo_l["por_atributo_sensivel"]:
        if item_atributo["atributo_sensivel"] != atributo:
            continue
        for item in item_atributo["por_l"]:
            if item["l"] == l:
                return item[variante][f"{metrica}_normalizado"]
    raise ValueError(f"l={l}/{variante}/{atributo} nao encontrado em {metrica}_l.")


def _valor_t(resumo_t: dict, metrica: str, t: float, atributo: str) -> float:
    for item_atributo in resumo_t["por_atributo_sensivel"]:
        if item_atributo["atributo_sensivel"] != atributo:
            continue
        for item in item_atributo["por_t"]:
            if math.isclose(item["t"], t):
                return item[f"{metrica}_normalizado"]
    raise ValueError(f"t={t}/{atributo} nao encontrado em {metrica}_t.")


def montar_tabela(metrica: str) -> pd.DataFrame:
    resumo_k = _carregar(base_dir / metrica / f"resultados/resumo_{metrica}_k.json")
    resumo_l = _carregar(base_dir / metrica / f"resultados/resumo_{metrica}_l.json")
    resumo_t = _carregar(base_dir / metrica / f"resultados/resumo_{metrica}_t.json")

    valor_k = _valor_k(resumo_k, metrica, K_REFERENCIA)

    linhas = [{
        "criterio": "k-anonimato",
        "parametro": f"k={K_REFERENCIA}",
        "EVOLUCAO": valor_k,
        "CLASSI_FIN": valor_k,
    }]

    for variante, rotulo in (("distinta", "l-diversidade distinta"), ("entropia", "l-diversidade entropia")):
        linha = {"criterio": rotulo, "parametro": f"l={L_REFERENCIA}"}
        for atributo in SENSIVEL_COLUNAS:
            linha[atributo] = _valor_l(resumo_l, metrica, L_REFERENCIA, variante, atributo)
        linhas.append(linha)

    linha_t = {"criterio": "t-proximidade", "parametro": f"t={T_REFERENCIA:g}"}
    for atributo in SENSIVEL_COLUNAS:
        linha_t[atributo] = _valor_t(resumo_t, metrica, T_REFERENCIA, atributo)
    linhas.append(linha_t)

    # Ordem de apresentacao do relatorio: k-anon < l-distinta < t-prox < l-entropia.
    ordem = ["k-anonimato", "l-diversidade distinta", "t-proximidade", "l-diversidade entropia"]
    tabela = pd.DataFrame(linhas).set_index("criterio").loc[ordem].reset_index()
    return tabela


def verificar_concordancia_ordem(tabela_dm: pd.DataFrame, tabela_ncp: pd.DataFrame) -> bool:
    # As duas metricas devem concordar na ordem de custo de utilidade entre
    # os 4 criterios, para os dois atributos sensiveis (Discussao dos
    # Resultados do NCP, relatorio).
    ok = True
    for atributo in SENSIVEL_COLUNAS:
        ordem_dm = tabela_dm[atributo].tolist()
        ordem_ncp = tabela_ncp[atributo].tolist()
        crescente_dm = all(a <= b for a, b in zip(ordem_dm, ordem_dm[1:]))
        crescente_ncp = all(a <= b for a, b in zip(ordem_ncp, ordem_ncp[1:]))
        ok = ok and crescente_dm and crescente_ncp
    return ok


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

    tabela_dm = montar_tabela("dm")
    tabela_ncp = montar_tabela("ncp")

    concorda = verificar_concordancia_ordem(tabela_dm, tabela_ncp)

    tabela_dm_export = tabela_dm.copy()
    tabela_dm_export.insert(0, "metrica", "DM")
    tabela_ncp_export = tabela_ncp.copy()
    tabela_ncp_export.insert(0, "metrica", "NCP")
    tabela_completa = pd.concat([tabela_dm_export, tabela_ncp_export], ignore_index=True)

    tabela_completa.to_csv(COMPARATIVO_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(tabela_completa, COMPARATIVO_PATH.with_suffix(".xlsx"))

    resumo = {
        "descricao": (
            "DM e NCP normalizados nos 4 pontos de referencia comparados no "
            "relatorio (k-anonimato k=2, l-diversidade distinta l=2, "
            "t-proximidade t=0,2, l-diversidade entropia l=2), consolidados "
            "a partir dos resumos ja gerados por dm_k/l/t.py e ncp_k/l/t.py."
        ),
        "k_referencia": K_REFERENCIA,
        "l_referencia": L_REFERENCIA,
        "t_referencia": T_REFERENCIA,
        "dm": tabela_dm.to_dict(orient="records"),
        "ncp": tabela_ncp.to_dict(orient="records"),
        "ordem_de_custo_concorda_entre_dm_e_ncp": concorda,
    }
    salvar_resumo_json(resumo, RESUMO_PATH)

    print("DM (normalizado) nos 4 criterios de referencia:")
    print(tabela_dm.to_string(index=False))
    print()
    print("NCP (normalizado) nos 4 criterios de referencia:")
    print(tabela_ncp.to_string(index=False))
    print()
    print(f"Ordem de custo concorda entre DM e NCP: {concorda}")
    print(f"Saida tabela: {COMPARATIVO_PATH}")
    print(f"Saida tabela (xlsx): {COMPARATIVO_PATH.with_suffix('.xlsx')}")
    print(f"Saida resumo: {RESUMO_PATH}")


if __name__ == "__main__":
    main()
