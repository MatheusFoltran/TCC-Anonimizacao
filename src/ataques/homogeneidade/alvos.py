# Alvos dos 2 cenários: Homogêneo (classes homogêneas) e Heterogêneo
# (controle negativo). Amostragem aleatória, seed fixa.
from pathlib import Path
import sys

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.homogeneidade.definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, RANDOM_SEED,
        ALVOS_HOMOGENEO_PATH, ALVOS_HETEROGENEO_PATH,
        BASE_HOMOGENEA_PATH, DEFAULT_INPUT,
        carregar_csv, normalizar, montar_chave_qi, validar_colunas,
    )
    from src.utils.comum import exportar_xlsx
else:
    from .definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, RANDOM_SEED,
        ALVOS_HOMOGENEO_PATH, ALVOS_HETEROGENEO_PATH,
        BASE_HOMOGENEA_PATH, DEFAULT_INPUT,
        carregar_csv, normalizar, montar_chave_qi, validar_colunas,
    )
    from src.utils.comum import exportar_xlsx


def _juntar_valores_distintos(valores_do_grupo: pd.Series) -> str:
    # Usado em transform(): uma string "valor1|valor2" com os valores
    # distintos (ordenados) do atributo sensível dentro do grupo.
    distintos = {str(v) for v in valores_do_grupo.dropna().unique()}
    return "|".join(sorted(distintos))


def gerar_alvos_homogeneo(df_homogeneo_atributo: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    # Amostra `limite` classes homogêneas com tamanho > 1: grupos de tamanho
    # 1 são excluídos por serem trivialmente identificáveis sem o ataque.
    validar_colunas(df_homogeneo_atributo)
    if "tamanho_grupo_qi" not in df_homogeneo_atributo.columns:
        raise ValueError("Coluna 'tamanho_grupo_qi' ausente. Use a base homogenea gerada por filtragem_inicial.py.")

    df = df_homogeneo_atributo.copy()
    df["chave_qi"] = montar_chave_qi(normalizar(df))
    df = df[df["tamanho_grupo_qi"].astype(str).str.strip().astype(int) > 1]

    grupos = df.drop_duplicates("chave_qi")
    amostra = grupos.sample(n=min(limite, len(grupos)), random_state=RANDOM_SEED).reset_index(drop=True)
    amostra.insert(0, "alvo_id", amostra.index + 1)
    amostra.insert(1, "nome", [f"Alvo Homogeneo {i+1}" for i in range(len(amostra))])

    # Não inclui tamanho_grupo_qi: reanexado via merge em busca.py; incluir
    # aqui geraria colunas duplicadas (_x/_y).
    return amostra[["alvo_id", "nome"] + QI_COLUNAS]


def gerar_alvos_heterogeneo(df_base: pd.DataFrame, sensivel_col: str = "EVOLUCAO", limite: int = 10) -> pd.DataFrame:
    # Amostra `limite` grupos heterogêneos (mais de um valor distinto de
    # sensivel_col) — controle negativo.
    validar_colunas(df_base, sensivel_col)
    df_base = normalizar(df_base.copy())
    df_base["chave_qi"] = montar_chave_qi(df_base)
    grupo_sensivel = df_base.groupby("chave_qi")[sensivel_col]
    valores_distintos = grupo_sensivel.transform("nunique")
    valores_lista = grupo_sensivel.transform(_juntar_valores_distintos)

    df_het = df_base[valores_distintos > 1].copy()
    df_het["valores_no_grupo"] = valores_lista[valores_distintos > 1]
    grupos = df_het.drop_duplicates("chave_qi")
    amostra = grupos.sample(n=min(limite, len(grupos)), random_state=RANDOM_SEED).reset_index(drop=True)
    amostra.insert(0, "alvo_id", amostra.index + 1)
    amostra.insert(1, "nome", [f"Alvo Heterogeneo {i+1}" for i in range(len(amostra))])

    return amostra[["alvo_id", "nome"] + QI_COLUNAS + ["valores_no_grupo"]]


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

    df_base = carregar_csv(DEFAULT_INPUT)
    df_homogeneo = carregar_csv(BASE_HOMOGENEA_PATH)

    alvos_homog = []
    alvos_heter = []
    for sensivel_col in SENSIVEL_COLUNAS:
        homog_atributo = df_homogeneo[df_homogeneo["atributo_sensivel"] == sensivel_col]
        homog = gerar_alvos_homogeneo(homog_atributo, limite=10)
        homog.insert(0, "atributo_sensivel", sensivel_col)
        alvos_homog.append(homog)

        heter = gerar_alvos_heterogeneo(df_base, sensivel_col=sensivel_col, limite=10)
        heter.insert(0, "atributo_sensivel", sensivel_col)
        alvos_heter.append(heter)

    todos_homog = pd.concat(alvos_homog, ignore_index=True)
    todos_heter = pd.concat(alvos_heter, ignore_index=True)
    todos_homog.to_csv(ALVOS_HOMOGENEO_PATH, sep=";", index=False, encoding="utf-8")
    todos_heter.to_csv(ALVOS_HETEROGENEO_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(todos_homog, ALVOS_HOMOGENEO_PATH.with_suffix(".xlsx"))
    exportar_xlsx(todos_heter, ALVOS_HETEROGENEO_PATH.with_suffix(".xlsx"))

    print(f"Homogeneo (classes grandes homogeneas): {sum(len(c) for c in alvos_homog)} alvos -> {ALVOS_HOMOGENEO_PATH}")
    print(f"Heterogeneo (controle negativo): {sum(len(c) for c in alvos_heter)} alvos -> {ALVOS_HETEROGENEO_PATH}")


if __name__ == "__main__":
    main()
