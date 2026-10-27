# NCP (Xu et al., KDD'06): penaliza cada registro pela largura do valor
# generalizado relativo ao domínio do atributo, somada nos 5 QI (pesos=1).
# DT_NASC = numérico (dias); CO_MUN_RES/CO_MUN_NOT = categórico com
# hierarquia (regional/UF, tamanho medido pelos códigos observados na
# base, sem precisar de fonte externa pros outros estados); CS_SEXO/
# CS_RACA = nunca generalizados (piso 1/|A| constante, não varia com k).
# Compartilhado por ncp_k.py/ncp_l.py/ncp_t.py.
import calendar
from pathlib import Path
import sys

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.utils.comum import QI_COLUNAS, normalizar_colunas
from src.tecnicas.generalizacao_supressao import mapear_municipio_regional
from src.tecnicas.regionais_pr import IBGE_TO_REGIONAL_PR

NCP_MAXIMO = float(len(QI_COLUNAS))  # supressão simulada: 1.0 por atributo (pesos=1)


def montar_dominios() -> tuple[dict, dict]:
    # |A| de cada atributo e o tamanho de cada nó da hierarquia de
    # município (regional/UF), a partir dos valores observados na base
    # bruta -- não depende de candidatos.csv nem de dados externos.
    input_path = project_dir / "base_filtrada" / "dados_filtro_base.csv"
    df = pd.read_csv(input_path, sep=";", dtype=str, low_memory=False, usecols=QI_COLUNAS)
    df.columns = [c.strip().replace('"', "") for c in df.columns]
    df = normalizar_colunas(df, QI_COLUNAS)

    datas = pd.to_datetime(df["DT_NASC"], errors="coerce")
    dominio_dias = int((datas.max() - datas.min()).days)

    tamanho_no = {}
    for col in ("CO_MUN_RES", "CO_MUN_NOT"):
        codigos = df[col].dropna().unique()
        generalizados = pd.Series(codigos).apply(mapear_municipio_regional, args=(IBGE_TO_REGIONAL_PR,))
        generalizados = normalizar_colunas(pd.DataFrame({"v": generalizados}), ["v"])["v"]
        tamanho_no[col] = generalizados.value_counts().to_dict()

    dominio = {
        "dias": dominio_dias,
        "co_mun_res": int(df["CO_MUN_RES"].dropna().nunique()),
        "co_mun_not": int(df["CO_MUN_NOT"].dropna().nunique()),
        "cs_sexo": int(df["CS_SEXO"].dropna().nunique()),
        "cs_raca": int(df["CS_RACA"].dropna().nunique()),
    }
    return dominio, tamanho_no


def _dias_no_ano(ano: float) -> int:
    if pd.isna(ano):
        return 365
    if calendar.isleap(int(ano)):
        return 366
    return 365


def ncp_por_registro(df: pd.DataFrame, dominio: dict, tamanho_no: dict) -> pd.Series:
    # NCP "depois": DT_NASC já generalizado a ano, CO_MUN_* já
    # generalizado a regional/UF (mesmas colunas de candidatos.csv).
    # DT_NASC nulo (raro, ~18 registros na base) vira penalidade máxima
    # nesse atributo (largura desconhecida = pior caso), em vez de erro.
    ano = pd.to_numeric(df["DT_NASC"], errors="coerce")
    dias_ano = ano.apply(_dias_no_ano)
    ncp_dt_nasc = (dias_ano / dominio["dias"]).where(ano.notna(), 1.0)

    ncp_mun_res = df["CO_MUN_RES"].map(tamanho_no["CO_MUN_RES"]) / dominio["co_mun_res"]
    ncp_mun_not = df["CO_MUN_NOT"].map(tamanho_no["CO_MUN_NOT"]) / dominio["co_mun_not"]

    piso = 1 / dominio["cs_sexo"] + 1 / dominio["cs_raca"]
    return ncp_dt_nasc + ncp_mun_res + ncp_mun_not + piso


def ncp_fixo_antes(dominio: dict) -> float:
    # Sem generalização: DT_NASC exato (largura 0 dias); municípios são
    # folhas (size=1) -- só o piso 1/|A| resta.
    return (
        1 / dominio["co_mun_res"] + 1 / dominio["co_mun_not"]
        + 1 / dominio["cs_sexo"] + 1 / dominio["cs_raca"]
    )


def calcular_ncp(ncp_fixo_por_registro: pd.Series, mask_conforme: pd.Series) -> dict:
    total = int(len(ncp_fixo_por_registro))
    penalidade = ncp_fixo_por_registro.where(mask_conforme, NCP_MAXIMO)
    ncp = float(penalidade.sum())
    ncp_maximo_teorico = total * NCP_MAXIMO
    return {
        "ncp": round(ncp, 4),
        "ncp_maximo_teorico": ncp_maximo_teorico,
        "ncp_normalizado": round(ncp / ncp_maximo_teorico, 6),
    }
