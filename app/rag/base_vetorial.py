"""Base vetorial persistente com ChromaDB e protocolo BaseConhecimento (A6-128)."""
from collections.abc import Callable
from functools import lru_cache
import json
import logging
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction
from pydantic import BaseModel

from app.core.config import get_settings
from app.rag.embeddings import EmbeddingFastembed
from app.rag.trechos import TrechoBase, hash_do_corpus

NOME_COLLECTION_PADRAO = "lana_conhecimento"

logger = logging.getLogger(__name__)


class TrechoEncontrado(BaseModel, frozen=True):
    """Resultado de uma busca vetorial contendo o trecho e a distância calculada."""

    trecho: TrechoBase
    distancia: float


@runtime_checkable
class BaseConhecimento(Protocol):
    """Protocolo da base vetorial para injeção de dependência."""

    def buscar(self, texto: str, k: int) -> list[TrechoEncontrado]: ...


class BaseChroma:
    """Implementação da base vetorial usando ChromaDB PersistentClient."""

    def __init__(
        self,
        pasta: Path | str,
        funcao_embedding: EmbeddingFunction[Documents],
        nome_collection: str = NOME_COLLECTION_PADRAO,
    ) -> None:
        self.pasta = Path(pasta)
        self.funcao_embedding = funcao_embedding
        self.nome_collection = nome_collection
        self.client = chromadb.PersistentClient(
            path=str(self.pasta),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        # A6-128: abrir a collection no Chroma 1.5 reconstrói a função de embedding (e recarrega o
        # modelo, ~840 ms). A collection aberta fica guardada e a busca cai para ~9 ms.
        self._collection: chromadb.Collection | None = None

    def indexar_se_mudou(self, trechos: list[TrechoBase]) -> bool:
        """Indexa os trechos na collection se o hash do corpus mudou.

        Ex.: base.indexar_se_mudou(trechos)
        """
        hash_novo = hash_do_corpus(trechos)
        hash_existente = self._obter_hash_salvo()
        if hash_existente == hash_novo:
            return False

        self._recriar_collection(hash_novo)
        if trechos:
            self._adicionar_trechos(trechos, hash_novo)
        return True

    def buscar(self, texto: str, k: int = 3) -> list[TrechoEncontrado]:
        """Busca os k trechos mais próximos do texto por similaridade de cosseno.

        Ex.: base.buscar("regra 5c", k=3)
        """
        collection = self._obter_collection()
        total = collection.count()
        if total == 0:
            return []

        limite = min(k, total)
        consulta = collection.query(query_texts=[texto], n_results=limite)
        return self._converter_resultados(consulta)

    def _obter_collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.nome_collection,
                embedding_function=self.funcao_embedding,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _obter_hash_salvo(self) -> str | None:
        try:
            col = self.client.get_collection(
                name=self.nome_collection,
                embedding_function=self.funcao_embedding,
            )
            return (col.metadata or {}).get("hash_corpus")
        except Exception:
            return None

    def _recriar_collection(self, hash_corpus: str) -> None:
        try:
            self.client.delete_collection(name=self.nome_collection)
        except Exception:
            pass
        self._collection = self.client.create_collection(
            name=self.nome_collection,
            embedding_function=self.funcao_embedding,
            metadata={"hnsw:space": "cosine", "hash_corpus": hash_corpus},
        )

    def _adicionar_trechos(self, trechos: list[TrechoBase], hash_corpus: str) -> None:
        col = self._obter_collection()
        ids = [t.id for t in trechos]
        documentos = [t.texto for t in trechos]
        metadados = [
            {
                "fonte": t.fonte,
                "item": t.item,
                "titulo": t.titulo,
                "texto": t.texto,
                "hash_corpus": hash_corpus,
            }
            for t in trechos
        ]
        col.add(ids=ids, documents=documentos, metadatas=metadados)

    def _converter_resultados(self, consulta: dict) -> list[TrechoEncontrado]:
        ids = consulta.get("ids", [[]])[0]
        distancias = consulta.get("distances", [[]])[0]
        metadados = consulta.get("metadatas", [[]])[0]
        achados: list[TrechoEncontrado] = []
        for id_doc, dist, meta in zip(ids, distancias, metadados):
            trecho = TrechoBase(
                id=str(id_doc),
                fonte=meta["fonte"],
                item=meta["item"],
                titulo=meta["titulo"],
                texto=meta["texto"],
            )
            achados.append(TrechoEncontrado(trecho=trecho, distancia=float(dist)))
        achados.sort(key=lambda t: t.distancia)
        return achados


@lru_cache
def obter_base_conhecimento() -> BaseChroma:
    """Retorna instância singleton da base vetorial do ChromaDB."""
    config = get_settings()
    pasta_chroma = Path(config.RAG_PASTA_CHROMA)
    pasta_modelo = Path(config.RAG_PASTA_MODELO)
    funcao = EmbeddingFastembed(pasta_cache=pasta_modelo)
    return BaseChroma(pasta=pasta_chroma, funcao_embedding=funcao)


def preparar_base_conhecimento(base: Any, trechos: list[TrechoBase]) -> None:
    """Indexa os trechos na base vetorial se houver alterações, com logs JSON (A6-128).

    Ex.: preparar_base_conhecimento(base, trechos)
    """
    try:
        reindexou = base.indexar_se_mudou(trechos)
        # A6-128: log de observabilidade em JSON de uma linha
        logger.info(
            json.dumps(
                {"evento": "rag_indexado", "trechos": len(trechos), "reindexou": reindexou},
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        # A6-128: falha aberta com registro de indisponibilidade
        logger.warning(
            json.dumps({"evento": "rag_indisponivel", "erro": str(exc)}, ensure_ascii=False)
        )


def iniciar_base_conhecimento(
    obter_base: Callable[[], BaseConhecimento],
    carregar: Callable[[], list[TrechoBase]],
) -> None:
    """Inicializa e indexa a base vetorial sem propagar exceções (A6-128).

    Ex.: iniciar_base_conhecimento(obter_base_conhecimento, carregar_corpus)
    """
    try:
        base = obter_base()
        trechos = carregar()
        preparar_base_conhecimento(base, trechos)
    except Exception as exc:
        # A6-128: falha aberta garantida no startup
        logger.warning(
            json.dumps({"evento": "rag_indisponivel", "erro": str(exc)}, ensure_ascii=False)
        )

