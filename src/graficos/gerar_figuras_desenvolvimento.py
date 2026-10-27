# Gera as figuras da seção de Desenvolvimento do relatório TCC, salvas em
# docs/figuras/. Uma função por figura (ver comentários "# Fig N" abaixo).
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Caminhos

PROJECT_DIR = Path(__file__).resolve().parents[2]
RESULTADOS_EXP  = PROJECT_DIR / "src" / "experimentos" / "resultados"
RESULTADOS_K    = PROJECT_DIR / "src" / "modelos" / "k_anonimato" / "resultados"
RESULTADOS_HOM  = PROJECT_DIR / "src" / "ataques" / "homogeneidade" / "resultados"
RESULTADOS_L    = PROJECT_DIR / "src" / "modelos" / "l_diversidade" / "resultados"
RESULTADOS_ASSI = PROJECT_DIR / "src" / "ataques" / "assimetria" / "resultados"
RESULTADOS_T    = PROJECT_DIR / "src" / "modelos" / "t_proximidade" / "resultados"
RESULTADOS_DM   = PROJECT_DIR / "src" / "metricas" / "dm" / "resultados"
RESULTADOS_NCP  = PROJECT_DIR / "src" / "metricas" / "ncp" / "resultados"
FIGS_DIR        = PROJECT_DIR / "docs" / "figuras"
FIGS_DIR.mkdir(parents=True, exist_ok=True)


# Estilo global

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
})

BLUE   = "#2E6EA6"
GRAY   = "#888888"
COLORS = ["#2E6EA6", "#E07B39", "#D94F4F", "#888888"]


def _salvar(fig: plt.Figure, nome: str) -> None:
    for ext in ("pdf", "png"):
        caminho = FIGS_DIR / f"{nome}.{ext}"
        fig.savefig(caminho, bbox_inches="tight", dpi=150)
    print(f"  -> {nome} salvo")


def _formatar_milhar(valor: float, _posicao) -> str:
    # Callback de eixo do matplotlib (FuncFormatter exige a assinatura
    # (valor, posicao)): "12345" -> "12.345".
    return f"{int(valor):,}".replace(",", ".")


# Fig 0: efeito da generalização sobre o agrupamento (antes/depois)

def fig_efeito_generalizacao() -> None:
    with open(RESULTADOS_EXP / "resumo_comparativo_generalizacao.json", encoding="utf-8") as f:
        dados = json.load(f)
    antes, depois = dados["antes"], dados["depois"]

    labels = ["Classes de\ntamanho 1", "Classes com múltiplos\nregistros (candidatos)"]
    pcts_antes  = [antes["percentual_registros_tamanho_1"], antes["percentual_registros_candidatos"]]
    pcts_depois = [depois["percentual_registros_tamanho_1"], depois["percentual_registros_candidatos"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_antes, width=largura, color=GRAY, label="Antes", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_depois, width=largura, color=BLUE, label="Depois", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Registros (%)")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 1.5,
                f"{v:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    fig.tight_layout()
    _salvar(fig, "fig_efeito_generalizacao")
    plt.close(fig)


# Fig 1: % de registros não conformes por k

def fig_k_nao_conformes() -> None:
    with open(RESULTADOS_K / "resumo.json", encoding="utf-8") as f:
        dados = json.load(f)
    k_valores = [item["k"] for item in dados["por_k"]]
    percentuais = [item["analise_k"]["percentual_registros_abaixo_k"] for item in dados["por_k"]]

    fig, ax = plt.subplots(figsize=(5, 3.2))
    bars = ax.bar(
        [str(k) for k in k_valores],
        percentuais,
        color=BLUE,
        width=0.5,
        zorder=2,
    )
    ax.set_xlabel("Valor de $k$")
    ax.set_ylabel("Registros não conformes (%)")
    ax.set_ylim(0, max(percentuais) * 1.25)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    for bar, v in zip(bars, percentuais):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            v + 0.3,
            f"{v:.2f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    fig.tight_layout()
    _salvar(fig, "fig_k_anonimato_nao_conformes")
    plt.close(fig)


# Fig 2: taxa de homogeneidade por k_max_satisfeito (EVOLUCAO x CLASSI_FIN)

def fig_homogeneidade_por_kmax() -> None:
    with open(RESULTADOS_HOM / "resumo_analise_comparativa_k.json", encoding="utf-8") as f:
        dados = json.load(f)
    por_atributo = {item["atributo_sensivel"]: item for item in dados["por_atributo_sensivel"]}
    dados_evolucao = por_atributo["EVOLUCAO"]
    dados_classifin = por_atributo["CLASSI_FIN"]

    labels = [f"k_max={n['k_max_satisfeito']}" for n in dados_evolucao["por_nivel_k"]]
    pcts_evolucao  = [n["pct_registros_hom"] for n in dados_evolucao["por_nivel_k"]]
    pcts_classifin = [n["pct_registros_hom"] for n in dados_classifin["por_nivel_k"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Registros homogêneos (%)")
    ax.set_ylim(0, max(pcts_evolucao + pcts_classifin) * 1.25)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 1.5,
                f"{v:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    fig.tight_layout()
    _salvar(fig, "fig_homogeneidade_por_kmax")
    plt.close(fig)


# Fig 3: distribuição de EVOLUCAO nas classes homogêneas

def fig_evolucao_classes_homogeneas() -> None:
    with open(RESULTADOS_HOM / "resumo_base_homogeneidade.json", encoding="utf-8") as f:
        dados_completo = json.load(f)
    dados = next(item for item in dados_completo["por_atributo_sensivel"] if item["atributo_sensivel"] == "EVOLUCAO")

    dist = dados["distribuicao_valor_sensivel_unico"]
    mapa_desfecho = {
        "1": "Cura\n(1)",
        "2": "Óbito SRAG\n(2)",
        "3": "Óbito outras\ncausas (3)",
        "9": "Ignorado\n(9)",
    }

    codigos   = ["1", "2", "3", "9"]
    desfechos = [mapa_desfecho[c] for c in codigos]
    contagens = [int(dist.get(c, 0)) for c in codigos]
    total     = sum(contagens)
    pcts      = [v / total * 100 for v in contagens]

    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    bars = ax.barh(
        desfechos[::-1],
        contagens[::-1],
        color=COLORS[::-1],
        height=0.5,
        zorder=2,
    )
    ax.set_xlabel("Registros em classes homogêneas")
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(_formatar_milhar)
    )
    ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    for bar, v, p in zip(bars, contagens[::-1], pcts[::-1]):
        ax.text(
            v + 150,
            bar.get_y() + bar.get_height() / 2,
            f"{v:,}  ({p:.1f}%)".replace(",", "."),
            va="center",
            fontsize=8.5,
        )
    ax.set_xlim(0, max(contagens) * 1.3)
    fig.tight_layout()
    _salvar(fig, "fig_evolucao_classes_homogeneas")
    plt.close(fig)


# Fig 4: distribuição de CLASSI_FIN nas classes homogêneas

def fig_classifin_classes_homogeneas() -> None:
    with open(RESULTADOS_HOM / "resumo_base_homogeneidade.json", encoding="utf-8") as f:
        dados_completo = json.load(f)
    dados = next(item for item in dados_completo["por_atributo_sensivel"] if item["atributo_sensivel"] == "CLASSI_FIN")

    dist = dados["distribuicao_valor_sensivel_unico"]
    mapa_diagnostico = {
        "1": "SRAG por\ninfluenza (1)",
        "2": "SRAG por outro\nvírus resp. (2)",
        "3": "SRAG por outro\nagente (3)",
        "4": "SRAG não\nespecificado (4)",
        "5": "SRAG por\nCOVID-19 (5)",
    }

    # Cores atribuídas por código (não por posição): "5" (COVID-19) é o
    # diagnóstico dominante e recebe a cor de destaque (azul), assim como
    # "Cura" recebe destaque na figura equivalente de EVOLUCAO.
    cores_por_codigo = {
        "1": "#D94F4F",
        "2": "#E07B39",
        "3": "#D94F4F",
        "4": "#6BA292",
        "5": BLUE,
    }

    codigos      = ["1", "2", "3", "4", "5"]
    diagnosticos = [mapa_diagnostico[c] for c in codigos]
    contagens    = [int(dist.get(c, 0)) for c in codigos]
    total        = sum(contagens)
    pcts         = [v / total * 100 for v in contagens]
    cores        = [cores_por_codigo[c] for c in codigos]

    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    bars = ax.barh(
        diagnosticos[::-1],
        contagens[::-1],
        color=cores[::-1],
        height=0.5,
        zorder=2,
    )
    ax.set_xlabel("Registros em classes homogêneas")
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(_formatar_milhar)
    )
    ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    for bar, v, p in zip(bars, contagens[::-1], pcts[::-1]):
        ax.text(
            v + 150,
            bar.get_y() + bar.get_height() / 2,
            f"{v:,}  ({p:.1f}%)".replace(",", "."),
            va="center",
            fontsize=8.5,
        )
    ax.set_xlim(0, max(contagens) * 1.3)
    fig.tight_layout()
    _salvar(fig, "fig_classifin_classes_homogeneas")
    plt.close(fig)


# Fig 5 e 6: l-diversidade (distinta / entropia) -- % registros abaixo de l,
# EVOLUCAO x CLASSI_FIN, por método

def _fig_l_diversidade_metodo(metodo: str, nome_arquivo: str, ylim_extra: float = 1.15) -> None:
    with open(RESULTADOS_L / "resumo_l_diversidade.json", encoding="utf-8") as f:
        dados = json.load(f)
    por_atributo = {item["atributo_sensivel"]: item for item in dados["por_atributo_sensivel"]}
    dados_evolucao = por_atributo["EVOLUCAO"]
    dados_classifin = por_atributo["CLASSI_FIN"]

    labels = [f"l={n['l']}" for n in dados_evolucao["por_l"]]
    pcts_evolucao  = [n[metodo]["percentual_registros_abaixo_l"] for n in dados_evolucao["por_l"]]
    pcts_classifin = [n[metodo]["percentual_registros_abaixo_l"] for n in dados_classifin["por_l"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Registros abaixo de $l$ (%)")
    ax.set_ylim(0, max(pcts_evolucao + pcts_classifin) * ylim_extra)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 1.2,
                f"{v:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    fig.tight_layout()
    _salvar(fig, nome_arquivo)
    plt.close(fig)


def fig_l_diversidade_distinta() -> None:
    _fig_l_diversidade_metodo("distinta", "fig_l_diversidade_distinta")


def fig_l_diversidade_entropia() -> None:
    _fig_l_diversidade_metodo("entropia", "fig_l_diversidade_entropia", ylim_extra=1.08)


# Fig 7: métrica combinada (AND por registro) -- breakdown empilhado por l,
# método distinta

def fig_l_diversidade_comparativo() -> None:
    with open(RESULTADOS_L / "resumo_l_diversidade_comparativo.json", encoding="utf-8") as f:
        dados_completo = json.load(f)
    dados = next(item for item in dados_completo["por_metodo"] if item["metodo"] == "distinta")

    labels = [f"l={n['l']}" for n in dados["por_l"]]
    protegido_ambos   = [n["percentual_protegido_ambos"] for n in dados["por_l"]]
    vuln_so_evolucao  = [n["percentual_vulneravel_so_evolucao"] for n in dados["por_l"]]
    vuln_so_classifin = [n["percentual_vulneravel_so_classi_fin"] for n in dados["por_l"]]
    vuln_ambos        = [n["percentual_vulneravel_ambos"] for n in dados["por_l"]]

    categorias = [
        ("Protegido nos dois",       protegido_ambos,   "#6BA292"),
        ("Vulnerável só EVOLUCAO",   vuln_so_evolucao,  BLUE),
        ("Vulnerável só CLASSI_FIN", vuln_so_classifin, COLORS[1]),
        ("Vulnerável nos dois",      vuln_ambos,         COLORS[2]),
    ]

    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    base = [0.0] * len(labels)
    for nome_cat, valores, cor in categorias:
        bars = ax.bar(list(x), valores, bottom=base, width=0.55, color=cor, label=nome_cat, zorder=2)
        for bar, v in zip(bars, valores):
            if v >= 4:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + v / 2,
                    f"{v:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                )
        base = [b + v for b, v in zip(base, valores)]

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Registros (%)")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    fig.tight_layout()
    _salvar(fig, "fig_l_diversidade_comparativo")
    plt.close(fig)


# Fig 8: razão de risco (mediana/média/p90) entre blocos l-diversos --
# EVOLUCAO x CLASSI_FIN

def fig_assimetria_razao_risco() -> None:
    with open(RESULTADOS_ASSI / "resumo_base_assimetria.json", encoding="utf-8") as f:
        dados = json.load(f)
    por_atributo = {item["atributo_sensivel"]: item for item in dados["por_atributo_sensivel"]}
    dados_evolucao = por_atributo["EVOLUCAO"]
    dados_classifin = por_atributo["CLASSI_FIN"]

    metricas = ["razao_risco_mediana", "razao_risco_media", "razao_risco_p90"]
    labels = ["Mediana", "Média", "P90"]
    valores_evolucao  = [dados_evolucao[m] for m in metricas]
    valores_classifin = [dados_classifin[m] for m in metricas]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], valores_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], valores_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Razão de risco (p_local / p_global)")
    ax.axhline(1.0, color=GRAY, linestyle=":", linewidth=1, zorder=1)
    ax.set_ylim(0, max(valores_evolucao + valores_classifin) * 1.3)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 0.1,
                f"{v:.2f}×",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    fig.tight_layout()
    _salvar(fig, "fig_assimetria_razao_risco")
    plt.close(fig)


# Fig 9: % de registros com razao_risco acima do limiar de sucesso --
# EVOLUCAO x CLASSI_FIN

def fig_assimetria_risco_elevado() -> None:
    with open(RESULTADOS_ASSI / "resumo_base_assimetria.json", encoding="utf-8") as f:
        dados = json.load(f)
    por_atributo = {item["atributo_sensivel"]: item for item in dados["por_atributo_sensivel"]}
    dados_evolucao = por_atributo["EVOLUCAO"]
    dados_classifin = por_atributo["CLASSI_FIN"]

    labels = [f"{n['razao_minima']:.0f}×" for n in dados_evolucao["por_razao"]]
    pcts_evolucao  = [n["percentual_registros_risco_elevado"] for n in dados_evolucao["por_razao"]]
    pcts_classifin = [n["percentual_registros_risco_elevado"] for n in dados_classifin["por_razao"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("Razão de risco mínima (p_local / p_global)")
    ax.set_ylabel("Registros com razão de risco acima do limiar (%)")
    ax.set_ylim(0, max(pcts_evolucao + pcts_classifin) * 1.35)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 0.4,
                f"{v:.2f}%",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    fig.tight_layout()
    _salvar(fig, "fig_assimetria_risco_elevado")
    plt.close(fig)


# Fig 10: % de registros que violam t-proximidade, por t -- EVOLUCAO x CLASSI_FIN

def fig_t_proximidade_violacao() -> None:
    with open(RESULTADOS_T / "resumo_t_proximidade.json", encoding="utf-8") as f:
        dados = json.load(f)
    por_atributo = {item["atributo_sensivel"]: item for item in dados["por_atributo_sensivel"]}
    dados_evolucao = por_atributo["EVOLUCAO"]
    dados_classifin = por_atributo["CLASSI_FIN"]

    labels = [f"t={n['t']:g}" for n in dados_evolucao["por_t"]]
    pcts_evolucao  = [n["percentual_registros_viola_t"] for n in dados_evolucao["por_t"]]
    pcts_classifin = [n["percentual_registros_viola_t"] for n in dados_classifin["por_t"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Registros que violam $t$-proximidade (%)")
    ax.set_ylim(0, max(pcts_evolucao + pcts_classifin) * 1.15)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 1.2,
                f"{v:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    fig.tight_layout()
    _salvar(fig, "fig_t_proximidade_violacao")
    plt.close(fig)


# Fig 10b: EMD média por k_max_satisfeito (EVOLUCAO x CLASSI_FIN)

def fig_t_proximidade_por_kmax() -> None:
    with open(RESULTADOS_T / "resumo_analise_comparativa_k.json", encoding="utf-8") as f:
        dados = json.load(f)
    por_atributo = {item["atributo_sensivel"]: item for item in dados["por_atributo_sensivel"]}
    dados_evolucao = por_atributo["EVOLUCAO"]
    dados_classifin = por_atributo["CLASSI_FIN"]

    labels = [f"k_max={n['k_max_satisfeito']}" for n in dados_evolucao["por_k_max"]]
    emd_evolucao  = [n["emd_media"] for n in dados_evolucao["por_k_max"]]
    emd_classifin = [n["emd_media"] for n in dados_classifin["por_k_max"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], emd_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], emd_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("EMD média do bloco")
    ax.set_ylim(0, max(emd_evolucao + emd_classifin) * 1.25)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 0.01,
                f"{v:.3f}",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    fig.tight_layout()
    _salvar(fig, "fig_t_proximidade_por_kmax")
    plt.close(fig)


# Fig 11: métrica combinada (AND por registro) -- breakdown empilhado por t

def fig_t_proximidade_comparativo() -> None:
    with open(RESULTADOS_T / "resumo_t_proximidade_comparativo.json", encoding="utf-8") as f:
        dados = json.load(f)

    labels = [f"t={n['t']:g}" for n in dados["por_t"]]
    protegido_ambos   = [n["percentual_protegido_ambos"] for n in dados["por_t"]]
    vuln_so_evolucao  = [n["percentual_vulneravel_so_evolucao"] for n in dados["por_t"]]
    vuln_so_classifin = [n["percentual_vulneravel_so_classi_fin"] for n in dados["por_t"]]
    vuln_ambos        = [n["percentual_vulneravel_ambos"] for n in dados["por_t"]]

    categorias = [
        ("Protegido nos dois",       protegido_ambos,   "#6BA292"),
        ("Vulnerável só EVOLUCAO",   vuln_so_evolucao,  BLUE),
        ("Vulnerável só CLASSI_FIN", vuln_so_classifin, COLORS[1]),
        ("Vulnerável nos dois",      vuln_ambos,         COLORS[2]),
    ]

    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    base = [0.0] * len(labels)
    for nome_cat, valores, cor in categorias:
        bars = ax.bar(list(x), valores, bottom=base, width=0.55, color=cor, label=nome_cat, zorder=2)
        for bar, v in zip(bars, valores):
            if v >= 4:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + v / 2,
                    f"{v:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                )
        base = [b + v for b, v in zip(base, valores)]

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Registros (%)")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    fig.tight_layout()
    _salvar(fig, "fig_t_proximidade_comparativo")
    plt.close(fig)


# Fig 12: DM normalizado antes x depois da generalizacao, por k

def fig_dm_k() -> None:
    with open(RESULTADOS_DM / "resumo_dm_k.json", encoding="utf-8") as f:
        dados = json.load(f)
    antes, depois = dados["antes"], dados["depois"]

    labels = [f"k={item['k']}" for item in antes["por_k"]]
    pcts_antes  = [item["dm_normalizado"] * 100 for item in antes["por_k"]]
    pcts_depois = [item["dm_normalizado"] * 100 for item in depois["por_k"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_antes, width=largura, color=GRAY, label="Antes", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_depois, width=largura, color=BLUE, label="Depois", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("DM normalizado (%)")
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    _salvar(fig, "fig_dm_k")
    plt.close(fig)


# Fig 13: comparativo DM normalizado entre k-anonimato, l-diversidade e
# t-proximidade, nos pontos representativos discutidos no texto

def fig_dm_comparativo() -> None:
    with open(RESULTADOS_DM / "resumo_dm_k.json", encoding="utf-8") as f:
        dados_k = json.load(f)
    with open(RESULTADOS_DM / "resumo_dm_l.json", encoding="utf-8") as f:
        dados_l = json.load(f)
    with open(RESULTADOS_DM / "resumo_dm_t.json", encoding="utf-8") as f:
        dados_t = json.load(f)

    dm_k2 = next(item for item in dados_k["depois"]["por_k"] if item["k"] == 2)["dm_normalizado"]
    por_atributo_l = {item["atributo_sensivel"]: item for item in dados_l["por_atributo_sensivel"]}
    por_atributo_t = {item["atributo_sensivel"]: item for item in dados_t["por_atributo_sensivel"]}
    l2_evo = next(item for item in por_atributo_l["EVOLUCAO"]["por_l"] if item["l"] == 2)
    l2_cf  = next(item for item in por_atributo_l["CLASSI_FIN"]["por_l"] if item["l"] == 2)
    t02_evo = next(item for item in por_atributo_t["EVOLUCAO"]["por_t"] if item["t"] == 0.2)
    t02_cf  = next(item for item in por_atributo_t["CLASSI_FIN"]["por_t"] if item["t"] == 0.2)

    labels = ["k-anonimato\n($k=2$)", "$\\ell$-diversidade\ndistinta ($\\ell=2$)", "$t$-proximidade\n($t=0{,}2$)", "$\\ell$-diversidade\nentropia ($\\ell=2$)"]
    pcts_evolucao  = [dm_k2 * 100, l2_evo["distinta"]["dm_normalizado"] * 100, t02_evo["dm_normalizado"] * 100, l2_evo["entropia"]["dm_normalizado"] * 100]
    pcts_classifin = [dm_k2 * 100, l2_cf["distinta"]["dm_normalizado"] * 100, t02_cf["dm_normalizado"] * 100, l2_cf["entropia"]["dm_normalizado"] * 100]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(7, 3.8))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("DM normalizado (%)")
    ax.set_ylim(0, max(pcts_evolucao + pcts_classifin) * 1.25)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=7.5)
    fig.tight_layout()
    _salvar(fig, "fig_dm_comparativo")
    plt.close(fig)


# Fig 14: NCP normalizado antes x depois da generalizacao, por k

def fig_ncp_k() -> None:
    with open(RESULTADOS_NCP / "resumo_ncp_k.json", encoding="utf-8") as f:
        dados = json.load(f)
    antes, depois = dados["antes"], dados["depois"]

    labels = [f"k={item['k']}" for item in antes["por_k"]]
    pcts_antes  = [item["ncp_normalizado"] * 100 for item in antes["por_k"]]
    pcts_depois = [item["ncp_normalizado"] * 100 for item in depois["por_k"]]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(6, 3.6))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_antes, width=largura, color=GRAY, label="Antes", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_depois, width=largura, color=BLUE, label="Depois", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("NCP normalizado (%)")
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    _salvar(fig, "fig_ncp_k")
    plt.close(fig)


# Fig 15: comparativo NCP normalizado entre k-anonimato, l-diversidade e
# t-proximidade, nos pontos representativos discutidos no texto

def fig_ncp_comparativo() -> None:
    with open(RESULTADOS_NCP / "resumo_ncp_k.json", encoding="utf-8") as f:
        dados_k = json.load(f)
    with open(RESULTADOS_NCP / "resumo_ncp_l.json", encoding="utf-8") as f:
        dados_l = json.load(f)
    with open(RESULTADOS_NCP / "resumo_ncp_t.json", encoding="utf-8") as f:
        dados_t = json.load(f)

    ncp_k2 = next(item for item in dados_k["depois"]["por_k"] if item["k"] == 2)["ncp_normalizado"]
    por_atributo_l = {item["atributo_sensivel"]: item for item in dados_l["por_atributo_sensivel"]}
    por_atributo_t = {item["atributo_sensivel"]: item for item in dados_t["por_atributo_sensivel"]}
    l2_evo = next(item for item in por_atributo_l["EVOLUCAO"]["por_l"] if item["l"] == 2)
    l2_cf  = next(item for item in por_atributo_l["CLASSI_FIN"]["por_l"] if item["l"] == 2)
    t02_evo = next(item for item in por_atributo_t["EVOLUCAO"]["por_t"] if item["t"] == 0.2)
    t02_cf  = next(item for item in por_atributo_t["CLASSI_FIN"]["por_t"] if item["t"] == 0.2)

    labels = ["k-anonimato\n($k=2$)", "$\\ell$-diversidade\ndistinta ($\\ell=2$)", "$t$-proximidade\n($t=0{,}2$)", "$\\ell$-diversidade\nentropia ($\\ell=2$)"]
    pcts_evolucao  = [ncp_k2 * 100, l2_evo["distinta"]["ncp_normalizado"] * 100, t02_evo["ncp_normalizado"] * 100, l2_evo["entropia"]["ncp_normalizado"] * 100]
    pcts_classifin = [ncp_k2 * 100, l2_cf["distinta"]["ncp_normalizado"] * 100, t02_cf["ncp_normalizado"] * 100, l2_cf["entropia"]["ncp_normalizado"] * 100]

    x = range(len(labels))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(7, 3.8))
    bars1 = ax.bar([i - largura / 2 for i in x], pcts_evolucao, width=largura, color=BLUE, label="EVOLUCAO", zorder=2)
    bars2 = ax.bar([i + largura / 2 for i in x], pcts_classifin, width=largura, color=COLORS[1], label="CLASSI_FIN", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("NCP normalizado (%)")
    ax.set_ylim(0, max(pcts_evolucao + pcts_classifin) * 1.25)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6, zorder=1)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    for bars in (bars1, bars2):
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=7.5)
    fig.tight_layout()
    _salvar(fig, "fig_ncp_comparativo")
    plt.close(fig)


# Main

def main() -> None:
    print("Gerando figuras do Desenvolvimento...")
    fig_efeito_generalizacao()
    fig_k_nao_conformes()
    fig_homogeneidade_por_kmax()
    fig_evolucao_classes_homogeneas()
    fig_classifin_classes_homogeneas()
    fig_l_diversidade_distinta()
    fig_l_diversidade_entropia()
    fig_l_diversidade_comparativo()
    fig_assimetria_razao_risco()
    fig_assimetria_risco_elevado()
    fig_t_proximidade_violacao()
    fig_t_proximidade_por_kmax()
    fig_t_proximidade_comparativo()
    fig_dm_k()
    fig_dm_comparativo()
    fig_ncp_k()
    fig_ncp_comparativo()
    print(f"Figuras salvas em: {FIGS_DIR}")


if __name__ == "__main__":
    main()
