# Repete o sorteio de alvos dos dois cenários para cada semente de
# SEMENTES_REPLICACAO e resume a taxa de sucesso (média, desvio padrão,
# mínimo e máximo) por cenário e atributo sensível.
from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.homogeneidade.definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR, BASE_HOMOGENEA_PATH, DEFAULT_INPUT,
        carregar_csv,
    )
    from src.ataques.homogeneidade.alvos import gerar_alvos_homogeneo, gerar_alvos_heterogeneo
    from src.ataques.homogeneidade.busca import executar_ataque
    from src.utils.comum import SEMENTES_REPLICACAO, exportar_xlsx, percentual
else:
    from .definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR, BASE_HOMOGENEA_PATH, DEFAULT_INPUT,
        carregar_csv,
    )
    from .alvos import gerar_alvos_homogeneo, gerar_alvos_heterogeneo
    from .busca import executar_ataque
    from src.utils.comum import SEMENTES_REPLICACAO, exportar_xlsx, percentual

N_ALVOS = 10
REPLICACOES_PATH = RESULTADOS_DIR / "replicacoes_homogeneidade.csv"
RESUMO_REPLICACOES_PATH = RESULTADOS_DIR / "resumo_replicacoes_homogeneidade.json"


def linha_replicacao(semente: int, cenario: str, sensivel_col: str, resultado: pd.DataFrame) -> dict:
    total_alvos = int(len(resultado))
    sucessos = int(resultado["ataque_bem_sucedido"].sum())
    return {
        "semente": semente,
        "cenario": cenario,
        "atributo_sensivel": sensivel_col,
        "total_alvos": total_alvos,
        "ataques_bem_sucedidos": sucessos,
        "taxa_sucesso": percentual(sucessos, total_alvos, 2),
    }


def resumir(tabela: pd.DataFrame) -> list[dict]:
    # Desvio padrão amostral (ddof=1), já que as sementes são uma amostra das
    # possíveis escolhas de alvos.
    resumo = []
    for (cenario, sensivel_col), grupo in tabela.groupby(["cenario", "atributo_sensivel"], sort=False):
        taxas = grupo["taxa_sucesso"]
        resumo.append({
            "cenario": cenario,
            "atributo_sensivel": sensivel_col,
            "replicacoes": int(len(grupo)),
            "alvos_por_replicacao": N_ALVOS,
            "taxa_sucesso_media": round(float(taxas.mean()), 2),
            "taxa_sucesso_desvio_padrao": round(float(taxas.std(ddof=1)), 2),
            "taxa_sucesso_minima": round(float(taxas.min()), 2),
            "taxa_sucesso_maxima": round(float(taxas.max()), 2),
        })
    return resumo


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    df_base = carregar_csv(DEFAULT_INPUT)
    df_homogeneo = carregar_csv(BASE_HOMOGENEA_PATH)

    linhas = []
    for semente in SEMENTES_REPLICACAO:
        for sensivel_col in SENSIVEL_COLUNAS:
            homog_atributo = df_homogeneo[df_homogeneo["atributo_sensivel"] == sensivel_col]

            alvos = gerar_alvos_homogeneo(homog_atributo, limite=N_ALVOS, semente=semente)
            resultado = executar_ataque(homog_atributo, alvos, sensivel_col, incluir_detalhes=True)
            linhas.append(linha_replicacao(semente, "homogeneo", sensivel_col, resultado))

            alvos = gerar_alvos_heterogeneo(df_base, sensivel_col=sensivel_col, limite=N_ALVOS, semente=semente)
            resultado = executar_ataque(homog_atributo, alvos, sensivel_col, incluir_detalhes=False)
            linhas.append(linha_replicacao(semente, "heterogeneo", sensivel_col, resultado))

    tabela = pd.DataFrame(linhas)
    tabela.to_csv(REPLICACOES_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(tabela, REPLICACOES_PATH.with_suffix(".xlsx"))

    resumo = {
        "descricao": (
            "Taxa de sucesso do ataque de homogeneidade em replicacoes do sorteio "
            "de alvos, uma por semente. Cenario homogeneo: alvos em classes "
            "homogeneas com mais de um registro. Cenario heterogeneo: controle "
            "negativo."
        ),
        "sementes": SEMENTES_REPLICACAO,
        "por_cenario_e_atributo": resumir(tabela),
    }
    with RESUMO_REPLICACOES_PATH.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    for item in resumo["por_cenario_e_atributo"]:
        print(
            f"[{item['cenario']} / {item['atributo_sensivel']}] "
            f"media {item['taxa_sucesso_media']}% | desvio {item['taxa_sucesso_desvio_padrao']} | "
            f"min {item['taxa_sucesso_minima']}% | max {item['taxa_sucesso_maxima']}%"
        )
    print(f"Saida CSV: {REPLICACOES_PATH}")
    print(f"Saida resumo: {RESUMO_REPLICACOES_PATH}")


if __name__ == "__main__":
    main()
