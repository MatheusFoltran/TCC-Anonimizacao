# Primeira etapa do pipeline de filtragem: filtra o CSV bruto (nacional) por
# UF, gerando dados_filtro_pr.csv. Etapa seguinte: filtrar_dados_pr.py.
import argparse
from pathlib import Path

import pandas as pd


def normalizar_datas_sem_hora(df: pd.DataFrame) -> pd.DataFrame:
    # Converte valores ISO como 2021-03-23T00:00:00.000Z para 2021-03-23.
    colunas_data = [
        col
        for col in df.columns
        if col.upper().startswith("DT_") or "_DT" in col.upper()
    ]

    if not colunas_data:
        return df

    for col in colunas_data:
        df[col] = df[col].fillna("").str.replace(
            r"^(\d{4}-\d{2}-\d{2})T.*$", r"\1", regex=True
        )

    return df


def filtrar_csv_por_uf(
    input_path: Path,
    output_path: Path,
    uf_alvo: str = "PR",
    chunk_size: int = 200_000,
) -> int:
    uf_alvo = uf_alvo.upper().strip()
    total_linhas = 0
    escreveu_cabecalho = False

    for chunk in pd.read_csv(
        input_path,
        sep=";",
        dtype=str,
        chunksize=chunk_size,
        low_memory=True,
    ):
        chunk.columns = [col.strip().replace('"', "") for col in chunk.columns]

        coluna_uf = None
        for candidata in ("SG_UF", "SG_UF_NOT"):
            if candidata in chunk.columns:
                coluna_uf = candidata
                break

        if coluna_uf is None:
            raise ValueError("Nenhuma coluna de UF encontrada (SG_UF ou SG_UF_NOT).")

        filtrado = chunk[chunk[coluna_uf].fillna("").str.upper().str.strip() == uf_alvo].copy()
        filtrado = normalizar_datas_sem_hora(filtrado)

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
        # Gera arquivo vazio com cabecalho quando nao houver resultados.
        amostra = pd.read_csv(input_path, sep=";", dtype=str, nrows=0)
        amostra.to_csv(output_path, sep=";", index=False)

    return total_linhas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filtra um CSV pelo estado (UF) e gera um novo arquivo.")
    parser.add_argument(
        "--input",
        default="base_original/INFLUD21-23-03-2026.csv",
        help="Caminho para o CSV de entrada.",
    )
    parser.add_argument(
        "--output",
        default="base_filtrada/dados_filtro_pr.csv",
        help="Caminho para o CSV de saida filtrado.",
    )
    parser.add_argument(
        "--uf",
        default="PR",
        help="Sigla da UF para filtro (padrao: PR).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=200_000,
        help="Quantidade de linhas por lote para leitura do CSV.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = filtrar_csv_por_uf(
        input_path=input_path,
        output_path=output_path,
        uf_alvo=args.uf,
        chunk_size=args.chunk_size,
    )

    print(f"Filtro concluido. Linhas encontradas para {args.uf.upper()}: {total}")
    print(f"Arquivo gerado: {output_path}")


if __name__ == "__main__":
    main()
