# NCP_k: custo fixo por registro (ncp_comum.py) + NCP_MAXIMO como
# penalidade de supressão simulada (bloco < k). Compara "antes" (sem
# generalização) x "depois" (mesma generalização de k_anonimato.py),
# mesmo padrão do DM_k.
from pathlib import Path
import sys

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.nucleo import COLUNAS_BASE_OBRIGATORIAS, executar_pipeline
from src.tecnicas.generalizacao_supressao import aplicar_generalizacao_supressao
from src.tecnicas.regionais_pr import IBGE_TO_REGIONAL_PR
from src.utils.comum import salvar_resumo_json, exportar_xlsx, caminho_relativo
from src.metricas.ncp.ncp_comum import montar_dominios, ncp_por_registro, ncp_fixo_antes, calcular_ncp

K_VALUES = [2, 3, 4, 5]
RESULTADOS_DIR = base_dir / "resultados"
RESUMO_PATH = RESULTADOS_DIR / "resumo_ncp_k.json"
NCP_POR_K_PATH = RESULTADOS_DIR / "ncp_por_k.csv"


def rodar_funil(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, int]:
    # Devolve (df enriquecido pelo funil, tamanho do bloco QI por
    # registro, total de blocos).
    df_pipeline, _ = executar_pipeline(df.copy())
    chave = df_pipeline["chave_etapa_3"]
    tamanhos_por_bloco = chave.value_counts(dropna=False)
    tamanho_por_registro = chave.map(tamanhos_por_bloco)
    return df_pipeline, tamanho_por_registro, int(len(tamanhos_por_bloco))


def calcular_ncp_k(ncp_fixo_por_registro: pd.Series, tamanho_por_registro: pd.Series, k: int) -> dict:
    return {"k": k, **calcular_ncp(ncp_fixo_por_registro, tamanho_por_registro >= k)}


def montar_resumo_momento(ncp_fixo: pd.Series, tamanho_por_registro: pd.Series, total_grupos: int, nome: str) -> dict:
    por_k = []
    for k in K_VALUES:
        por_k.append(calcular_ncp_k(ncp_fixo, tamanho_por_registro, k))

    return {
        "momento": nome,
        "total_registros": int(len(tamanho_por_registro)),
        "total_grupos": total_grupos,
        "por_k": por_k,
    }


def montar_csv_por_k(resumo_antes: dict, resumo_depois: dict) -> pd.DataFrame:
    linhas = []
    for resumo in (resumo_antes, resumo_depois):
        for item in resumo["por_k"]:
            linhas.append({"momento": resumo["momento"], **item})
    return pd.DataFrame(linhas).sort_values(["momento", "k"]).reset_index(drop=True)


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

    input_path = project_dir / "base_filtrada" / "dados_filtro_base.csv"
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_path}")

    df_base = pd.read_csv(input_path, sep=";", dtype=str, low_memory=False)
    df_base.columns = [c.strip().replace('"', "") for c in df_base.columns]

    colunas_analise = ["DT_NOTIFIC", "DT_SIN_PRI", "EVOLUCAO", "CLASSI_FIN"]
    obrigatorias = COLUNAS_BASE_OBRIGATORIAS + colunas_analise
    faltantes = [c for c in obrigatorias if c not in df_base.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatorias ausentes na base: {faltantes}")

    dominio, tamanho_no = montar_dominios()

    df_pipeline_antes, tamanho_antes, grupos_antes = rodar_funil(df_base)
    ncp_antes = pd.Series(ncp_fixo_antes(dominio), index=tamanho_antes.index)

    df_generalizado = aplicar_generalizacao_supressao(df_base, IBGE_TO_REGIONAL_PR)
    df_pipeline_depois, tamanho_depois, grupos_depois = rodar_funil(df_generalizado)
    ncp_depois = ncp_por_registro(df_pipeline_depois, dominio, tamanho_no)

    resumo_antes = montar_resumo_momento(ncp_antes, tamanho_antes, grupos_antes, "antes")
    resumo_depois = montar_resumo_momento(ncp_depois, tamanho_depois, grupos_depois, "depois")

    reducao_por_k = []
    for item_antes, item_depois in zip(resumo_antes["por_k"], resumo_depois["por_k"]):
        reducao_por_k.append({
            "k": item_antes["k"],
            "reducao_percentual_ncp": round((1 - item_depois["ncp"] / item_antes["ncp"]) * 100, 4),
        })

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "descricao": (
            "Normalized Certainty Penalty (Xu et al., KDD'06) sobre os 5 QI, "
            "por valor de k. antes = funil rodado sobre a base bruta filtrada, "
            "sem nenhuma tecnica aplicada; depois = mesma generalizacao/"
            "supressao usada em k_anonimato.py."
        ),
        "antes": resumo_antes,
        "depois": resumo_depois,
        "reducao_percentual_ncp_por_k": reducao_por_k,
    }
    salvar_resumo_json(resumo, RESUMO_PATH)

    ncp_por_k = montar_csv_por_k(resumo_antes, resumo_depois)
    ncp_por_k.to_csv(NCP_POR_K_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(ncp_por_k, NCP_POR_K_PATH.with_suffix(".xlsx"))

    print("Normalized Certainty Penalty (NCP) por k:")
    for item_antes, item_depois, reducao in zip(resumo_antes["por_k"], resumo_depois["por_k"], reducao_por_k):
        print(
            f"  k={item_antes['k']}: antes={item_antes['ncp']:,} (norm={item_antes['ncp_normalizado']}) | "
            f"depois={item_depois['ncp']:,} (norm={item_depois['ncp_normalizado']}) | "
            f"reducao={reducao['reducao_percentual_ncp']}%"
        )
    print(f"Saida resumo: {RESUMO_PATH}")
    print(f"Saida ncp_por_k: {NCP_POR_K_PATH}")
    print(f"Saida ncp_por_k (xlsx): {NCP_POR_K_PATH.with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()
