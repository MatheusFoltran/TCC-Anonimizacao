# Funil de identificação por QI, dispersão temporal, confiança e
# inconsistência de óbito — compartilhado por k_anonimato.py e afins.

import numpy as np
import pandas as pd

from src.utils.comum import normalizar_colunas, montar_chave

# Configuração

COLUNAS_BASE_OBRIGATORIAS = ["NU_NOTIFIC", "DT_NASC", "CO_MUN_RES", "CS_SEXO"]

ETAPAS_FUNIL = [
    {
        "nome": "etapa_1",
        "descricao": "DT_NASC + CO_MUN_RES + CS_SEXO",
        "colunas": ["DT_NASC", "CO_MUN_RES", "CS_SEXO"],
    },
    {
        "nome": "etapa_2",
        "descricao": "DT_NASC + CO_MUN_RES + CS_SEXO + CS_RACA",
        "colunas": ["DT_NASC", "CO_MUN_RES", "CS_SEXO", "CS_RACA"],
    },
    {
        "nome": "etapa_3",
        "descricao": "DT_NASC + CO_MUN_RES + CS_SEXO + CS_RACA + CO_MUN_NOT",
        "colunas": ["DT_NASC", "CO_MUN_RES", "CS_SEXO", "CS_RACA", "CO_MUN_NOT"],
    },
]

ETAPA_CLASSIFICACAO = "etapa_3"

THRESHOLDS_DT_SIN     = [0, 3, 7, 14]
THRESHOLDS_DT_NOTIFIC = [1, 7, 14, 21]
TAM_PENALIDADE_LEVE   = 5

# Helpers

def _score_dispersao(dispersao: pd.Series, thresholds: list[int]) -> pd.Series:
    t0, t1, t2, t3 = thresholds
    return pd.Series(
        np.select(
            [dispersao <= t0, dispersao <= t1, dispersao <= t2, dispersao <= t3],
            [3, 2, 1, 0],
            default=-1,
        ),
        index=dispersao.index,
    ).astype("int64")


def _dispersao_por_grupo(datas: pd.Series, grupos: pd.Series) -> pd.Series:
    return (
        (datas.groupby(grupos).max() - datas.groupby(grupos).min())
        .dt.days.fillna(0)
        .astype("int64")
    )


def classificar_confianca(metricas_grupo: pd.DataFrame) -> pd.Series:
    score_base = np.minimum(
        metricas_grupo["score_dt_sin"],
        metricas_grupo["score_dt_notific"],
    )
    # Penaliza só quando grupo grande E dispersão já fraca — não pune grupos
    # grandes com datas concentradas, que são clinicamente plausíveis.
    penalidade = np.where(
        (metricas_grupo["tamanho_grupo"] >= TAM_PENALIDADE_LEVE) &
        (metricas_grupo["score_dt_sin"] <= 1),
        1, 0
    )
    score_final = score_base - penalidade

    # O tamanho do grupo só pesa via penalidade acima; sozinho, não rebaixa
    # a confiança.
    return pd.Series(
        np.select(
            [
                metricas_grupo["inconsistente_obito"],
                score_final >= 2,
                score_final >= 1,
            ],
            ["baixa", "alta", "media"],
            default="baixa",
        ),
        index=metricas_grupo.index,
        name="confianca_mesma_pessoa",
    )


def resumo_etapa(df: pd.DataFrame, nome_etapa: str, descricao: str, colunas: list[str]) -> dict:
    chave = montar_chave(df, colunas)
    tamanhos = chave.value_counts(dropna=False)
    tamanhos_por_registro = chave.map(tamanhos)
    grupos_suspeitos   = int((tamanhos > 1).sum())
    registros_suspeitos = int((tamanhos_por_registro > 1).sum())
    pares_possiveis    = int(((tamanhos * (tamanhos - 1)) // 2).sum())

    if tamanhos.empty:
        maior_grupo = 0
    else:
        maior_grupo = int(tamanhos.max())

    return {
        "etapa": nome_etapa,
        "descricao": descricao,
        "colunas": ",".join(colunas),
        "grupos_total": int(len(tamanhos)),
        "grupos_suspeitos": grupos_suspeitos,
        "registros_suspeitos": registros_suspeitos,
        "percentual_registros_suspeitos": round(registros_suspeitos / len(df) * 100.0, 4),
        "maior_grupo": maior_grupo,
        "pares_possiveis": pares_possiveis,
    }

# Pipeline principal (reutilizável)

def executar_pipeline(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    # Recebe o DataFrame (já normalizado e opcionalmente anonimizado) e devolve (df_enriquecido, resumos_funil).

    colunas_funil = sorted({col for etapa in ETAPAS_FUNIL for col in etapa["colunas"]})
    df = normalizar_colunas(df, colunas_funil)

    # Funil
    resumos = []
    for etapa in ETAPAS_FUNIL:
        chave_etapa = montar_chave(df, etapa["colunas"])
        tamanhos_etapa = chave_etapa.value_counts(dropna=False)
        df[f"chave_{etapa['nome']}"] = chave_etapa
        df[f"tam_grupo_{etapa['nome']}"] = chave_etapa.map(tamanhos_etapa).astype("int64")
        resumos.append(resumo_etapa(df, etapa["nome"], etapa["descricao"], etapa["colunas"]))

    # Grupos
    df["grupo_id"] = df.groupby(f"chave_{ETAPA_CLASSIFICACAO}").ngroup()
    df["tamanho_grupo"] = df.groupby("grupo_id")["DT_NOTIFIC"].transform("count").astype("int64")

    # Dispersão
    dt_sin    = pd.to_datetime(df["DT_SIN_PRI"],  errors="coerce")
    dt_notific = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce")

    for label, datas, thresholds in [
        ("dt_sin",    dt_sin,    THRESHOLDS_DT_SIN),
        ("dt_notific", dt_notific, THRESHOLDS_DT_NOTIFIC),
    ]:
        dispersao = _dispersao_por_grupo(datas, df["grupo_id"])
        dispersao.index.name = "grupo_id"
        score = _score_dispersao(dispersao, thresholds)
        score.index.name = "grupo_id"
        df[f"dispersao_{label}"] = df["grupo_id"].map(dispersao)
        df[f"score_{label}"]     = df["grupo_id"].map(score)

    # Faixa descritiva da dispersão de DT_SIN (resumo de executar_estudo.py)
    dispersao_sin = df.groupby("grupo_id")["dispersao_dt_sin"].first()
    faixa_sin = pd.Series(
        np.select(
            [dispersao_sin <= 0, dispersao_sin <= 3, dispersao_sin <= 7, dispersao_sin <= 14],
            ["muito forte", "forte", "plausivel", "suspeito"],
            default="muito improvavel",
        ),
        index=dispersao_sin.index,
        name="faixa_dispersao_dt_sin",
    )
    df["faixa_dispersao_dt_sin"] = df["grupo_id"].map(faixa_sin)

    # Inconsistência de óbito: posterior_a_obito é por REGISTRO (notificação
    # após o óbito do grupo -> prova que é pessoa diferente); conflito_obito_grupo
    # é por GRUPO (óbito por SRAG e por outras causas juntos -> mutuamente
    # exclusivas para uma única pessoa).
    evolucao = df["EVOLUCAO"].astype(str).str.strip().str.lower()
    is_obito_srag   = evolucao.isin(["obito", "óbito", "2"])
    is_obito_outras = evolucao.isin(["obito por outras causas", "óbito por outras causas", "3"])

    primeira_data_obito_grupo = (
        dt_notific.where(is_obito_srag | is_obito_outras).groupby(df["grupo_id"]).transform("min")
    )
    df["posterior_a_obito"] = (dt_notific > primeira_data_obito_grupo) & primeira_data_obito_grupo.notna()

    conflito_por_grupo = is_obito_srag.groupby(df["grupo_id"]).any() & is_obito_outras.groupby(df["grupo_id"]).any()
    conflito_por_grupo.index.name = "grupo_id"
    df["conflito_obito_grupo"] = df["grupo_id"].map(conflito_por_grupo)

    df["inconsistente_obito"] = df["posterior_a_obito"] | df["conflito_obito_grupo"]

    # Classificação de confiança
    tamanho_por_grupo  = df.groupby("grupo_id")["DT_NOTIFIC"].size()
    grupos_candidatos  = tamanho_por_grupo[tamanho_por_grupo > 1].index
    score_sin_grp    = df.groupby("grupo_id")["score_dt_sin"].first()
    score_notific_grp = df.groupby("grupo_id")["score_dt_notific"].first()
    # Se QUALQUER registro prova ser pessoa diferente (posterior_a_obito) ou
    # há conflito de causas, o grupo inteiro deixa de ser plausível como
    # duplicata única.
    inconsistencia_grupo = df.groupby("grupo_id")["inconsistente_obito"].any()

    metricas_grupo = pd.DataFrame({
        "tamanho_grupo":      tamanho_por_grupo,
        "score_dt_sin":       score_sin_grp,
        "score_dt_notific":   score_notific_grp,
        "inconsistente_obito": inconsistencia_grupo,
    }).loc[grupos_candidatos]

    classificacao = classificar_confianca(metricas_grupo)
    classificacao.index.name = "grupo_id"

    df["confianca_mesma_pessoa"] = pd.Categorical(
        df["grupo_id"].map(classificacao),
        categories=["baixa", "media", "alta"],
        ordered=True,
    )
    df["caso_forte"] = df["confianca_mesma_pessoa"] == "alta"

    return df, resumos


def montar_candidatos(df: pd.DataFrame, col_ordem: str | None = None) -> pd.DataFrame:
    # Filtra os candidatos (tamanho > 1) e adiciona id_grupo ordenado.
    candidatos = df[df["tamanho_grupo"] > 1].copy()
    candidatos["_ordem_confianca"] = candidatos["confianca_mesma_pessoa"].map(
        {"baixa": 1, "media": 2, "alta": 3}
    ).astype("int64")
    candidatos["_dt_notific_ord"] = pd.to_datetime(candidatos["DT_NOTIFIC"], errors="coerce")

    resumo_grupos = (
        candidatos.groupby("grupo_id", as_index=False)
        .agg(
            ordem_confianca=("_ordem_confianca", "max"),
            dispersao_dt_sin=("dispersao_dt_sin", "min"),
            dt_notific_min=("_dt_notific_ord", "min"),
        )
        .sort_values(
            by=["ordem_confianca", "dispersao_dt_sin", "dt_notific_min", "grupo_id"],
            ascending=[False, True, True, True],
        )
        .reset_index(drop=True)
    )
    resumo_grupos["id_grupo"] = resumo_grupos.index + 1

    candidatos = candidatos.merge(resumo_grupos[["grupo_id", "id_grupo"]], on="grupo_id", how="left")
    candidatos["_pos"] = range(len(candidatos))
    sort_by = ["id_grupo", "_dt_notific_ord"]
    if col_ordem and col_ordem in candidatos.columns:
        sort_by.append(col_ordem)
    sort_by.append("_pos")
    candidatos = candidatos.sort_values(by=sort_by, ascending=True)
    candidatos["ordem_notificacao_no_grupo"] = candidatos.groupby("id_grupo").cumcount() + 1
    candidatos = candidatos.drop(columns=["_pos"])
    return candidatos


COLUNAS_SAIDA = [
    "id_grupo", "NU_NOTIFIC", "DT_NASC", "CO_MUN_RES", "CS_SEXO",
    "CS_RACA", "CO_MUN_NOT", "EVOLUCAO", "CLASSI_FIN", "confianca_mesma_pessoa",
    "tamanho_grupo", "dispersao_dt_sin", "dispersao_dt_notific",
    "score_dt_sin", "score_dt_notific", "inconsistente_obito",
]

# Análise

def distribuicao_scores(candidatos: pd.DataFrame) -> dict:
    def _dist(coluna: str) -> dict:
        return {
            str(k): int(v)
            for k, v in (
                candidatos.groupby("grupo_id")[coluna].first()
                .map({3: "alta", 2: "alta", 1: "media", 0: "baixa", -1: "baixa"})
                .value_counts()
                .reindex(["baixa", "media", "alta"], fill_value=0)
                .astype("int64")
                .to_dict()
            ).items()
        }
    return {
        "distribuicao_score_dt_sin":    _dist("score_dt_sin"),
        "distribuicao_score_dt_notific": _dist("score_dt_notific"),
    }