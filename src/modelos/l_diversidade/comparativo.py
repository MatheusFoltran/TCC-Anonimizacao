# EVOLUCAO e CLASSI_FIN usam blocos diferentes, então só dá pra combinar
# "protegido nos dois" por REGISTRO, não por bloco (exclui nulos).
from pathlib import Path
import sys
import json
import math

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.modelos.l_diversidade.definicoes import (
        L_VALUES, RESULTADOS_DIR, REGISTROS_COMPARATIVO_PATH, RESUMO_COMPARATIVO_PATH,
        estatisticas_por_registro,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, caminho_relativo
else:
    from .definicoes import (
        L_VALUES, RESULTADOS_DIR, REGISTROS_COMPARATIVO_PATH, RESUMO_COMPARATIVO_PATH,
        estatisticas_por_registro,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, caminho_relativo

METODOS = ["distinta", "entropia"]


def montar_tabela_por_registro(df: pd.DataFrame) -> pd.DataFrame:
    distintos_evo, entropia_evo = estatisticas_por_registro(df, "EVOLUCAO")
    distintos_cf, entropia_cf = estatisticas_por_registro(df, "CLASSI_FIN")
    return pd.DataFrame({
        "distintos_evolucao": distintos_evo,
        "entropia_evolucao": entropia_evo,
        "distintos_classi_fin": distintos_cf,
        "entropia_classi_fin": entropia_cf,
    })


def avaliar_combinado(populacao: pd.DataFrame, metodo: str, l: int) -> dict:
    if metodo == "distinta":
        protegido_evo = populacao["distintos_evolucao"] >= l
        protegido_cf = populacao["distintos_classi_fin"] >= l
    else:
        limiar = math.log(l)
        protegido_evo = populacao["entropia_evolucao"] >= limiar
        protegido_cf = populacao["entropia_classi_fin"] >= limiar

    # As 4 combinações possíveis de protegido/vulnerável nos dois atributos
    # (cada registro cai em exatamente uma).
    protegido_ambos = protegido_evo & protegido_cf
    vulneravel_so_evolucao = (~protegido_evo) & protegido_cf
    vulneravel_so_classi_fin = protegido_evo & (~protegido_cf)
    vulneravel_ambos = (~protegido_evo) & (~protegido_cf)

    total = int(len(populacao))

    return {
        "l": l,
        "registros_protegido_ambos": int(protegido_ambos.sum()),
        "percentual_protegido_ambos": percentual(int(protegido_ambos.sum()), total),
        "registros_vulneravel_so_evolucao": int(vulneravel_so_evolucao.sum()),
        "percentual_vulneravel_so_evolucao": percentual(int(vulneravel_so_evolucao.sum()), total),
        "registros_vulneravel_so_classi_fin": int(vulneravel_so_classi_fin.sum()),
        "percentual_vulneravel_so_classi_fin": percentual(int(vulneravel_so_classi_fin.sum()), total),
        "registros_vulneravel_ambos": int(vulneravel_ambos.sum()),
        "percentual_vulneravel_ambos": percentual(int(vulneravel_ambos.sum()), total),
        "registros_vulneravel_pelo_menos_um": int((~protegido_ambos).sum()),
        "percentual_vulneravel_pelo_menos_um": percentual(int((~protegido_ambos).sum()), total),
    }


def montar_resumo_metodo(populacao: pd.DataFrame, metodo: str) -> dict:
    por_l = []
    for l in L_VALUES:
        por_l.append(avaliar_combinado(populacao, metodo, l))
    return {
        "metodo": metodo,
        "por_l": por_l,
    }


def salvar_resumo(populacao: pd.DataFrame, por_metodo: list[dict], total_registros_entrada: int, input_path: Path, output_json: Path) -> None:
    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "total_registros_entrada": total_registros_entrada,
        "total_registros_avaliados": int(len(populacao)),
        "total_registros_excluidos": total_registros_entrada - int(len(populacao)),
        "por_metodo": por_metodo,
    }
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = get_input_path()
    df_entrada = carregar_csv(input_path)

    tabela = montar_tabela_por_registro(df_entrada)
    tabela.to_csv(REGISTROS_COMPARATIVO_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(tabela, REGISTROS_COMPARATIVO_PATH.with_suffix(".xlsx"))

    populacao = tabela.dropna()
    print(f"Populacao avaliada (ambos atributos preenchidos): {len(populacao)} de {len(df_entrada)} registros.")

    por_metodo = []
    for metodo in METODOS:
        por_metodo.append(montar_resumo_metodo(populacao, metodo))

    salvar_resumo(populacao, por_metodo, len(df_entrada), input_path, RESUMO_COMPARATIVO_PATH)

    for resumo_metodo in por_metodo:
        print(f"[{resumo_metodo['metodo']}] combinado EVOLUCAO x CLASSI_FIN:")
        for item in resumo_metodo["por_l"]:
            print(
                f"  l={item['l']}: protegido nos dois {item['percentual_protegido_ambos']}% | "
                f"vulneravel so EVOLUCAO {item['percentual_vulneravel_so_evolucao']}% | "
                f"vulneravel so CLASSI_FIN {item['percentual_vulneravel_so_classi_fin']}% | "
                f"vulneravel nos dois {item['percentual_vulneravel_ambos']}%"
            )

    print(f"Saida tabela por registro: {REGISTROS_COMPARATIVO_PATH}")
    print(f"Saida tabela por registro (xlsx): {REGISTROS_COMPARATIVO_PATH.with_suffix('.xlsx')}")
    print(f"Saida resumo: {RESUMO_COMPARATIVO_PATH}")


if __name__ == "__main__":
    main()
