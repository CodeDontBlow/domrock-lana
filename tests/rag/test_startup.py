"""Testes de inicialização da base de conhecimento no startup (A6-128)."""
import logging
from app.rag.base_vetorial import iniciar_base_conhecimento, preparar_base_conhecimento
from app.rag.trechos import TrechoBase
from tests.rag.fakes_rag import FakeBaseQuebrada, trechos_gerente_e_admissao


class FakeBaseContadora:
    """Fake de BaseChroma que conta chamadas a indexar_se_mudou."""

    def __init__(self) -> None:
        self.chamadas = 0

    def indexar_se_mudou(self, trechos: list[TrechoBase]) -> bool:
        self.chamadas += 1
        return True


class FakeFabricaQuebrada:
    """Fábrica que simula falha ao obter a base."""

    def __call__(self):
        raise RuntimeError("falha ao carregar modelo vetorial")


class FakeFabricaBaseBoa:
    """Fábrica que devolve fake de base de conhecimento."""

    def __init__(self, base: FakeBaseContadora) -> None:
        self.base = base

    def __call__(self):
        return self.base


class FakeFabricaCorpusBoa:
    """Fábrica que devolve lista válida de trechos."""

    def __init__(self, trechos: list[TrechoBase]) -> None:
        self.trechos = trechos

    def __call__(self) -> list[TrechoBase]:
        return self.trechos


def test_preparar_base_registra_indexacao(caplog):
    base = FakeBaseContadora()
    trechos = trechos_gerente_e_admissao()
    with caplog.at_level(logging.INFO):
        preparar_base_conhecimento(base, trechos)
    assert base.chamadas == 1
    assert any("rag_indexado" in record.message for record in caplog.records)


def test_preparar_base_com_erro_nao_levanta(caplog):
    base = FakeBaseQuebrada()
    trechos = trechos_gerente_e_admissao()
    with caplog.at_level(logging.WARNING):
        preparar_base_conhecimento(base, trechos)
    assert any("rag_indisponivel" in record.message for record in caplog.records)


def test_iniciar_base_fabrica_que_levanta_nao_levanta_para_fora(caplog):
    fabrica_erro = FakeFabricaQuebrada()
    fabrica_corpus = FakeFabricaCorpusBoa(trechos_gerente_e_admissao())
    with caplog.at_level(logging.WARNING):
        iniciar_base_conhecimento(fabrica_erro, fabrica_corpus)
    assert any("rag_indisponivel" in record.message for record in caplog.records)


def test_iniciar_base_fabrica_boa_indexa(caplog):
    base = FakeBaseContadora()
    fabrica_base = FakeFabricaBaseBoa(base)
    fabrica_corpus = FakeFabricaCorpusBoa(trechos_gerente_e_admissao())
    with caplog.at_level(logging.INFO):
        iniciar_base_conhecimento(fabrica_base, fabrica_corpus)
    assert base.chamadas == 1
    assert any("rag_indexado" in record.message for record in caplog.records)

