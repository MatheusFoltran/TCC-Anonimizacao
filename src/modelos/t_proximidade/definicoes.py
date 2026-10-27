# t-proximidade: bloco QI puro satisfaz se D[P_local,Q]<=t. Sem ordem ->
# "equal distance" D[P,Q]=(1/2)*sum|p_i-q_i| equivale (distribuições somam
# 1) a D=sum max(0,p_local-p_global) só pros valores presentes no bloco —
# não precisa enumerar categorias ausentes.
import sys
from pathlib import Path
import numpy as np
import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.utils.comum import (
    SENSIVEL_COLUNAS, normalizar_qi_sensivel as normalizar, montar_chave_qi,
    validar_colunas,
)

# Reexportado para avaliacao.py (não usado diretamente aqui).
__all__ = ["SENSIVEL_COLUNAS"]

T_VALUES = [0.1, 0.15, 0.2, 0.3]
RESULTADOS_DIR = base_dir / "resultados"

BLOCOS_PATH = RESULTADOS_DIR / "blocos_t_proximidade.csv"
RESUMO_PATH = RESULTADOS_DIR / "resumo_t_proximidade.json"
REGISTROS_COMPARATIVO_PATH = RESULTADOS_DIR / "registros_t_proximidade_comparativo.csv"
RESUMO_COMPARATIVO_PATH = RESULTADOS_DIR / "resumo_t_proximidade_comparativo.json"
ANALISE_COMPARATIVA_K_PATH = RESULTADOS_DIR / "analise_comparativa_k.csv"
RESUMO_ANALISE_COMPARATIVA_K_PATH = RESULTADOS_DIR / "resumo_analise_comparativa_k.json"


def calcular_estatisticas_bloco(df: pd.DataFrame, sensivel_alvo: str) -> pd.DataFrame:
    # Uma linha por bloco: tamanho, distintos e EMD. Exclui sensivel_alvo nulo.
    validar_colunas(df, sensivel_alvo)
    df = normalizar(df.copy())
    df = df[df[sensivel_alvo].notna()].copy()
    df["chave_qi"] = montar_chave_qi(df)

    # Q: distribuição global do atributo sensível na base inteira.
    p_global = df[sensivel_alvo].value_counts(normalize=True)

    # P: distribuição LOCAL (contagem/tamanho do bloco); index de "contagens" = (chave_qi, valor).
    contagens = df.groupby(["chave_qi", sensivel_alvo]).size()
    tamanho_bloco = contagens.groupby(level="chave_qi").transform("sum")
    p_local = contagens / tamanho_bloco

    # soma do excesso por bloco = EMD do bloco (ver cabeçalho, prova).
    p_global_alinhado = p_local.index.get_level_values(sensivel_alvo).map(p_global)
    excesso = np.clip(p_local.to_numpy() - p_global_alinhado.to_numpy(), a_min=0, a_max=None)
    emd_por_linha = pd.Series(excesso, index=p_local.index)

    stats = pd.DataFrame({
        "tamanho_bloco": contagens.groupby(level="chave_qi").sum(),
        "distintos": contagens.groupby(level="chave_qi").size(),
        "emd": emd_por_linha.groupby(level="chave_qi").sum(),  # soma do excesso == EMD do bloco
    })
    return stats


def estatisticas_por_registro(df: pd.DataFrame, sensivel_alvo: str) -> pd.Series:
    # emd do bloco por registro; mask_valido pra não herdar a estatística
    # do bloco quando o próprio sensivel_alvo é nulo.
    df_norm = normalizar(df.copy())
    chave = montar_chave_qi(df_norm)
    mask_valido = df_norm[sensivel_alvo].notna()

    stats = calcular_estatisticas_bloco(df, sensivel_alvo)
    # Repete a EMD do bloco em cada linha que pertence a ele (NaN se nulo).
    return chave.map(stats["emd"]).where(mask_valido)
