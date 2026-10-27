# Avaliação de Técnicas de Anonimização para Proteção de Dados Sensíveis

Código-fonte do Trabalho de Conclusão de Curso *Avaliação de Técnicas de
Anonimização para Proteção de Dados Sensíveis*, desenvolvido no curso de
Bacharelado em Ciência da Computação da Universidade Estadual de Maringá (UEM).

- **Autor:** Matheus Foltran Consonni
- **Orientador:** Alisson Renan Svaigen
- **Ano:** 2026

O trabalho avalia, sobre a base pública de Síndrome Respiratória Aguda Grave
(SRAG) de 2021 filtrada para o estado do Paraná, o risco que permanece nos
dados após a aplicação de três modelos formais de privacidade:

- ***k*-anonimato**, para *k* ∈ {2, 3, 4, 5};
- ***ℓ*-diversidade**, nas variantes distinta e por entropia, com a formulação
  multi-atributo para os dois atributos sensíveis avaliados;
- ***t*-proximidade**, com a *Earth Mover's Distance* (EMD) de distância
  uniforme entre categorias, para *t* ∈ {0,1; 0,15; 0,2; 0,3}.

O risco residual é estimado pela simulação de dois ataques de inferência:

- **ataque de homogeneidade**, incluindo as variantes por confiança temporal e
  por inconsistência de óbito;
- **ataque de assimetria**, contra blocos que já satisfazem *ℓ*-diversidade,
  medido pela razão entre a frequência local e a global do valor sensível.

A perda de utilidade é medida pela *Discernibility Metric* (DM) e pelo
*Normalized Certainty Penalty* (NCP).

Os atributos sensíveis avaliados, em paralelo, são `EVOLUCAO` (desfecho
clínico) e `CLASSI_FIN` (classificação final do caso).

## Dados

A base bruta **não está incluída** neste repositório, por causa do tamanho
(cerca de 1,8 GB). Ela deve ser obtida no Portal de Dados Abertos do SUS:

<https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026>

O estudo utilizou o recurso **"2021- Banco vivo 23/03/2026"** (formato CSV),
salvo como `base_original/INFLUD21-23-03-2026.csv`. Por se tratar de um
"banco vivo", versões publicadas em outras datas podem conter registros
atualizados e produzir números ligeiramente diferentes dos relatados no TCC.

O repositório inclui `base_filtrada/dados_filtro_base.csv`, gerado pelos dois
primeiros passos da reprodução, o que permite executar as demais etapas sem
baixar a base bruta. Esse arquivo é um recorte, sem nenhuma transformação, da
base publicada abertamente pelo Ministério da Saúde: contém apenas as colunas
usadas no estudo e os registros do Paraná.

O dicionário de dados está em `docs/dicionario-de-dados-2019-a-2025.pdf` e
também na mesma página do portal, no recurso "2019 a 2025- Dicionário de
Dados".

## Requisitos

- Python 3.13
- Bibliotecas listadas em `requirements.txt` (pandas, openpyxl, numpy,
  matplotlib)
- `make` (opcional, para usar os alvos do `Makefile`)

```
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
.venv/bin/python -m pip install -r requirements.txt           # Linux/macOS
```

O `Makefile` usa o interpretador do ambiente virtual `.venv`
(`.venv/Scripts/python.exe` no Windows, `.venv/bin/python` nos demais
sistemas). Para usar outro, informe-o na chamada, por exemplo:
`make k PYTHON=python3`.

## Reprodução do estudo

Com a base salva em `base_original/`, os passos abaixo reproduzem o estudo na
ordem em que foram executados (os dois primeiros podem ser pulados, pois
`base_filtrada/dados_filtro_base.csv` já está no repositório):

```
make filter-pr UF=PR             # filtra a base pela UF (gera base_filtrada/dados_filtro_pr.csv)
make project-base                # seleciona as colunas usadas (gera base_filtrada/dados_filtro_base.csv)
make comparativo-generalizacao   # agrupamento antes e depois da generalização
make k                           # k-anonimato (k = 2, 3, 4, 5)
make homogeneidade               # ataque de homogeneidade e variantes
make l-diversidade               # l-diversidade (distinta, entropia e multi-atributo)
make t-proximidade               # t-proximidade (EMD)
make assimetria                  # ataque de assimetria
make dm dm-l dm-t                # Discernibility Metric para k, l e t
make ncp ncp-l ncp-t             # Normalized Certainty Penalty para k, l e t
make metricas-comparativo        # consolidação de DM e NCP entre os modelos
```

As figuras do trabalho são geradas a partir dos resumos em JSON:

```
make figuras                     # salva em docs/figuras/
```

Para executar tudo de uma vez, a partir da base filtrada incluída (inclui
também `make study` e `make generalizacao`, descritos abaixo):

```
make reproduzir
```

`make help` lista todos os alvos disponíveis, inclusive os que executam cada
etapa isoladamente.

Três scripts auxiliares não fazem parte da sequência acima:

- `make study` executa o agrupamento por quase-identificadores sobre a base
  sem anonimização, para estimar quantos registros provavelmente pertencem à
  mesma pessoa (duplicidade de notificação). Gera
  `src/experimentos/resultados/resumo_probabilidade_mesma_pessoa.json`.
- `make generalizacao` aplica a generalização e a supressão e executa o mesmo
  agrupamento sobre a base anonimizada. Gera
  `src/tecnicas/resultados/resumo_anonimizacao.json`.
- `python src/experimentos/exemplo_ilustrativo.py [--id-grupo N]` seleciona,
  de forma determinística, o grupo real usado como exemplo ilustrativo ao
  longo do Desenvolvimento do TCC e exibe seus dados no terminal, sem gravar
  arquivos. Requer que as etapas de k-anonimato e de assimetria já tenham sido
  executadas.

## Estrutura

```
filtragem/                        Filtragem da base bruta por UF e seleção de colunas
src/
  nucleo.py                       Agrupamento por quase-identificadores (lógica central)
  utils/                          Funções de leitura e exportação compartilhadas
  experimentos/                   Efeito da generalização sobre o agrupamento
  tecnicas/                       Generalização e supressão; mapa município -> regional de saúde
  modelos/
    k_anonimato/                  Avaliação do k-anonimato
    l_diversidade/                Avaliação da l-diversidade
    t_proximidade/                Avaliação da t-proximidade
  ataques/
    homogeneidade/                Ataque de homogeneidade e variantes
    assimetria/                   Ataque de assimetria
  metricas/
    dm/                           Discernibility Metric
    ncp/                          Normalized Certainty Penalty
    comparativo.py                Consolidação das métricas entre os modelos
  graficos/                       Geração das figuras do trabalho
docs/
  figuras/                        Figuras utilizadas no TCC
  dicionario-de-dados-2019-a-2025.pdf   Dicionário de dados da base SRAG
```

Cada módulo grava suas saídas em uma subpasta `resultados/` própria (CSV, XLSX
e um JSON de resumo com a metodologia e os números agregados).

## Resultados

Este repositório versiona apenas os resultados agregados: os JSONs de resumo
de cada etapa (dos quais as figuras são geradas) e as tabelas de DM, NCP e das
análises comparativas por *k*.

As saídas em nível de registro (por exemplo, a base com as classes de
equivalência, os blocos de *ℓ*-diversidade e *t*-proximidade e os alvos
simulados dos ataques) não são versionadas, porque contêm combinações de
quase-identificadores e atributos sensíveis de registros reais. Elas são
recriadas nas mesmas subpastas `resultados/` ao executar o pipeline.

## Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE`.

A licença MIT cobre o código. A base filtrada e o dicionário de dados são do
Ministério da Saúde, obtidos no Portal de Dados Abertos do SUS.
