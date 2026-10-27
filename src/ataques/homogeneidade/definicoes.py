import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.utils.comum import (
    QI_COLUNAS, SENSIVEL_COLUNAS, RANDOM_SEED, get_input_path, carregar_csv,
    normalizar_qi_sensivel as normalizar, montar_chave_qi, validar_colunas,
)

# Reexportados para alvos.py/busca.py/confianca.py/filtragem_inicial.py/
# analise_comparativa_k.py (não usados diretamente neste arquivo).
__all__ = [
    "QI_COLUNAS", "SENSIVEL_COLUNAS", "RANDOM_SEED", "carregar_csv",
    "normalizar", "montar_chave_qi", "validar_colunas",
]

K_VALUES = [2, 3, 4, 5]
RESULTADOS_DIR = base_dir / "resultados"

DEFAULT_INPUT = get_input_path()

# Independente de k (só o breakdown de quantos grupos satisfazem cada k
# varia); um único par de saídas p/ os dois atributos, via atributo_sensivel.
BASE_HOMOGENEA_PATH = RESULTADOS_DIR / "base_homogeneidade.csv"
RESUMO_BASE_HOMOGENEA_PATH = RESULTADOS_DIR / "resumo_base_homogeneidade.json"

# Dois cenários (detalhes em alvos.py):
#   1 — homogêneo: amostra de classes homogêneas.
#   2 — heterogêneo (controle negativo): classes com valores distintos.
ALVOS_HOMOGENEO_PATH = RESULTADOS_DIR / "alvos_homogeneo.csv"
ALVOS_HETEROGENEO_PATH = RESULTADOS_DIR / "alvos_heterogeneo.csv"

RESULTADO_HOMOGENEO_PATH = RESULTADOS_DIR / "resultado_busca_homogeneo.csv"
RESUMO_HOMOGENEO_PATH = RESULTADOS_DIR / "resumo_busca_homogeneo.json"
RESULTADO_HETEROGENEO_PATH = RESULTADOS_DIR / "resultado_busca_heterogeneo.csv"
RESUMO_HETEROGENEO_PATH = RESULTADOS_DIR / "resumo_busca_heterogeneo.json"

ATAQUE_CONFIANCA_PATH = RESULTADOS_DIR / "ataque_confianca.csv"
ATAQUE_INCONSISTENCIA_PATH = RESULTADOS_DIR / "ataque_inconsistencia.csv"
RESUMO_ATAQUE_CONFIANCA_PATH = RESULTADOS_DIR / "resumo_ataque_confianca.json"

ANALISE_COMPARATIVA_K_PATH = RESULTADOS_DIR / "analise_comparativa_k.csv"
RESUMO_ANALISE_COMPARATIVA_K_PATH = RESULTADOS_DIR / "resumo_analise_comparativa_k.json"

