"""Fakes e utilitários de teste para o módulo RAG (A6-128)."""
import math
import re
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.rag.base_vetorial import TrechoEncontrado
from app.rag.grounding import ConfigRag
from app.rag.trechos import TrechoBase, fatiar_por_secao

CONFIG_050 = ConfigRag(ativo=True, limiar=0.50, top_k=3)

VOCABULARIO_PADRAO: list[str] = [
    "comissao", "gerente", "admissao", "demissao", "afastamento", "ferias",
    "loja", "venda", "vendas", "marca", "cargo", "funcionario", "dias",
    "trabalhados", "proporcional", "proporcionalmente", "total", "regra",
    "campanha", "bonus", "percentual", "apurado", "valor", "base", "novembro",
    "black", "friday", "tempo", "previsao", "senha", "banco", "instrucoes",
]


def _normalizar_palavra(termo: str) -> str:
    substituicoes = {"ã": "a", "á": "a", "â": "a", "é": "e", "ê": "e", "í": "i", "ó": "o", "ô": "o", "ú": "u", "ç": "c"}
    termo = termo.lower()
    for o, d in substituicoes.items():
        termo = termo.replace(o, d)
    return termo


class FakeEmbeddingPorPalavras(EmbeddingFunction[Documents]):
    """Vetor de contagem sobre vocabulário fixo, normalizado e determinístico."""

    def __init__(self, vocabulario: list[str] | None = None) -> None:
        self.vocabulario = vocabulario or VOCABULARIO_PADRAO

    def __call__(self, input: Documents) -> Embeddings:
        vetores: list[list[float]] = []
        for doc in input:
            tokens = [_normalizar_palavra(p) for p in re.findall(r"\w+", doc)]
            contagens = [float(tokens.count(p)) for p in self.vocabulario]
            norma = math.sqrt(sum(c * c for c in contagens))
            if norma == 0.0:
                vetor = [0.0] * len(self.vocabulario)
                vetor[0] = 1.0
            else:
                vetor = [c / norma for c in contagens]
            vetores.append(vetor)
        return vetores

    @staticmethod
    def name() -> str:
        return "fake_palavras"

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine"]

    def get_config(self) -> dict[str, Any]:
        return {"vocabulario": self.vocabulario}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "FakeEmbeddingPorPalavras":
        return FakeEmbeddingPorPalavras(vocabulario=config.get("vocabulario"))


def encontrado(item: str, distancia: float, fonte: str = "especificacao") -> TrechoEncontrado:
    """Cria um TrechoEncontrado sintético para testes."""
    trecho = TrechoBase(
        id=f"{fonte}:{item}",
        fonte=fonte,
        item=item,
        titulo=f"Regra {item}",
        texto=f"Texto explicativo da regra {item}.",
    )
    return TrechoEncontrado(trecho=trecho, distancia=distancia)


def trechos_gerente_e_admissao() -> list[TrechoBase]:
    """Retorna os itens 5b e 5c com texto de especificação para testes."""
    md = (
        "## 5b — Gerente\n"
        "Para o código de cargo Gerente (150) a aplicação do % de comissionamento se dará pela venda total da loja.\n\n"
        "## 5c — Admissão\n"
        "Caso algum funcionário seja admitido no mês de competência o seu comissionamento será calculado proporcionalmente aos dias trabalhados."
    )
    return fatiar_por_secao(md, "especificacao")


class FakeBaseConhecimento:
    """Fake da BaseConhecimento que devolve achados pré-configurados e grava consultas."""

    def __init__(self, achados: list[TrechoEncontrado] | None = None) -> None:
        self.achados = achados or []
        self.consultas: list[str] = []

    def buscar(self, texto: str, k: int = 3) -> list[TrechoEncontrado]:
        self.consultas.append(texto)
        return self.achados[:k]


class FakeBaseQuebrada:
    """Fake de BaseConhecimento indisponível para testar falha aberta."""

    def buscar(self, texto: str, k: int = 3) -> list[TrechoEncontrado]:
        raise RuntimeError("chroma fora")

    def indexar_se_mudou(self, trechos: list[TrechoBase]) -> bool:
        raise RuntimeError("chroma fora")


class FakeGrafoRegistrador:
    """Fake de _executar_grafo que registra entradas e devolve [AIMessage('ok')]."""

    def __init__(self, resposta: str = "ok") -> None:
        self.chamadas: list[list[Any]] = []
        self.resposta = resposta

    def __call__(self, entrada: list[Any]) -> list[Any]:
        from langchain_core.messages import AIMessage
        self.chamadas.append(entrada)
        return [AIMessage(content=self.resposta)]
