# Funil "mesma pessoa" ANTES x DEPOIS da generalização/supressão (mesma
# de k_anonimato.py) — mede a redução na fragmentação dos grupos QI.
from pathlib import Path
import sys

import pandas as pd

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from src.nucleo import COLUNAS_BASE_OBRIGATORIAS, executar_pipeline
from src.tecnicas.generalizacao_supressao import aplicar_generalizacao_supressao
from src.tecnicas.regionais_pr import IBGE_TO_REGIONAL_PR
from src.utils.comum import salvar_resumo_json, exportar_xlsx, percentual, razao_segura, caminho_relativo


def montar_momento(df: pd.DataFrame, momento: str) -> dict:
    df_pipeline, _ = executar_pipeline(df.copy())
    tamanhos = df_pipeline.groupby("grupo_id").size()

    total_registros = int(len(df_pipeline))
    total_grupos = int(len(tamanhos))
    registros_tamanho_1 = int((tamanhos == 1).sum())
    registros_candidatos = total_registros - registros_tamanho_1

    if total_grupos:
        maior_grupo = int(tamanhos.max())
    else:
        maior_grupo = 0

    return {
        "momento": momento,
        "total_registros": total_registros,
        "total_grupos": total_grupos,
        "maior_grupo": maior_grupo,
        "tamanho_medio_grupo": razao_segura(total_registros, total_grupos),
        "registros_tamanho_1": registros_tamanho_1,
        "percentual_registros_tamanho_1": percentual(registros_tamanho_1, total_registros),
        "registros_candidatos": registros_candidatos,
        "percentual_registros_candidatos": percentual(registros_candidatos, total_registros),
        "distribuicao_tamanho_grupos": {
            str(k): int(v) for k, v in tamanhos.value_counts().sort_index().items()
        },
    }


def montar_distribuicao_csv(antes: dict, depois: dict) -> pd.DataFrame:
    linhas = []
    for resumo in (antes, depois):
        for tamanho, contagem in resumo["distribuicao_tamanho_grupos"].items():
            linhas.append({
                "momento": resumo["momento"],
                "tamanho_grupo": int(tamanho),
                "quantidade_grupos": contagem,
            })
    return pd.DataFrame(linhas).sort_values(["momento", "tamanho_grupo"]).reset_index(drop=True)


def main() -> None:
    resultados_dir = base_dir / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)

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

    antes = montar_momento(df_base, "antes")
    df_generalizado = aplicar_generalizacao_supressao(df_base, IBGE_TO_REGIONAL_PR)
    depois = montar_momento(df_generalizado, "depois")

    distribuicao = montar_distribuicao_csv(antes, depois)
    distribuicao_path = resultados_dir / "distribuicao_tamanho_grupos_antes_depois.csv"
    distribuicao.to_csv(distribuicao_path, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(distribuicao, distribuicao_path.with_suffix(".xlsx"))

    if antes["total_grupos"]:
        reducao_percentual_grupos = round((1 - depois["total_grupos"] / antes["total_grupos"]) * 100, 4)
    else:
        reducao_percentual_grupos = 0.0

    if antes["registros_tamanho_1"]:
        reducao_percentual_registros_tamanho_1 = round(
            (1 - depois["registros_tamanho_1"] / antes["registros_tamanho_1"]) * 100, 4
        )
    else:
        reducao_percentual_registros_tamanho_1 = 0.0

    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "descricao": (
            "Efeito da generalizacao/supressao sobre o agrupamento por "
            "quase-identificador: antes = funil rodado sobre a base bruta "
            "filtrada, sem nenhuma tecnica aplicada; depois = mesma "
            "generalizacao/supressao usada em k_anonimato.py."
        ),
        "antes": antes,
        "depois": depois,
        "reducao_percentual_grupos": reducao_percentual_grupos,
        "reducao_percentual_registros_tamanho_1": reducao_percentual_registros_tamanho_1,
    }
    resumo_path = resultados_dir / "resumo_comparativo_generalizacao.json"
    salvar_resumo_json(resumo, resumo_path)

    print("Efeito da generalizacao/supressao sobre o agrupamento:")
    for momento in (antes, depois):
        print(
            f"  [{momento['momento']}] {momento['total_grupos']} grupos | "
            f"tamanho medio {momento['tamanho_medio_grupo']} | "
            f"tamanho 1: {momento['registros_tamanho_1']} ({momento['percentual_registros_tamanho_1']}%) | "
            f"candidatos (tamanho>1): {momento['percentual_registros_candidatos']}%"
        )
    print(f"  Reducao no numero de grupos: {resumo['reducao_percentual_grupos']}%")
    print(f"  Reducao em registros de tamanho 1: {resumo['reducao_percentual_registros_tamanho_1']}%")
    print(f"Saida distribuicao: {distribuicao_path}")
    print(f"Saida distribuicao (xlsx): {distribuicao_path.with_suffix('.xlsx')}")
    print(f"Saida resumo: {resumo_path}")


if __name__ == "__main__":
    main()
