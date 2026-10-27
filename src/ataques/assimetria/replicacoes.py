# Repete o sorteio de alvos para cada semente de SEMENTES_REPLICACAO e resume
# a taxa de sucesso por patamar de RAZOES_RISCO e a razão de risco média
# (média, desvio padrão, mínimo e máximo) por atributo sensível.
from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.assimetria.definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR, RAZOES_RISCO, BASE_ASSIMETRIA_PATH,
    )
    from src.ataques.assimetria.alvos import gerar_alvos
    from src.ataques.assimetria.busca import executar_ataque
    from src.utils.comum import SEMENTES_REPLICACAO, carregar_csv, exportar_xlsx, percentual
else:
    from .definicoes import (
        SENSIVEL_COLUNAS, RESULTADOS_DIR, RAZOES_RISCO, BASE_ASSIMETRIA_PATH,
    )
    from .alvos import gerar_alvos
    from .busca import executar_ataque
    from src.utils.comum import SEMENTES_REPLICACAO, carregar_csv, exportar_xlsx, percentual

N_ALVOS = 10
REPLICACOES_PATH = RESULTADOS_DIR / "replicacoes_assimetria.csv"
RESUMO_REPLICACOES_PATH = RESULTADOS_DIR / "resumo_replicacoes_assimetria.json"


def coluna_taxa(razao: float) -> str:
    return f"taxa_sucesso_{int(razao)}x"


def linha_replicacao(semente: int, sensivel_col: str, resultado: pd.DataFrame) -> dict:
    total_alvos = int(len(resultado))
    linha = {
        "semente": semente,
        "atributo_sensivel": sensivel_col,
        "total_alvos": total_alvos,
        "razao_risco_media": round(float(resultado["razao_risco"].mean()), 4),
    }
    for r in RAZOES_RISCO:
        sucessos = int((resultado["razao_risco"] >= r).sum())
        linha[coluna_taxa(r)] = percentual(sucessos, total_alvos, 2)
    return linha


def estatisticas(serie: pd.Series) -> dict:
    # Desvio padrão amostral (ddof=1), já que as sementes são uma amostra das
    # possíveis escolhas de alvos.
    return {
        "media": round(float(serie.mean()), 2),
        "desvio_padrao": round(float(serie.std(ddof=1)), 2),
        "minimo": round(float(serie.min()), 2),
        "maximo": round(float(serie.max()), 2),
    }


def resumir(tabela: pd.DataFrame) -> list[dict]:
    resumo = []
    for sensivel_col, grupo in tabela.groupby("atributo_sensivel", sort=False):
        por_razao = []
        for r in RAZOES_RISCO:
            item = {"razao_minima": r}
            item.update(estatisticas(grupo[coluna_taxa(r)]))
            por_razao.append(item)
        resumo.append({
            "atributo_sensivel": sensivel_col,
            "replicacoes": int(len(grupo)),
            "alvos_por_replicacao": N_ALVOS,
            "taxa_sucesso_por_razao": por_razao,
            "razao_risco_media": estatisticas(grupo["razao_risco_media"]),
        })
    return resumo


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    base = carregar_csv(BASE_ASSIMETRIA_PATH)
    base["contagem_local"] = base["contagem_local"].astype(int)

    linhas = []
    for semente in SEMENTES_REPLICACAO:
        for sensivel_col in SENSIVEL_COLUNAS:
            base_atributo = base[base["atributo_sensivel"] == sensivel_col]
            alvos = gerar_alvos(base_atributo, limite=N_ALVOS, semente=semente)
            resultado = executar_ataque(base_atributo, alvos, sensivel_col)
            linhas.append(linha_replicacao(semente, sensivel_col, resultado))

    tabela = pd.DataFrame(linhas)
    tabela.to_csv(REPLICACOES_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(tabela, REPLICACOES_PATH.with_suffix(".xlsx"))

    resumo = {
        "descricao": (
            "Taxa de sucesso do ataque de assimetria em replicacoes do sorteio "
            "de alvos, uma por semente, para cada patamar de razao de risco."
        ),
        "sementes": SEMENTES_REPLICACAO,
        "razoes_avaliadas": RAZOES_RISCO,
        "por_atributo_sensivel": resumir(tabela),
    }
    with RESUMO_REPLICACOES_PATH.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    for item in resumo["por_atributo_sensivel"]:
        partes = []
        for r in item["taxa_sucesso_por_razao"]:
            partes.append(f"{r['razao_minima']}x: {r['media']}% (dp {r['desvio_padrao']})")
        razao = item["razao_risco_media"]
        print(f"[{item['atributo_sensivel']}] {' | '.join(partes)} | razao media {razao['media']} (dp {razao['desvio_padrao']})")
    print(f"Saida CSV: {REPLICACOES_PATH}")
    print(f"Saida resumo: {RESUMO_REPLICACOES_PATH}")


if __name__ == "__main__":
    main()
