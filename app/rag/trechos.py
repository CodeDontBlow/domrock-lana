"""Fatiamento estrutural e carregamento do corpus do RAG (A6-128)."""
import hashlib
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel

FonteTrecho = Literal[
    "especificacao",
    "capacidades",
    "esclarecimentos",
    "glossario",
    "legislacao",
    "estrategias",
    "exemplos",
]

FONTES_VALIDAS: set[str] = {
    "especificacao",
    "capacidades",
    "esclarecimentos",
    "glossario",
    "legislacao",
    "estrategias",
    "exemplos",
}

PASTA_CORPUS: Path = Path(__file__).resolve().parent / "corpus"
PADRAO_SECAO = re.compile(r"^##\s+([a-zA-Z0-9_-]+)\s+—\s+(.+)$", re.MULTILINE)


class TrechoBase(BaseModel, frozen=True):
    """Trecho atômico de conhecimento indexado na base vetorial."""

    id: str
    fonte: FonteTrecho
    item: str
    titulo: str
    texto: str


def _validar_fonte(fonte: str) -> None:
    if fonte not in FONTES_VALIDAS:
        raise ValueError(
            f"Fonte inválida: {fonte!r}; esperado uma de {sorted(FONTES_VALIDAS)}"
        )


def _extrair_trecho_secao(
    markdown: str,
    matches: list[re.Match[str]],
    idx: int,
    fonte: FonteTrecho,
) -> TrechoBase:
    match = matches[idx]
    item = match.group(1).strip()
    titulo = match.group(2).strip()
    inicio = match.end()
    fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
    corpo = markdown[inicio:fim].strip()
    return TrechoBase(
        id=f"{fonte}:{item}",
        fonte=fonte,
        item=item,
        titulo=titulo,
        texto=corpo,
    )


def fatiar_por_secao(markdown: str, fonte: str) -> list[TrechoBase]:
    """Divide um documento markdown estruturado em trechos por seção.

    Ex.: fatiar_por_secao("## 5b — Gerente\\nTexto", "especificacao")
    """
    _validar_fonte(fonte)
    correspondencias = list(PADRAO_SECAO.finditer(markdown))
    if not correspondencias:
        inicio = markdown[:40]
        raise ValueError(
            f"Nenhuma seção encontrada no texto: {inicio!r}; esperado formato '## <item> — <título>'"
        )
    fonte_tipada: FonteTrecho = fonte  # type: ignore[assignment]
    return [
        _extrair_trecho_secao(markdown, correspondencias, i, fonte_tipada)
        for i in range(len(correspondencias))
    ]



def carregar_corpus(pasta: Path = PASTA_CORPUS) -> list[TrechoBase]:
    """Carrega todos os arquivos Markdown da pasta do corpus em ordem alfabética.

    Ex.: carregar_corpus()
    """
    if not pasta.exists():
        return []

    arquivos = sorted(pasta.glob("*.md"))
    todos_trechos: list[TrechoBase] = []
    for arquivo in arquivos:
        fonte = arquivo.stem
        _validar_fonte(fonte)
        conteudo = arquivo.read_text(encoding="utf-8")
        todos_trechos.extend(fatiar_por_secao(conteudo, fonte))
    return todos_trechos


def hash_do_corpus(trechos: list[TrechoBase]) -> str:
    """Calcula hash sha256 determinístico dos trechos em ordem.

    Ex.: hash_do_corpus(trechos)
    """
    hasher = hashlib.sha256()
    for trecho in trechos:
        hasher.update(trecho.id.encode("utf-8"))
        hasher.update(trecho.texto.encode("utf-8"))
    return hasher.hexdigest()
