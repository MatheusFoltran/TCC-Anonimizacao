# Indivíduo real sorteado por bloco l-diverso (valor sensível ponderado
# pela frequência no bloco); CSV guarda o gabarito usado em busca.py.
from pathlib import Path
import sys

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.assimetria.definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, RANDOM_SEED,
        BASE_ASSIMETRIA_PATH, ALVOS_ASSIMETRIA_PATH,
    )
    from src.utils.comum import carregar_csv, exportar_xlsx
else:
    from .definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, RANDOM_SEED,
        BASE_ASSIMETRIA_PATH, ALVOS_ASSIMETRIA_PATH,
    )
    from src.utils.comum import carregar_csv, exportar_xlsx


def gerar_alvos(base_atributo: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    # Sorteio em duas etapas: primeiro o bloco, depois o VALOR do alvo dentro
    # dele, ponderado por contagem_local — equivale a sortear uma pessoa real
    # ao acaso dentre as do bloco, sem viés pra valores minoritários.
    blocos = base_atributo.drop_duplicates("chave_bloco")
    blocos_sorteados = blocos.sample(n=min(limite, len(blocos)), random_state=RANDOM_SEED)

    alvos = []
    for _, bloco in blocos_sorteados.iterrows():
        candidatos_valor = base_atributo[base_atributo["chave_bloco"] == bloco["chave_bloco"]]
        alvo = candidatos_valor.sample(n=1, weights="contagem_local", random_state=RANDOM_SEED).iloc[0]
        alvos.append(alvo)

    amostra = pd.DataFrame(alvos).reset_index(drop=True)
    amostra.insert(0, "alvo_id", amostra.index + 1)
    amostra.insert(1, "nome", [f"Alvo Assimetria {i+1}" for i in range(len(amostra))])

    colunas = ["alvo_id", "nome"] + QI_COLUNAS + ["atributo_conhecido", "atributo_conhecido_valor", "valor_sensivel"]
    return amostra[colunas].rename(columns={"valor_sensivel": "valor_sensivel_real"})


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    base = carregar_csv(BASE_ASSIMETRIA_PATH)
    base["contagem_local"] = base["contagem_local"].astype(int)

    alvos_por_atributo = []
    for sensivel_col in SENSIVEL_COLUNAS:
        base_atributo = base[base["atributo_sensivel"] == sensivel_col]
        alvos = gerar_alvos(base_atributo, limite=10)
        alvos.insert(0, "atributo_sensivel", sensivel_col)
        alvos_por_atributo.append(alvos)

    todos = pd.concat(alvos_por_atributo, ignore_index=True)
    todos.to_csv(ALVOS_ASSIMETRIA_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(todos, ALVOS_ASSIMETRIA_PATH.with_suffix(".xlsx"))

    print(f"Alvos (blocos l-diversos): {sum(len(a) for a in alvos_por_atributo)} alvos -> {ALVOS_ASSIMETRIA_PATH}")


if __name__ == "__main__":
    main()
