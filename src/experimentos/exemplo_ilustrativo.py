# Seleciona um grupo real da base como exemplo ilustrativo, acompanhado ao
# longo do Desenvolvimento. Sem amostragem aleatória: filtro+ordenação
# determinística sobre candidatos.csv, id_grupo já vem estável de
# montar_candidatos() — o grupo escolhido é sempre o mesmo entre execuções.
import argparse
import sys
from pathlib import Path

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.utils.comum import (
    QI_COLUNAS,
    SENSIVEL_COLUNAS,
    get_input_path,
    carregar_csv,
    normalizar_qi_sensivel,
    montar_chave_qi,
    montar_chave_bloco,
)
from src.modelos.l_diversidade.definicoes import estatisticas_por_registro
from src.tecnicas.generalizacao_supressao import aplicar_generalizacao_supressao
from src.tecnicas.regionais_pr import IBGE_TO_REGIONAL_PR

TAMANHO_MIN, TAMANHO_MAX = 3, 8
MINORIA_MINIMA = 0.15  # evita blocos l-diversos com divisão quase 99%/1%
ASSIMETRIA_PATH = project_dir / "src" / "ataques" / "assimetria" / "resultados" / "base_assimetria.csv"
BASE_BRUTA_PATH = project_dir / "base_filtrada" / "dados_filtro_base.csv"


def carregar_candidatos_enriquecido() -> pd.DataFrame:
    df = carregar_csv(get_input_path())
    df = normalizar_qi_sensivel(df)
    for k in (2, 3, 4, 5):
        df[f"nao_atinge_k{k}"] = df[f"nao_atinge_k{k}"] == "True"
    df["tamanho_grupo"] = df["tamanho_grupo"].astype(int)
    df["id_grupo"] = pd.to_numeric(df["id_grupo"], errors="coerce")

    for atributo in SENSIVEL_COLUNAS:
        sufixo = atributo.lower()
        distintos, entropia = estatisticas_por_registro(df, atributo)
        df[f"distintos_{sufixo}"] = distintos
        df[f"entropia_{sufixo}"] = entropia
        df[f"chave_bloco_{sufixo}"] = montar_chave_bloco(df, atributo)
    return df


def carregar_lookup_razao_risco() -> dict:
    # (atributo_sensivel, chave_bloco, valor_sensivel) -> razao_risco (saída do ataque de assimetria).
    base = carregar_csv(ASSIMETRIA_PATH)
    return {
        (row.atributo_sensivel, row.chave_bloco, row.valor_sensivel): float(row.razao_risco)
        for row in base.itertuples()
    }


def analisar_grupo(grupo: pd.DataFrame, lookup_risco: dict) -> dict:
    # Atributo homogêneo no grupo -> bloco l-diverso DO MESMO também é
    # único (nunca discordam). O bloco do CONTRÁRIO, condicionado a esse
    # valor constante, coincide com o próprio grupo -- calculado direto,
    # sem lookup.
    stats = {}
    for atributo in SENSIVEL_COLUNAS:
        sufixo = atributo.lower()
        valores = grupo[atributo].dropna()
        distintos = valores.nunique()

        if distintos >= 2:
            minoria = valores.value_counts(normalize=True).min()
        else:
            minoria = None

        stats[atributo] = {
            "homogeneo": distintos == 1,
            "distintos": distintos,
            "minoria": minoria,
        }
        risco = None
        if distintos >= 2:
            chaves_bloco = grupo[f"chave_bloco_{sufixo}"].dropna().unique()
            if len(chaves_bloco) == 1:
                for valor in valores.unique():
                    r = lookup_risco.get((atributo, chaves_bloco[0], valor))
                    if r is not None and (risco is None or r > risco):
                        risco = r
        stats[atributo]["razao_risco_max"] = risco
    return stats


def listar_candidatos(df: pd.DataFrame) -> pd.DataFrame:
    lookup_risco = carregar_lookup_razao_risco()

    linhas = []
    for id_grupo, grupo in df.dropna(subset=["id_grupo"]).groupby("id_grupo"):
        tamanho = len(grupo)
        if not (TAMANHO_MIN <= tamanho <= TAMANHO_MAX):
            continue

        stats = analisar_grupo(grupo, lookup_risco)
        registro = {"id_grupo": int(id_grupo), "tamanho_grupo": tamanho}
        for atributo in SENSIVEL_COLUNAS:
            sufixo = atributo.lower()
            registro[f"homogeneo_{sufixo}"] = stats[atributo]["homogeneo"]
            registro[f"minoria_bloco_{sufixo}"] = stats[atributo]["minoria"]
            registro[f"razao_risco_{sufixo}"] = stats[atributo]["razao_risco_max"]

        # Melhor exemplo: um atributo homogêneo (falha clássica de homogeneidade)
        # e o OUTRO heterogêneo, mas não muito enviesado e ainda com risco
        # elevado de assimetria (a lacuna que a l-diversidade sozinha não fecha).
        pontuacao = 0
        for homogeneo_alvo, diverso_alvo in (SENSIVEL_COLUNAS, SENSIVEL_COLUNAS[::-1]):
            h = stats[homogeneo_alvo]
            d = stats[diverso_alvo]
            if h["homogeneo"] and d["minoria"] is not None:
                pontos = 1
                if d["minoria"] >= MINORIA_MINIMA:
                    pontos += 1
                if d["razao_risco_max"] is not None and d["razao_risco_max"] >= 2.0:
                    pontos += 1
                pontuacao = max(pontuacao, pontos)
        registro["pontuacao"] = pontuacao
        linhas.append(registro)

    candidatos = pd.DataFrame(linhas)
    return candidatos.sort_values(["pontuacao", "tamanho_grupo"], ascending=[False, True])


def detalhar_grupo(df: pd.DataFrame, id_grupo: int) -> pd.DataFrame:
    grupo = df[df["id_grupo"] == id_grupo].copy()
    if grupo.empty:
        raise ValueError(f"Grupo {id_grupo} nao encontrado (verifique se e' um id_grupo valido).")

    assinatura = {col: grupo[col].iloc[0] for col in QI_COLUNAS}

    df_bruto = pd.read_csv(BASE_BRUTA_PATH, sep=";", dtype=str, low_memory=False)
    df_bruto.columns = [c.strip().replace('"', "") for c in df_bruto.columns]
    df_bruto = df_bruto[QI_COLUNAS + SENSIVEL_COLUNAS].copy()

    chave_qi_bruta = montar_chave_qi(df_bruto)
    df_bruto["tamanho_grupo_bruto"] = chave_qi_bruta.map(chave_qi_bruta.value_counts())
    df_bruto = df_bruto.rename(columns={
        "DT_NASC": "DT_NASC_bruto",
        "CO_MUN_RES": "CO_MUN_RES_bruto",
        "CO_MUN_NOT": "CO_MUN_NOT_bruto",
    })

    df_gen_bruto = pd.read_csv(BASE_BRUTA_PATH, sep=";", dtype=str, low_memory=False)
    df_gen_bruto.columns = [c.strip().replace('"', "") for c in df_gen_bruto.columns]
    df_gen = aplicar_generalizacao_supressao(df_gen_bruto, IBGE_TO_REGIONAL_PR)
    df_gen = normalizar_qi_sensivel(df_gen)
    mascara = pd.Series(True, index=df_gen.index)
    for col, valor in assinatura.items():
        mascara &= df_gen[col] == valor
    membros_brutos = df_bruto.loc[mascara].reset_index(drop=True)

    saida = grupo.reset_index(drop=True).join(
        membros_brutos[["DT_NASC_bruto", "CO_MUN_RES_bruto", "CO_MUN_NOT_bruto", "tamanho_grupo_bruto"]]
    )

    colunas = [
        "DT_NASC_bruto", "CO_MUN_RES_bruto", "CO_MUN_NOT_bruto", "tamanho_grupo_bruto",
        *QI_COLUNAS, "tamanho_grupo",
        "EVOLUCAO", "distintos_evolucao", "entropia_evolucao",
        "CLASSI_FIN", "distintos_classi_fin", "entropia_classi_fin",
    ]
    return saida[[c for c in colunas if c in saida.columns]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seleciona/detalha o exemplo ilustrativo do Desenvolvimento.")
    parser.add_argument("--id-grupo", type=int, default=None)
    args = parser.parse_args()

    df = carregar_candidatos_enriquecido()

    if args.id_grupo is not None:
        detalhe = detalhar_grupo(df, args.id_grupo)
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(detalhe.to_string(index=False))
        return

    candidatos = listar_candidatos(df)
    print(f"{len(candidatos)} grupos com tamanho entre {TAMANHO_MIN} e {TAMANHO_MAX}.")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(candidatos.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
