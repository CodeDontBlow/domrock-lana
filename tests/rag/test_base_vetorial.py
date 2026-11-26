"""Testes da base vetorial no ChromaDB (A6-128)."""
from pathlib import Path

from app.rag.base_vetorial import BaseChroma
from tests.rag.fakes_rag import FakeEmbeddingPorPalavras, trechos_gerente_e_admissao


def test_buscar_devolve_o_trecho_mais_proximo_primeiro(tmp_path: Path):
    base = BaseChroma(tmp_path, FakeEmbeddingPorPalavras())
    base.indexar_se_mudou(trechos_gerente_e_admissao())
    achados = base.buscar("comissão do gerente pela venda da loja", k=2)
    assert len(achados) == 2
    assert achados[0].trecho.item == "5b"
    assert achados[0].distancia <= achados[1].distancia


def test_texto_identico_tem_distancia_quase_zero(tmp_path: Path):
    base = BaseChroma(tmp_path, FakeEmbeddingPorPalavras())
    trechos = trechos_gerente_e_admissao()
    base.indexar_se_mudou(trechos)
    achados = base.buscar(trechos[0].texto, k=1)
    assert len(achados) == 1
    assert achados[0].distancia < 0.01


def test_indexar_se_mudou_nao_reindexa_o_mesmo_corpus(tmp_path: Path):
    base = BaseChroma(tmp_path, FakeEmbeddingPorPalavras())
    trechos = trechos_gerente_e_admissao()
    assert base.indexar_se_mudou(trechos) is True
    assert base.indexar_se_mudou(trechos) is False


def test_reindexa_e_remove_trechos_antigos_quando_o_corpus_muda(tmp_path: Path):
    base = BaseChroma(tmp_path, FakeEmbeddingPorPalavras())
    trechos = trechos_gerente_e_admissao()
    base.indexar_se_mudou(trechos)
    so_admissao = [t for t in trechos if t.item == "5c"]
    assert base.indexar_se_mudou(so_admissao) is True
    achados = base.buscar("gerente", k=5)
    assert all(a.trecho.item != "5b" for a in achados)


def test_base_persiste_em_disco(tmp_path: Path):
    embedding = FakeEmbeddingPorPalavras()
    base1 = BaseChroma(tmp_path, embedding)
    trechos = trechos_gerente_e_admissao()
    assert base1.indexar_se_mudou(trechos) is True
    base2 = BaseChroma(tmp_path, embedding)
    assert base2.indexar_se_mudou(trechos) is False
    achados = base2.buscar("gerente", k=2)
    assert len(achados) > 0


class ClienteChromaContador:
    """Envolve o cliente real do Chroma e conta quantas vezes a collection é aberta."""

    def __init__(self, cliente_real: object) -> None:
        self._cliente_real = cliente_real
        self.aberturas = 0

    def get_or_create_collection(self, **kwargs: object) -> object:
        self.aberturas += 1
        return self._cliente_real.get_or_create_collection(**kwargs)

    def __getattr__(self, nome: str) -> object:
        return getattr(self._cliente_real, nome)


def test_buscas_seguidas_nao_reabrem_a_collection(tmp_path: Path):
    # A6-128: reabrir a collection recarregava o modelo e levava ~840 ms por busca.
    base = BaseChroma(tmp_path, FakeEmbeddingPorPalavras())
    contador = ClienteChromaContador(base.client)
    base.client = contador
    for _ in range(3):
        base.buscar("comissão do gerente", k=1)
    assert contador.aberturas == 1
