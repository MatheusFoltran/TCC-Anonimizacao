# Junta alvos (alvos.py) com a base homogênea (filtragem_inicial.py) pelo
# QI — se a classe é homogênea, o valor sensível é revelado com certeza.
from pathlib import Path
import sys
import json

import pandas as pd

if __package__ in (None, ""):
    project_dir = Path(__file__).resolve().parents[3]
    if str(project_dir) not in sys.path:
        sys.path.append(str(project_dir))
    from src.ataques.homogeneidade.definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, K_VALUES, RESULTADOS_DIR,
        BASE_HOMOGENEA_PATH,
        ALVOS_HOMOGENEO_PATH, ALVOS_HETEROGENEO_PATH,
        RESULTADO_HOMOGENEO_PATH, RESUMO_HOMOGENEO_PATH,
        RESULTADO_HETEROGENEO_PATH, RESUMO_HETEROGENEO_PATH,
        carregar_csv,
    )
    from src.utils.comum import exportar_xlsx, percentual
else:
    from .definicoes import (
        QI_COLUNAS, SENSIVEL_COLUNAS, K_VALUES, RESULTADOS_DIR,
        BASE_HOMOGENEA_PATH,
        ALVOS_HOMOGENEO_PATH, ALVOS_HETEROGENEO_PATH,
        RESULTADO_HOMOGENEO_PATH, RESUMO_HOMOGENEO_PATH,
        RESULTADO_HETEROGENEO_PATH, RESUMO_HETEROGENEO_PATH,
        carregar_csv,
    )
    from src.utils.comum import exportar_xlsx, percentual

CENARIOS = {
    "homogeneo": {
        "numero": 1,
        "descricao": "Alvos nas maiores classes homogeneas do dataset, para cada atributo sensivel.",
        "alvos_path": ALVOS_HOMOGENEO_PATH,
        "resultado_path": RESULTADO_HOMOGENEO_PATH,
        "resumo_path": RESUMO_HOMOGENEO_PATH,
        "alvos_por_atributo": True,
        "incluir_detalhes": True,
    },
    "heterogeneo": {
        "numero": 2,
        "descricao": "Controle negativo: alvos em classes heterogeneas (mais de um valor distinto do atributo sensivel), onde o ataque nao deve ter sucesso.",
        "alvos_path": ALVOS_HETEROGENEO_PATH,
        "resultado_path": RESULTADO_HETEROGENEO_PATH,
        "resumo_path": RESUMO_HETEROGENEO_PATH,
        "alvos_por_atributo": True,
        # Alvos deste cenário são sempre heterogêneos, então nunca aparecem
        # na base homogênea (merge falharia p/ 100% deles) — só
        # ataque_bem_sucedido importa aqui.
        "incluir_detalhes": False,
    },
}


def executar_ataque(df_homogeneo_atributo: pd.DataFrame, alvos: pd.DataFrame, sensivel_col: str, incluir_detalhes: bool = True) -> pd.DataFrame:
    colunas_match = [c for c in QI_COLUNAS if c in alvos.columns and c in df_homogeneo_atributo.columns]
    if not colunas_match:
        raise ValueError("Nenhuma coluna QI em comum entre alvos e base homogenea.")

    if incluir_detalhes:
        colunas_nao_atinge = [c for c in df_homogeneo_atributo.columns if c.startswith("nao_atinge_k")]
        colunas_info = ["valor_sensivel", "tamanho_grupo_qi"] + colunas_nao_atinge
        if "confianca_mesma_pessoa" in df_homogeneo_atributo.columns:
            colunas_info.append("confianca_mesma_pessoa")
        base_unica = df_homogeneo_atributo[colunas_match + colunas_info].drop_duplicates(subset=colunas_match)

        resultado = alvos.merge(base_unica, on=colunas_match, how="left")
        resultado["ataque_bem_sucedido"] = resultado["valor_sensivel"].notna()
    else:
        chaves_homogeneas = df_homogeneo_atributo[colunas_match].drop_duplicates()
        marcado = alvos.merge(chaves_homogeneas, on=colunas_match, how="left", indicator=True)
        # "valores_no_grupo" fica só no CSV de alvos, não duplicada aqui.
        resultado = alvos.drop(columns=["valores_no_grupo"], errors="ignore").copy()
        resultado["ataque_bem_sucedido"] = (marcado["_merge"] == "both").values

    resultado.insert(0, "atributo_sensivel", sensivel_col)
    return resultado


def montar_resumo_atributo(resultado_attr: pd.DataFrame, k_values: list[int], sensivel_col: str) -> dict:
    total_alvos = int(len(resultado_attr))
    ataques_bem_sucedidos = int(resultado_attr["ataque_bem_sucedido"].sum())
    taxa_sucesso = percentual(ataques_bem_sucedidos, total_alvos, 2)

    colunas_nao_atinge = [f"nao_atinge_k{k}" for k in k_values if f"nao_atinge_k{k}" in resultado_attr.columns]
    cols_detalhe = ["alvo_id", "nome", "valor_sensivel", "tamanho_grupo_qi", "ataque_bem_sucedido"] + colunas_nao_atinge + ["confianca_mesma_pessoa"]
    cols_detalhe = [c for c in cols_detalhe if c in resultado_attr.columns]
    bem_suc = resultado_attr[resultado_attr["ataque_bem_sucedido"]]
    detalhes = bem_suc[cols_detalhe].copy()

    por_k = []
    for k in k_values:
        coluna_k = f"nao_atinge_k{k}"
        if coluna_k not in bem_suc.columns:
            continue
        mask_nao = bem_suc[coluna_k].astype(str).str.lower().isin(["true", "1"])
        por_k.append({
            "k": k,
            "contra_grupos_que_satisfazem_k": int((~mask_nao).sum()),
            "contra_grupos_abaixo_k": int(mask_nao.sum()),
        })

    return {
        "atributo_sensivel": sensivel_col,
        "total_alvos": total_alvos,
        "ataques_encontrados": ataques_bem_sucedidos,
        "taxa_sucesso": taxa_sucesso,
        "breakdown_nao_atinge_k": por_k,
        "alvos_confirmados": detalhes.to_dict(orient="records"),
    }


def executar_cenario(cenario: str, df_homogeneo: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cfg = CENARIOS[cenario]
    alvos_arquivo = carregar_csv(cfg["alvos_path"])

    resultados = []
    resumos = []
    for sensivel_col in SENSIVEL_COLUNAS:
        if cfg["alvos_por_atributo"]:
            alvos = alvos_arquivo[alvos_arquivo["atributo_sensivel"] == sensivel_col].drop(columns="atributo_sensivel")
        else:
            alvos = alvos_arquivo

        df_homog_attr = df_homogeneo[df_homogeneo["atributo_sensivel"] == sensivel_col]
        resultado_attr = executar_ataque(df_homog_attr, alvos, sensivel_col, incluir_detalhes=cfg["incluir_detalhes"])
        resultados.append(resultado_attr)
        resumos.append(montar_resumo_atributo(resultado_attr, K_VALUES, sensivel_col))

    resultado = pd.concat(resultados, ignore_index=True)
    resumo = {
        "cenario": cfg["numero"],
        "nome_cenario": cenario,
        "descricao": cfg["descricao"],
        "descricao_breakdown_nao_atinge_k": (
            "Ataques bem-sucedidos contra grupos que satisfazem k demonstram "
            "vulnerabilidade real do k-anonimato ao ataque de homogeneidade."
        ),
        "por_atributo_sensivel": resumos,
    }
    return resultado, resumo


def main() -> None:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    df_homogeneo = carregar_csv(BASE_HOMOGENEA_PATH)

    for cenario, cfg in CENARIOS.items():
        resultado, resumo = executar_cenario(cenario, df_homogeneo)

        resultado.to_csv(cfg["resultado_path"], sep=";", index=False, encoding="utf-8")
        exportar_xlsx(resultado, cfg["resultado_path"].with_suffix(".xlsx"))
        with cfg["resumo_path"].open("w", encoding="utf-8") as f:
            json.dump(resumo, f, indent=2, ensure_ascii=False)

        print(f"Cenario {cfg['numero']} ({cenario}): {cfg['descricao']}")
        for item in resumo["por_atributo_sensivel"]:
            print(f"  [{item['atributo_sensivel']}] Alvos: {item['total_alvos']} | Bem-sucedidos: {item['ataques_encontrados']} | Taxa: {item['taxa_sucesso']}%")
        print(f"  Saida CSV: {cfg['resultado_path']}")
        print(f"  Saida CSV (xlsx): {cfg['resultado_path'].with_suffix('.xlsx')}")
        print(f"  Saida resumo: {cfg['resumo_path']}")


if __name__ == "__main__":
    main()
