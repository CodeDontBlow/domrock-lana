"""Cartão de correção só com a competência dita pelo usuário (critério da A6-81)."""
import pytest

from app.agent.competencia_dita import (
    competencia_foi_dita,
    exigir_competencia_dita,
    padroes_da_competencia,
    textos_do_usuario,
)

CORRECAO = {"categoria": "CORRECAO", "tipo": "TRANSFERENCIA_LOJA", "competencia": "2025-10"}


@pytest.mark.parametrize("texto", [
    "foi transferida em outubro de 2025",
    "competência 10/2025",
    "em 10/25",
    "a partir de 2025-10",
    "no dia 01/10/2025",
    "em out/2025",
])
def test_formas_de_citar_outubro_de_2025(texto: str) -> None:
    assert competencia_foi_dita("2025-10", [texto])


@pytest.mark.parametrize("texto", ["foi transferida para a loja 8", "em novembro", "a marca 10 mudou", "11/2025"])
def test_texto_sem_a_competencia(texto: str) -> None:
    assert not competencia_foi_dita("2025-10", [texto])


def test_marco_com_e_sem_cedilha() -> None:
    assert competencia_foi_dita("2025-03", ["em março"]) and competencia_foi_dita("2025-03", ["em marco"])
    assert padroes_da_competencia("2025-03")[-1] == r"\bmar\b"


def test_competencia_invalida_nao_conta_como_dita() -> None:
    assert not competencia_foi_dita("10/2025", ["outubro"])


def test_correcao_sem_mes_dito_cai() -> None:
    assert exigir_competencia_dita(CORRECAO, None, ["A MATRIC-38 foi para a loja 8"]) is None


def test_correcao_com_mes_dito_fica() -> None:
    assert exigir_competencia_dita(CORRECAO, None, ["em outubro de 2025"]) == CORRECAO


def test_rascunho_com_a_mesma_competencia_conta_como_dito() -> None:
    assert exigir_competencia_dita(CORRECAO, {"competencia": "2025-10"}, ["troque o motivo"]) == CORRECAO


def test_intercorrencia_nao_passa_pela_regra() -> None:
    ferias = {"categoria": "INTERCORRENCIA", "competencia": "2025-12"}
    assert exigir_competencia_dita(ferias, None, ["férias de 01/12 a 15/12"]) == ferias


def test_textos_do_usuario_ignora_a_lana() -> None:
    historico = [{"papel": "usuario", "texto": "em outubro"}, {"papel": "lana", "texto": "em novembro"}]
    assert textos_do_usuario("troque", historico) == ["em outubro", "troque"]
