ifeq ($(OS),Windows_NT)
PYTHON ?= .venv/Scripts/python.exe
else
PYTHON ?= .venv/bin/python
endif
UF ?= PR

.DEFAULT_GOAL := help

.PHONY: help check-python reproduzir figuras filter-pr project-base study comparativo-generalizacao generalizacao k homogeneidade homogeneidade-base homogeneidade-alvos homogeneidade-busca homogeneidade-confianca homogeneidade-comparativa l-diversidade l-diversidade-avaliacao l-diversidade-comparativo t-proximidade t-proximidade-avaliacao t-proximidade-comparativo t-proximidade-comparativa-k assimetria assimetria-base assimetria-alvos assimetria-busca dm dm-l dm-t ncp ncp-l ncp-t metricas-comparativo clean-results

help:
	@echo "Alvos disponiveis:"
	@echo "  make filter-pr           -> Filtra base original por UF (padrao UF=PR)"
	@echo "  make project-base        -> Projeta colunas base em base_filtrada/dados_filtro_base.csv"
	@echo "  make study               -> Agrupamento por QI sem anonimizacao (registros da mesma pessoa)"
	@echo "  make comparativo-generalizacao -> Compara agrupamento antes/depois da generalizacao"
	@echo "  make generalizacao       -> Agrupamento por QI apos generalizacao/supressao"
	@echo "  make k                   -> Executa k-anonimato (todos os k=2,3,4,5 juntos)"
	@echo "  make homogeneidade       -> Executa filtragem + alvos + busca (2 cenarios) + confianca + comparativa"
	@echo "  make homogeneidade-base  -> Filtra base homogenea (independente de k; breakdown por k=2..5 no resumo)"
	@echo "  make homogeneidade-alvos -> Gera alvos para os 2 cenarios de ataque"
	@echo "  make homogeneidade-busca -> Executa os 2 cenarios de ataque de homogeneidade (independente de k)"
	@echo "  make homogeneidade-confianca     -> Executa ataque por confianca temporal (independente de k)"
	@echo "  make homogeneidade-comparativa   -> Analise comparativa de vulnerabilidade por k_max"
	@echo "  make l-diversidade       -> Executa l-diversidade (distinta + entropia) + comparativo"
	@echo "  make l-diversidade-avaliacao     -> l-diversidade distinta e por entropia (EVOLUCAO e CLASSI_FIN)"
	@echo "  make l-diversidade-comparativo   -> Metrica combinada (AND por registro) EVOLUCAO x CLASSI_FIN"
	@echo "  make t-proximidade       -> Executa t-proximidade (avaliacao + comparativo + comparativa-k)"
	@echo "  make t-proximidade-avaliacao     -> Avaliacao por EMD de distancia uniforme (EVOLUCAO e CLASSI_FIN)"
	@echo "  make t-proximidade-comparativo   -> Metrica combinada (AND por registro) EVOLUCAO x CLASSI_FIN"
	@echo "  make t-proximidade-comparativa-k -> Analise comparativa de EMD/violacao por k_max"
	@echo "  make assimetria          -> Executa base + alvos + busca do ataque de assimetria"
	@echo "  make assimetria-base     -> Filtra blocos l-diversos (l=2 distinta) e calcula desvio vs distribuicao global"
	@echo "  make assimetria-alvos    -> Amostra alvos dentro dos blocos l-diversos"
	@echo "  make assimetria-busca    -> Executa o ataque contra os alvos (confianca local vs global)"
	@echo "  make dm                  -> Discernibility Metric (Bayardo) por k, antes x depois da generalizacao"
	@echo "  make dm-l                -> DM generalizado para l-diversidade (distinta + entropia, EVOLUCAO e CLASSI_FIN)"
	@echo "  make dm-t                -> DM generalizado para t-proximidade (EVOLUCAO e CLASSI_FIN)"
	@echo "  make ncp                 -> Normalized Certainty Penalty (Xu et al.) por k, antes x depois da generalizacao"
	@echo "  make ncp-l               -> NCP generalizado para l-diversidade (distinta + entropia, EVOLUCAO e CLASSI_FIN)"
	@echo "  make ncp-t                -> NCP generalizado para t-proximidade (EVOLUCAO e CLASSI_FIN)"
	@echo "  make metricas-comparativo -> Consolida DM e NCP nos 4 criterios de referencia (k, l-distinta, t, l-entropia)"
	@echo "  make figuras             -> Gera as figuras do trabalho em docs/figuras/"
	@echo "  make reproduzir          -> Executa todas as etapas (inclusive study e generalizacao) a partir de base_filtrada/dados_filtro_base.csv"
	@echo "  make clean-results       -> Remove arquivos de saida em resultados/"
	@echo ""
	@echo "Variaveis uteis: UF=PR"
	@echo "Exemplos: make reproduzir | make k | make homogeneidade"

check-python:
	@$(PYTHON) --version

reproduzir: study generalizacao comparativo-generalizacao k homogeneidade l-diversidade t-proximidade assimetria dm dm-l dm-t ncp ncp-l ncp-t metricas-comparativo figuras

figuras: check-python
	@$(PYTHON) src/graficos/gerar_figuras_desenvolvimento.py

filter-pr: check-python
	@$(PYTHON) filtragem/filtrar_dados.py --uf $(UF)

project-base: check-python
	@$(PYTHON) filtragem/filtrar_dados_pr.py

study: check-python
	@$(PYTHON) src/experimentos/executar_estudo.py

comparativo-generalizacao: check-python
	@$(PYTHON) src/experimentos/comparativo_generalizacao.py

generalizacao: check-python
	@$(PYTHON) src/tecnicas/generalizacao_supressao.py

k: check-python
	@$(PYTHON) src/modelos/k_anonimato/k_anonimato.py

homogeneidade: check-python homogeneidade-base homogeneidade-alvos homogeneidade-busca homogeneidade-confianca homogeneidade-comparativa

homogeneidade-base: check-python
	@$(PYTHON) src/ataques/homogeneidade/filtragem_inicial.py

homogeneidade-alvos: check-python
	@$(PYTHON) src/ataques/homogeneidade/alvos.py

homogeneidade-busca: check-python
	@$(PYTHON) src/ataques/homogeneidade/busca.py

homogeneidade-confianca: check-python
	@$(PYTHON) src/ataques/homogeneidade/confianca.py

homogeneidade-comparativa: check-python
	@$(PYTHON) src/ataques/homogeneidade/analise_comparativa_k.py

l-diversidade: check-python l-diversidade-avaliacao l-diversidade-comparativo

l-diversidade-avaliacao: check-python
	@$(PYTHON) src/modelos/l_diversidade/avaliacao.py

l-diversidade-comparativo: check-python
	@$(PYTHON) src/modelos/l_diversidade/comparativo.py

t-proximidade: check-python t-proximidade-avaliacao t-proximidade-comparativo t-proximidade-comparativa-k

t-proximidade-avaliacao: check-python
	@$(PYTHON) src/modelos/t_proximidade/avaliacao.py

t-proximidade-comparativo: check-python
	@$(PYTHON) src/modelos/t_proximidade/comparativo.py

t-proximidade-comparativa-k: check-python
	@$(PYTHON) src/modelos/t_proximidade/analise_comparativa_k.py

assimetria: check-python assimetria-base assimetria-alvos assimetria-busca

assimetria-base: check-python
	@$(PYTHON) src/ataques/assimetria/base.py

assimetria-alvos: check-python
	@$(PYTHON) src/ataques/assimetria/alvos.py

assimetria-busca: check-python
	@$(PYTHON) src/ataques/assimetria/busca.py

dm: check-python
	@$(PYTHON) src/metricas/dm/dm_k.py

dm-l: check-python
	@$(PYTHON) src/metricas/dm/dm_l.py

dm-t: check-python
	@$(PYTHON) src/metricas/dm/dm_t.py

ncp: check-python
	@$(PYTHON) src/metricas/ncp/ncp_k.py

ncp-l: check-python
	@$(PYTHON) src/metricas/ncp/ncp_l.py

ncp-t: check-python
	@$(PYTHON) src/metricas/ncp/ncp_t.py

metricas-comparativo: check-python
	@$(PYTHON) src/metricas/comparativo.py

clean-results:
	@echo "Limpando resultados gerados..."
	@rm -rf src/experimentos/resultados/*
	@rm -rf src/tecnicas/resultados/*
	@rm -rf src/modelos/k_anonimato/resultados/*
	@rm -rf src/modelos/l_diversidade/resultados/*
	@rm -rf src/modelos/t_proximidade/resultados/*
	@rm -rf src/ataques/homogeneidade/resultados/*
	@rm -rf src/ataques/assimetria/resultados/*
	@rm -rf src/metricas/dm/resultados/*
	@rm -rf src/metricas/ncp/resultados/*
	@rm -rf src/metricas/resultados/*
