# Funil "mesma pessoa" sobre a base bruta filtrada, SEM anonimização —
# contraparte "antes" usada por comparativo_generalizacao.py.
import sys
from pathlib import Path

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.nucleo import (
    COLUNAS_BASE_OBRIGATORIAS,
    THRESHOLDS_DT_SIN,
    THRESHOLDS_DT_NOTIFIC,
    TAM_PENALIDADE_LEVE,
    executar_pipeline,
    montar_candidatos,
    COLUNAS_SAIDA,
    distribuicao_scores,
)
from src.utils.comum import salvar_resumo_json, exportar_xlsx, percentual, caminho_relativo


def main() -> None:
    resultados_dir = base_dir / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)

    input_path = project_dir / "base_filtrada" / "dados_filtro_base.csv"
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_path}")

    df = pd.read_csv(input_path, sep=";", dtype=str, low_memory=False)
    df.columns = [c.strip().replace('"', "") for c in df.columns]

    colunas_analise = ["DT_NOTIFIC", "DT_SIN_PRI", "EVOLUCAO", "DT_EVOLUCA", "CLASSI_FIN"]
    obrigatorias = COLUNAS_BASE_OBRIGATORIAS + colunas_analise
    faltantes = [c for c in obrigatorias if c not in df.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatorias ausentes na base: {faltantes}")

    df, resumos_funil = executar_pipeline(df)
    candidatos = montar_candidatos(df)
    colunas_saida = [c for c in COLUNAS_SAIDA if c in candidatos.columns]

    candidatos_path = resultados_dir / "candidatos_mesma_pessoa.csv"
    candidatos[colunas_saida].to_csv(candidatos_path, sep=";", index=False)

    candidatos_xlsx_path = resultados_dir / "candidatos_mesma_pessoa.xlsx"
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
    distribuicao_faixa_dispersao = (
        df.groupby("grupo_id")["faixa_dispersao_dt_sin"].first()
        .value_counts()
        .reindex(["muito forte", "forte", "plausivel", "suspeito", "muito improvavel"], fill_value=0)
        .astype("int64")
        .to_dict()
    )
    # inconsistente_obito varia por registro (sintomas_apos_obito); o grupo conta
    # como inconsistente se tiver ao menos um registro marcado.
    inconsistencia_resumo = df.groupby("grupo_id")["inconsistente_obito"].any()
    distribuicao_score = distribuicao_scores(candidatos)

    resumo_final = {
        "arquivo_entrada": caminho_relativo(input_path),
        "total_registros": int(len(df)),
        "total_grupos": int(df["grupo_id"].nunique()),
        "registros_candidatos": int(len(candidatos)),
        "percentual_registros_candidatos": percentual(len(candidatos), len(df)),
        "thresholds": {
            "dt_sin_dias": THRESHOLDS_DT_SIN,
            "dt_notific_dias": THRESHOLDS_DT_NOTIFIC,
            "tam_penalidade_leve": TAM_PENALIDADE_LEVE,
        },
        "etapas_funil": resumos_funil,
        "analise_grupos": {
            "distribuicao_tamanho_grupos": {str(k): int(v) for k, v in distribuicao_tamanho.items()},
            "distribuicao_confianca_mesma_pessoa": {str(k): int(v) for k, v in distribuicao_confianca.items()},
            "distribuicao_score_dt_sin": distribuicao_score.get("distribuicao_score_dt_sin", {}),
            "distribuicao_score_dt_notific": distribuicao_score.get("distribuicao_score_dt_notific", {}),
            "distribuicao_faixa_dispersao_dt_sin": {str(k): int(v) for k, v in distribuicao_faixa_dispersao.items()},
            "media_dispersao_dt_sin": round(float(df.groupby("grupo_id")["dispersao_dt_sin"].first().mean()), 4),
            "media_dispersao_dt_notific": round(float(df.groupby("grupo_id")["dispersao_dt_notific"].first().mean()), 4),
            "taxa_grupos_inconsistentes_obito": round(float(inconsistencia_resumo.mean()), 4),
            "total_grupos_inconsistentes_obito": int(inconsistencia_resumo.sum()),
            "total_registros_caso_forte": int(df["caso_forte"].sum()),
        },
    }

    resumo_path = resultados_dir / "resumo_probabilidade_mesma_pessoa.json"
    salvar_resumo_json(resumo_final, resumo_path)

    print("Estudo executado com sucesso.")
    print("Entrada:", input_path)
    print("Saida candidatos:", candidatos_path)
    print("Saida candidatos (xlsx):", candidatos_xlsx_path)
    print("Saida resumo:", resumo_path)


if __name__ == "__main__":
    main()