"""Command line entry point: ``rag ingest PATH``."""

from pathlib import Path
from typing import Annotated

import typer

from rag_agent.config import IngestionTunables, load_tunables
from rag_agent.ingestion.pipeline import IngestionPipeline
from rag_agent.retrieval.bm25 import BM25Index
from rag_agent.retrieval.embedder import Embedder
from rag_agent.retrieval.vector_store import VectorStore

app = typer.Typer(help="RAG agent command line.", no_args_is_help=True)

CONFIG_PATH = Path("config.yaml")


def _make_embedder(ingestion: IngestionTunables) -> Embedder:
    return Embedder(ingestion.embedding_model, ingestion.embed_batch_size)


@app.callback()
def root() -> None:
    """Keep ``rag`` a command group, so each command is named on the command line."""


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(exists=True, help="A file or a folder to ingest.")],
) -> None:
    """Load, chunk, embed and store the files at PATH. Re-running adds only new chunks."""
    ingestion = load_tunables(CONFIG_PATH).ingestion
    pipeline = IngestionPipeline(
        store=VectorStore(ingestion.chroma_path, ingestion.collection_name),
        embedder=_make_embedder(ingestion),
        keyword_index=BM25Index(),
        chunk_size=ingestion.chunk_size_chars,
        chunk_overlap=ingestion.chunk_overlap_chars,
        embed_with_heading=ingestion.embed_with_heading,
    )
    report = pipeline.run(path)
    typer.echo(
        f"files: {report.files}, chunks added: {report.chunks_added}, "
        f"chunks skipped: {report.chunks_skipped}"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
