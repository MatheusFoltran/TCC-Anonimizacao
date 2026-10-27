# Supressão de NU_NOTIFIC; generalização de DT_NASC (ano) e municípios
# para regional de saúde (ou UF, fora do Paraná).
import sys
from pathlib import Path

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.nucleo import (
    COLUNAS_BASE_OBRIGATORIAS,
    executar_pipeline,
    montar_candidatos,
    COLUNAS_SAIDA,
    distribuicao_scores,
)
from src.utils.comum import salvar_resumo_json, normalizar_colunas, exportar_xlsx, percentual, caminho_relativo

MAPA_ESTADOS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
    "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS",
    "50": "MS", "51": "MT", "52": "GO", "53": "DF"
}

def mapear_municipio_regional(codigo: str, mapa_pr: dict) -> str:
    if pd.isna(codigo) or not isinstance(codigo, str) or len(codigo) < 2:
        return pd.NA
    
    estado = codigo[:2]
    if estado == "41":
        # Retorna a regional se houver, senão mantém PR
        return mapa_pr.get(codigo, "PR")
    else:
        # Se for de outro estado, retorna apenas a sigla do estado
        return MAPA_ESTADOS.get(estado, estado)

def aplicar_generalizacao_supressao(df: pd.DataFrame, mapa_pr: dict) -> pd.DataFrame:
    df_mod = df.copy()

    # 1. Supressão de atributo: NU_NOTIFIC vira um marcador fixo. O agrupamento
    # só usa count (que ignora NAs), então qualquer valor preenchido serve.
    if "NU_NOTIFIC" in df_mod.columns:
        df_mod["NU_NOTIFIC"] = "SUPRIMIDO"
    
    # 2. Generalização da Data de Nascimento (para o ano)
    if "DT_NASC" in df_mod.columns:
        df_mod["DT_NASC"] = df_mod["DT_NASC"].astype(str).str[:4]
    
    # 3. Generalização dos Municípios para Regional de Saúde (ou Estado)
    if "CO_MUN_RES" in df_mod.columns:
        df_mod["CO_MUN_RES"] = df_mod["CO_MUN_RES"].apply(mapear_municipio_regional, args=(mapa_pr,))

    if "CO_MUN_NOT" in df_mod.columns:
        df_mod["CO_MUN_NOT"] = df_mod["CO_MUN_NOT"].apply(mapear_municipio_regional, args=(mapa_pr,))

    return normalizar_colunas(df_mod, ["CO_MUN_RES", "CO_MUN_NOT"])


def main() -> None:
    resultados_dir = base_dir / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)

    input_path = project_dir / "base_filtrada" / "dados_filtro_base.csv"
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_path}")

    from src.tecnicas.regionais_pr import IBGE_TO_REGIONAL_PR
    mapa_pr = IBGE_TO_REGIONAL_PR

    df = pd.read_csv(input_path, sep=";", dtype=str, low_memory=False)
    df.columns = [c.strip().replace('"', "") for c in df.columns]

    colunas_analise = ["DT_NOTIFIC", "DT_SIN_PRI", "EVOLUCAO", "CLASSI_FIN"]
    obrigatorias = COLUNAS_BASE_OBRIGATORIAS + colunas_analise
    faltantes = [c for c in obrigatorias if c not in df.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatorias ausentes na base: {faltantes}")

    # Aplica Técnicas de Anonimização (Generalização / Supressão)
    df = aplicar_generalizacao_supressao(df, mapa_pr)
    df, resumos_funil = executar_pipeline(df)
    candidatos = montar_candidatos(df)
    colunas_saida = [c for c in COLUNAS_SAIDA if c in candidatos.columns]

    candidatos_path = resultados_dir / "candidatos_anonimizados.csv"
    candidatos[colunas_saida].to_csv(candidatos_path, sep=";", index=False)

    candidatos_xlsx_path = resultados_dir / "candidatos_anonimizados.xlsx"
    exportar_xlsx(candidatos[colunas_saida], candidatos_xlsx_path)

    distribuicao_tamanho = (
        df.groupby("grupo_id").size().value_counts().sort_index().astype("int64").to_dict()
    )
    distribuicao_confianca = (
        df.groupby("grupo_id")["confianca_mesma_pessoa"].first()
        .value_counts()
        .reindex(["baixa", "media", "alta"], fill_value=0)
        .astype("int64")
        .to_dict()
    )
    distribuicao_score = distribuicao_scores(candidatos)

    resumo_final = {
        "arquivo_entrada": caminho_relativo(input_path),
        "total_registros": int(len(df)),
        "total_grupos": int(df["grupo_id"].nunique()),
        "registros_candidatos": int(len(candidatos)),
        "percentual_registros_candidatos": percentual(len(candidatos), len(df)),
        "etapas_funil": resumos_funil,
        "analise_grupos": {
            "distribuicao_tamanho_grupos": {str(k): int(v) for k, v in distribuicao_tamanho.items()},
            "distribuicao_confianca_mesma_pessoa": {str(k): int(v) for k, v in distribuicao_confianca.items()},
            "distribuicao_score_dt_sin": distribuicao_score.get("distribuicao_score_dt_sin", {}),
            "distribuicao_score_dt_notific": distribuicao_score.get("distribuicao_score_dt_notific", {}),
        },
    }

    resumo_path = resultados_dir / "resumo_anonimizacao.json"
    salvar_resumo_json(resumo_final, resumo_path)

    print("Estudo anonimizado executado com sucesso.")
    print("Saida candidatos (xlsx):", candidatos_xlsx_path)


if __name__ == "__main__":
    main()