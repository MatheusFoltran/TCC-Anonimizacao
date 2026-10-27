import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.utils.comum import (
    QI_COLUNAS, SENSIVEL_COLUNAS, RANDOM_SEED, get_input_path,
    normalizar_qi_sensivel as normalizar,
    outro_atributo_sensivel as outro_atributo, montar_chave_bloco,
    validar_colunas,
)

# Reexportados para base.py/alvos.py/busca.py (não usados diretamente
# neste arquivo, que só define constantes/caminhos).
__all__ = [
    "QI_COLUNAS", "SENSIVEL_COLUNAS", "RANDOM_SEED", "get_input_path",
    "normalizar", "outro_atributo", "montar_chave_bloco", "validar_colunas",
]

RESULTADOS_DIR = base_dir / "resultados"

# l-diversidade mínima que um bloco precisa satisfazer para entrar na base
# do ataque: mostra que blocos já "protegidos" por l ainda vazam informação.
L_MINIMO = 2

# Patamares de razão de risco (p_local/p_global) a partir dos quais o ataque
# é considerado bem-sucedido.
RAZOES_RISCO = [2.0, 5.0, 10.0]

# Base de blocos l-diversos com o desvio local x global por valor (ver
# base.py) — análoga a BASE_HOMOGENEA_PATH em homogeneidade/definicoes.py.
BASE_ASSIMETRIA_PATH = RESULTADOS_DIR / "base_assimetria.csv"
RESUMO_BASE_ASSIMETRIA_PATH = RESULTADOS_DIR / "resumo_base_assimetria.json"

# Simulação do ataque: alvos sorteados dentre os blocos l-diversos (alvos.py)
# e o resultado da busca (busca.py) — mesmo padrão de homogeneidade.
ALVOS_ASSIMETRIA_PATH = RESULTADOS_DIR / "alvos_assimetria.csv"
RESULTADO_BUSCA_PATH = RESULTADOS_DIR / "resultado_busca_assimetria.csv"
RESUMO_BUSCA_PATH = RESULTADOS_DIR / "resumo_busca_assimetria.json"
