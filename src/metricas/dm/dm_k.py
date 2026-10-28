# Discernibility Metric (Bayardo & Agrawal, 2005): C_DM = sum|E|^2 (blocos
# QI puro >= k) + sum|D||E| (blocos < k, supressao simulada). Compara
# "antes" (QI bruto) x "depois" (generalizacao de k_anonimato.py).
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

K_VALUES = [2, 3, 4, 5]
RESULTADOS_DIR = base_dir / "resultados"
RESUMO_PATH = RESULTADOS_DIR / "resumo_dm_k.json"
DM_POR_K_PATH = RESULTADOS_DIR / "dm_por_k.csv"


def montar_tamanhos_registro(df: pd.DataFrame) -> tuple[pd.Series, int]:
    # Devolve (tamanho do bloco QI por registro, total de blocos).
    df_pipeline, _ = executar_pipeline(df.copy())
    chave = df_pipeline["chave_etapa_3"]
    tamanhos_por_bloco = chave.value_counts(dropna=False)
    tamanho_por_registro = chave.map(tamanhos_por_bloco)
    return tamanho_por_registro, int(len(tamanhos_por_bloco))


def calcular_dm(tamanho_por_registro: pd.Series, k: int) -> dict:
    # dm_minimo=|D|*k (bloco exato k); dm_maximo=|D|^2 (tudo suprimido).
    total = int(len(tamanho_por_registro))
    penalidade = tamanho_por_registro.where(tamanho_por_registro >= k, total)
    dm = int(penalidade.sum())
    dm_maximo = total * total
    return {
        "k": k,
        "dm": dm,
        "dm_minimo_teorico": total * k,
        "dm_maximo_teorico": dm_maximo,
        "dm_normalizado": round(dm / dm_maximo, 6),
    }


def montar_resumo_momento(tamanho_por_registro: pd.Series, total_grupos: int, nome: str) -> dict:
    por_k = []
    for k in K_VALUES:
        por_k.append(calcular_dm(tamanho_por_registro, k))

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

    colunas_analise = ["DT_NOTIFIC", "DT_SIN_PRI", "EVOLUCAO", "DT_EVOLUCA", "CLASSI_FIN"]
    obrigatorias = COLUNAS_BASE_OBRIGATORIAS + colunas_analise
    faltantes = [c for c in obrigatorias if c not in df_base.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatorias ausentes na base: {faltantes}")

    tamanho_antes, grupos_antes = montar_tamanhos_registro(df_base)

    df_generalizado = aplicar_generalizacao_supressao(df_base, IBGE_TO_REGIONAL_PR)
    tamanho_depois, grupos_depois = montar_tamanhos_registro(df_generalizado)

    resumo_antes = montar_resumo_momento(tamanho_antes, grupos_antes, "antes")
    resumo_depois = montar_resumo_momento(tamanho_depois, grupos_depois, "depois")

    reducao_por_k = []
    for item_antes, item_depois in zip(resumo_antes["por_k"], resumo_depois["por_k"]):
        reducao_por_k.append({
            "k": item_antes["k"],
            "reducao_percentual_dm": round((1 - item_depois["dm"] / item_antes["dm"]) * 100, 4),
        })

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "descricao": (
            "Discernibility Metric (Bayardo & Agrawal, 2005) sobre blocos de "
            "quase-identificador puro, por valor de k. antes = funil rodado "
            "sobre a base bruta filtrada, sem nenhuma tecnica aplicada; "
            "depois = mesma generalizacao/supressao usada em k_anonimato.py."
        ),
        "antes": resumo_antes,
        "depois": resumo_depois,
        "reducao_percentual_dm_por_k": reducao_por_k,
    }
    salvar_resumo_json(resumo, RESUMO_PATH)

    dm_por_k = montar_csv_por_k(resumo_antes, resumo_depois)
    dm_por_k.to_csv(DM_POR_K_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(dm_por_k, DM_POR_K_PATH.with_suffix(".xlsx"))

    print("Discernibility Metric (DM) por k:")
    for item_antes, item_depois, reducao in zip(resumo_antes["por_k"], resumo_depois["por_k"], reducao_por_k):
        print(
            f"  k={item_antes['k']}: antes={item_antes['dm']:,} (norm={item_antes['dm_normalizado']}) | "
            f"depois={item_depois['dm']:,} (norm={item_depois['dm_normalizado']}) | "
            f"reducao={reducao['reducao_percentual_dm']}%"
        )
    print(f"Saida resumo: {RESUMO_PATH}")
    print(f"Saida dm_por_k: {DM_POR_K_PATH}")
    print(f"Saida dm_por_k (xlsx): {DM_POR_K_PATH.with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()
