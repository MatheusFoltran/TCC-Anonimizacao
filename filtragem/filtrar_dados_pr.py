# Projeta dados_filtro_pr.csv (saída de filtrar_dados.py) nas colunas
# usadas pelo resto do projeto, gerando dados_filtro_base.csv.
from pathlib import Path

import pandas as pd

COLUNAS_BASE = [
    "NU_NOTIFIC",
    "DT_NOTIFIC",
    "SEM_NOT",
    "DT_SIN_PRI",
    "SEM_PRI",
    "SG_UF_NOT",
    "CO_REGIONA",
    "ID_MUNICIP",
    "CO_MUN_NOT",
    "CS_SEXO",
    "DT_NASC",
    "CS_RACA",
    "CO_RG_RESI",
    "CO_MUN_RES",
    "EVOLUCAO",
    "DT_EVOLUCA",
    "CLASSI_FIN",
]


def gerar_projecao_colunas(
    input_path: Path,
    output_path: Path,
    colunas: list[str],
    chunk_size: int = 200_000,
) -> int:
    total_linhas = 0
    escreveu_cabecalho = False
    colunas_validadas = False

    for chunk in pd.read_csv(
        input_path,
        sep=";",
        dtype=str,
        chunksize=chunk_size,
        low_memory=True,
    ):
        chunk.columns = [col.strip().replace('"', "") for col in chunk.columns]

        if not colunas_validadas:
            faltantes = [col for col in colunas if col not in chunk.columns]
            if faltantes:
                raise ValueError(
                    "Colunas ausentes no arquivo de entrada: "
                    f"{faltantes}"
                )
            colunas_validadas = True

        filtrado = chunk[colunas]

        if not filtrado.empty:
            filtrado.to_csv(
                output_path,
                sep=";",
                index=False,
                mode="a" if escreveu_cabecalho else "w",
                header=not escreveu_cabecalho,
            )
            escreveu_cabecalho = True
            total_linhas += len(filtrado)

    if not escreveu_cabecalho:
        pd.DataFrame(columns=colunas).to_csv(output_path, sep=";", index=False)

    return total_linhas


def main() -> None:
    input_path = Path("base_filtrada/dados_filtro_pr.csv")
    output_path = Path("base_filtrada/dados_filtro_base.csv")
    chunk_size = 200_000

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = gerar_projecao_colunas(
        input_path=input_path,
        output_path=output_path,
        colunas=COLUNAS_BASE,
        chunk_size=chunk_size,
    )

    print("Geracao concluida para base.")
    print(f"Linhas processadas: {total}")
    print(f"Arquivo gerado: {output_path}")


if __name__ == "__main__":
    main()
