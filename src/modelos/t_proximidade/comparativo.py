# Bloco QI é a mesma partição pros dois atributos (diferente da
# l-diversidade) — combinação direta por registro (exclui nulos).
from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.modelos.t_proximidade.definicoes import (
        T_VALUES, RESULTADOS_DIR, REGISTROS_COMPARATIVO_PATH, RESUMO_COMPARATIVO_PATH,
        estatisticas_por_registro,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, caminho_relativo
else:
    from .definicoes import (
        T_VALUES, RESULTADOS_DIR, REGISTROS_COMPARATIVO_PATH, RESUMO_COMPARATIVO_PATH,
        estatisticas_por_registro,
    )
    from src.utils.comum import get_input_path, carregar_csv, exportar_xlsx, percentual, caminho_relativo


def montar_tabela_por_registro(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "emd_evolucao": estatisticas_por_registro(df, "EVOLUCAO"),
        "emd_classi_fin": estatisticas_por_registro(df, "CLASSI_FIN"),
    })


def avaliar_combinado(populacao: pd.DataFrame, t: float) -> dict:
    protegido_evo = populacao["emd_evolucao"] <= t
    protegido_cf = populacao["emd_classi_fin"] <= t

    # As 4 combinações possíveis de protegido/vulnerável nos dois atributos
    # (cada registro cai em exatamente uma).
    protegido_ambos = protegido_evo & protegido_cf
    vulneravel_so_evolucao = (~protegido_evo) & protegido_cf
    vulneravel_so_classi_fin = protegido_evo & (~protegido_cf)
    vulneravel_ambos = (~protegido_evo) & (~protegido_cf)

    total = int(len(populacao))

    return {
        "t": t,
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


def salvar_resumo(populacao: pd.DataFrame, por_t: list[dict], total_registros_entrada: int, input_path: Path, output_json: Path) -> None:
    resumo = {
        "arquivo_entrada": caminho_relativo(input_path),
        "total_registros_entrada": total_registros_entrada,
        "total_registros_avaliados": int(len(populacao)),
        "total_registros_excluidos": total_registros_entrada - int(len(populacao)),
        "por_t": por_t,
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

    por_t = []
    for t in T_VALUES:
        por_t.append(avaliar_combinado(populacao, t))

    salvar_resumo(populacao, por_t, len(df_entrada), input_path, RESUMO_COMPARATIVO_PATH)

    for item in por_t:
        print(
            f"  t={item['t']}: protegido nos dois {item['percentual_protegido_ambos']}% | "
            f"vulneravel so EVOLUCAO {item['percentual_vulneravel_so_evolucao']}% | "
            f"vulneravel so CLASSI_FIN {item['percentual_vulneravel_so_classi_fin']}% | "
            f"vulneravel nos dois {item['percentual_vulneravel_ambos']}%"
        )

    print(f"Saida tabela por registro: {REGISTROS_COMPARATIVO_PATH}")
    print(f"Saida tabela por registro (xlsx): {REGISTROS_COMPARATIVO_PATH.with_suffix('.xlsx')}")
    print(f"Saida resumo: {RESUMO_COMPARATIVO_PATH}")


if __name__ == "__main__":
    main()
