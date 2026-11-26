"""Adaptador do FastEmbed ao protocolo de EmbeddingFunction do ChromaDB (A6-128)."""
from pathlib import Path
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from fastembed import TextEmbedding

MODELO_PADRAO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingFastembed(EmbeddingFunction[Documents]):
    """Função de embedding usando fastembed com cache persistente."""

    def __init__(
        self,
        modelo: str = MODELO_PADRAO,
        pasta_cache: Path | str | None = None,
    ) -> None:
        if not pasta_cache:
            raise ValueError(
                f"pasta_cache é obrigatória; recebido {pasta_cache!r}"
            )
        self.modelo = modelo
        self.pasta_cache = str(pasta_cache)
        self._embedder = TextEmbedding(
            model_name=self.modelo,
            cache_dir=self.pasta_cache,
        )

    def __call__(self, input: Documents) -> Embeddings:
        """Calcula embeddings normalizados para os textos fornecidos."""
        vetores = list(self._embedder.embed(input))
        return [v.tolist() for v in vetores]

    @staticmethod
    def name() -> str:
        """Nome identificador da função de embedding."""
        return "fastembed"

    def default_space(self) -> str:
        """Espaço métrico padrão configurado para cosseno."""
        return "cosine"

    def supported_spaces(self) -> list[str]:
        """Espaços métricos suportados."""
        return ["cosine"]

    def get_config(self) -> dict[str, Any]:
        """Configuração serializável da função."""
        return {"modelo": self.modelo, "pasta_cache": self.pasta_cache}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "EmbeddingFastembed":
        """Reconstrói a função a partir da configuração serializada."""
        return EmbeddingFastembed(
            modelo=config.get("modelo", MODELO_PADRAO),
            pasta_cache=config.get("pasta_cache"),
        )
