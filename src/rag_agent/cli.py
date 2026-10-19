"""Command line entry point: ``rag ingest PATH`` and ``rag search QUERY``."""

from pathlib import Path
from typing import Annotated

import typer

from rag_agent.config import IngestionTunables, RetrievalTunables, load_tunables
from rag_agent.ingestion.pipeline import IngestionPipeline
from rag_agent.retrieval.bm25 import BM25Index
from rag_agent.retrieval.embedder import Embedder
from rag_agent.retrieval.hybrid import HybridRetriever
from rag_agent.retrieval.reranker import Reranker
from rag_agent.retrieval.vector_store import VectorStore

app = typer.Typer(help="RAG agent command line.", no_args_is_help=True)

CONFIG_PATH = Path("config.yaml")
PREVIEW_CHARS = 160


def _make_embedder(ingestion: IngestionTunables) -> Embedder:
    return Embedder(ingestion.embedding_model, ingestion.embed_batch_size)


def _make_reranker(retrieval: RetrievalTunables) -> Reranker:
    return Reranker(retrieval.rerank_model)


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


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="The question or keywords to search for.")],
) -> None:
    """Print the best chunks for QUERY, with the stages that were used and any that degraded."""
    config = load_tunables(CONFIG_PATH)
    ingestion, retrieval = config.ingestion, config.retrieval
    retriever = HybridRetriever(
        store=VectorStore(ingestion.chroma_path, ingestion.collection_name),
        embedder=_make_embedder(ingestion),
        keyword_index=BM25Index(),
        mode=retrieval.mode,
        dense_top_k=retrieval.dense_top_k,
        bm25_top_k=retrieval.bm25_top_k,
        rrf_k=retrieval.rrf_k,
        fused_top_k=retrieval.fused_top_k,
        reranker=_make_reranker(retrieval) if retrieval.mode == "hybrid_rerank" else None,
        rerank_top_k=retrieval.rerank_top_k,
    )
    result = retriever.retrieve(query)
    if not result.hits:
        typer.echo("No results.")
    for rank, hit in enumerate(result.hits, start=1):
        chunk = hit.chunk
        location = f"{chunk.source}, page {chunk.page}" if chunk.page else chunk.source
        typer.echo(f"{rank}. score {hit.score:.4f}  {location}")
        if chunk.heading_path:
            typer.echo(f"   {chunk.heading_path}")
        preview = chunk.text[:PREVIEW_CHARS].replace("\n", " ")
        typer.echo(f"   {preview}")
    typer.echo(f"degraded: {', '.join(result.degraded) or 'none'}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
