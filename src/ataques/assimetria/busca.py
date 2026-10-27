# razao_risco = p_local/p_global do valor real do alvo; sucesso por
# patamar de RAZOES_RISCO mesmo o bloco satisfazendo l-diversidade.
from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.assimetria.definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, RAZOES_RISCO,
        BASE_ASSIMETRIA_PATH, ALVOS_ASSIMETRIA_PATH, RESULTADO_BUSCA_PATH, RESUMO_BUSCA_PATH,
    )
    from src.utils.comum import carregar_csv, exportar_xlsx, percentual, round_seguro
else:
    from .definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, RESULTADOS_DIR, RAZOES_RISCO,
        BASE_ASSIMETRIA_PATH, ALVOS_ASSIMETRIA_PATH, RESULTADO_BUSCA_PATH, RESUMO_BUSCA_PATH,
    )
    from src.utils.comum import carregar_csv, exportar_xlsx, percentual, round_seguro


def _coluna_sucesso(razao: float) -> str:
    return f"ataque_bem_sucedido_{int(razao)}x"


def executar_ataque(base_atributo: pd.DataFrame, alvos_atributo: pd.DataFrame, sensivel_col: str) -> pd.DataFrame:
    colunas_join = QI_COLUNAS + ["atributo_conhecido_valor"]
    base_valores = base_atributo[colunas_join + ["valor_sensivel", "tamanho_bloco", "distintos", "p_local", "p_global", "razao_risco"]]

    resultado = alvos_atributo.merge(
        base_valores,
        left_on=colunas_join + ["valor_sensivel_real"],
        right_on=colunas_join + ["valor_sensivel"],
        how="left",
    ).drop(columns="valor_sensivel")

    for col in ["p_local", "p_global", "razao_risco"]:
        resultado[col] = pd.to_numeric(resultado[col], errors="coerce")
    for col in ["tamanho_bloco", "distintos"]:
        resultado[col] = pd.to_numeric(resultado[col], errors="coerce").astype("Int64")
    for r in RAZOES_RISCO:
        resultado[_coluna_sucesso(r)] = resultado["razao_risco"] >= r
    resultado.insert(0, "atributo_sensivel", sensivel_col)
    return resultado


def montar_resumo_atributo(resultado_attr: pd.DataFrame, sensivel_col: str) -> dict:
    total_alvos = int(len(resultado_attr))

    por_razao = []
    for r in RAZOES_RISCO:
        col = _coluna_sucesso(r)
        ataques_bem_sucedidos = int(resultado_attr[col].sum())
        taxa_sucesso = percentual(ataques_bem_sucedidos, total_alvos, 2)
        por_razao.append({
            "razao_minima": r,
            "ataques_bem_sucedidos": ataques_bem_sucedidos,
            "taxa_sucesso": taxa_sucesso,
        })

    cols_detalhe = [
        "alvo_id", "nome", "atributo_conhecido", "atributo_conhecido_valor",
        "valor_sensivel_real", "tamanho_bloco", "distintos",
        "p_local", "p_global", "razao_risco",
    ] + [_coluna_sucesso(r) for r in RAZOES_RISCO]
    detalhes = resultado_attr[[c for c in cols_detalhe if c in resultado_attr.columns]].copy()
    # to_json/json.loads em vez de to_dict: converte escalares numpy (int64,
    # float64, Int64 anulável) para tipos nativos que o json.dump aceita.
    alvos_json = json.loads(detalhes.to_json(orient="records"))

    return {
        "atributo_sensivel": sensivel_col,
        "total_alvos": total_alvos,
        "razao_risco_media": round_seguro(resultado_attr["razao_risco"].mean(), total_alvos),
        "por_razao": por_razao,
        "alvos": alvos_json,
    }


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    base = carregar_csv(BASE_ASSIMETRIA_PATH)
    alvos = carregar_csv(ALVOS_ASSIMETRIA_PATH)

    resultados = []
    resumos = []
    for sensivel_col in SENSIVEL_COLUNAS:
        base_attr = base[base["atributo_sensivel"] == sensivel_col]
        alvos_attr = alvos[alvos["atributo_sensivel"] == sensivel_col].drop(columns="atributo_sensivel")

        resultado_attr = executar_ataque(base_attr, alvos_attr, sensivel_col)
        resultados.append(resultado_attr)
        resumos.append(montar_resumo_atributo(resultado_attr, sensivel_col))

    resultado = pd.concat(resultados, ignore_index=True)
    resultado.to_csv(RESULTADO_BUSCA_PATH, sep=";", index=False, encoding="utf-8")
    exportar_xlsx(resultado, RESULTADO_BUSCA_PATH.with_suffix(".xlsx"))

    resumo = {
        "criterio_sucesso": "razao_risco (p_local / p_global do valor real do alvo) >= razao_minima, varrido em RAZOES_RISCO",
        "razoes_avaliadas": RAZOES_RISCO,
        "por_atributo_sensivel": resumos,
    }
    with RESUMO_BUSCA_PATH.open("w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    for item in resumo["por_atributo_sensivel"]:
        partes_detalhe = []
        for r in item["por_razao"]:
            partes_detalhe.append(f"{r['razao_minima']}x: {r['ataques_bem_sucedidos']}/{item['total_alvos']} ({r['taxa_sucesso']}%)")
        detalhe = " | ".join(partes_detalhe)

        print(f"[{item['atributo_sensivel']}] Alvos: {item['total_alvos']} | razao_risco media: {item['razao_risco_media']} | {detalhe}")
    print(f"Saida CSV: {RESULTADO_BUSCA_PATH}")
    print(f"Saida CSV (xlsx): {RESULTADO_BUSCA_PATH.with_suffix('.xlsx')}")
    print(f"Saida resumo: {RESUMO_BUSCA_PATH}")


if __name__ == "__main__":
    main()
