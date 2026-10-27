# Blocos multi-atributo: pra avaliar UM sensível, o OUTRO entra no QI
# (bloco de EVOLUCAO = QI+CLASSI_FIN e vice-versa) — partições diferentes.
import sys
from pathlib import Path
import numpy as np
import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.utils.comum import (
    SENSIVEL_COLUNAS, normalizar_qi_sensivel as normalizar, montar_chave_bloco,
    validar_colunas,
)

# Reexportado para avaliacao.py/comparativo.py (não usado diretamente aqui).
__all__ = ["SENSIVEL_COLUNAS"]

L_VALUES = [2, 3, 4, 5]
RESULTADOS_DIR = base_dir / "resultados"

# Saída única (blocos + resumo); atributo/método viram coluna/chave, não arquivos separados.
BLOCOS_PATH = RESULTADOS_DIR / "blocos_l_diversidade.csv"
RESUMO_PATH = RESULTADOS_DIR / "resumo_l_diversidade.json"
REGISTROS_COMPARATIVO_PATH = RESULTADOS_DIR / "registros_l_diversidade_comparativo.csv"
RESUMO_COMPARATIVO_PATH = RESULTADOS_DIR / "resumo_l_diversidade_comparativo.json"


def calcular_estatisticas_bloco(df: pd.DataFrame, sensivel_alvo: str) -> pd.DataFrame:
    # Uma linha por bloco: tamanho, distintos, entropia (log natural) e
    # l_efetivo (=exp(entropia)). Exclui registros com sensivel_alvo nulo.
    validar_colunas(df, sensivel_alvo)
    df = normalizar(df.copy())
    df = df[df[sensivel_alvo].notna()].copy()
    df["chave_bloco"] = montar_chave_bloco(df, sensivel_alvo)

    grupo = df.groupby("chave_bloco")[sensivel_alvo]
    stats = grupo.agg(
        tamanho_bloco="size",
        distintos="nunique",
    )

    # Entropia do bloco: -sum(p * ln p) sobre a proporção de cada valor.
    contagens = df.groupby(["chave_bloco", sensivel_alvo]).size()
    p = contagens / contagens.groupby(level="chave_bloco").transform("sum")
    stats["entropia"] = (-(p * np.log(p))).groupby(level="chave_bloco").sum()
    stats["l_efetivo"] = np.exp(stats["entropia"])
    return stats


def estatisticas_por_registro(df: pd.DataFrame, sensivel_alvo: str) -> tuple[pd.Series, pd.Series]:
    # mask_valido pra não herdar a estatística do bloco quando o próprio
    # sensivel_alvo é nulo (a chave do bloco não depende dele).
    df_norm = normalizar(df.copy())
    chave = montar_chave_bloco(df_norm, sensivel_alvo)
    mask_valido = df_norm[sensivel_alvo].notna()

    stats = calcular_estatisticas_bloco(df, sensivel_alvo)
    distintos = chave.map(stats["distintos"]).where(mask_valido)
    entropia = chave.map(stats["entropia"]).where(mask_valido)
    return distintos, entropia
