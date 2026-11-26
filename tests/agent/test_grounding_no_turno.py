"""Testes de integração do grounding e guardrail no turno da Lana (A6-128)."""
import pytest
from app.agent import service
from app.agent.service import lana_invoke
from app.rag.grounding import MENSAGEM_FORA_DO_ESCOPO, ConfigRag
from tests.rag.fakes_rag import (
    CONFIG_050,
    FakeBaseConhecimento,
    FakeBaseQuebrada,
    FakeGrafoRegistrador,
    encontrado,
)


def test_fora_do_escopo_nao_chama_a_llm(monkeypatch):
    grafo = FakeGrafoRegistrador()
    monkeypatch.setattr(service, "_executar_grafo", grafo)
    turno = lana_invoke(
        "c1",
        "Qual a previsão do tempo para amanhã?",
        base=FakeBaseConhecimento([encontrado("5c", 0.80)]),
        config_rag=CONFIG_050,
    )
    assert turno["response"] == MENSAGEM_FORA_DO_ESCOPO
    assert grafo.chamadas == []
    g = turno["trilha"]["grounding"]
    assert (g["situacao"], g["distancia"], g["limiar"]) == ("fora_do_escopo", 0.80, 0.50)


def test_no_escopo_leva_os_trechos_e_a_instrucao_ao_prompt(monkeypatch):
    grafo = FakeGrafoRegistrador()
    monkeypatch.setattr(service, "_executar_grafo", grafo)
    turno = lana_invoke(
        "c1",
        "Como funciona a admissão?",
        base=FakeBaseConhecimento([encontrado("5c", 0.30)]),
        config_rag=CONFIG_050,
    )
    assert len(grafo.chamadas) == 1
    ultima_msg = grafo.chamadas[0][-1]
    assert "item 5c" in ultima_msg.content and "APENAS" in ultima_msg.content
    g = turno["trilha"]["grounding"]
    assert g["situacao"] == "no_escopo"
    assert g["item"] == "5c"


def test_busca_usa_a_mensagem_sem_o_prefixo_do_painel(monkeypatch):
    grafo = FakeGrafoRegistrador()
    monkeypatch.setattr(service, "_executar_grafo", grafo)
    base = FakeBaseConhecimento([encontrado("5c", 0.20)])
    regra = {"parametros": [{"key": "pct_acrescimo", "value": 2.0}]}
    lana_invoke(
        "c1",
        "Admissão no meio do mês",
        regra=regra,
        base=base,
        config_rag=CONFIG_050,
    )
    assert len(base.consultas) == 1
    assert "Parâmetros atuais no painel" not in base.consultas[0]
    assert "Admissão no meio do mês" in base.consultas[0]


def test_follow_up_usa_o_historico_na_busca(monkeypatch):
    grafo = FakeGrafoRegistrador()
    monkeypatch.setattr(service, "_executar_grafo", grafo)
    base = FakeBaseConhecimento([encontrado("campanha", 0.25)])
    historico = [
        {"papel": "usuario", "texto": "crie uma campanha de 2% para a marca 10 em novembro"},
        {"papel": "lana", "texto": "Confirma a campanha de 2% para a marca 10 em novembro?"},
    ]
    lana_invoke(
        "c1",
        "sim, pode registrar",
        historico=historico,
        base=base,
        config_rag=CONFIG_050,
    )
    assert len(base.consultas) == 1
    assert "Confirma a campanha de 2% para a marca 10 em novembro?" in base.consultas[0]
    assert "sim, pode registrar" in base.consultas[0]


def test_base_quebrada_segue_sem_rag(monkeypatch):
    grafo = FakeGrafoRegistrador()
    monkeypatch.setattr(service, "_executar_grafo", grafo)
    turno = lana_invoke(
        "c1",
        "Como funciona a admissão?",
        base=FakeBaseQuebrada(),
        config_rag=CONFIG_050,
    )
    assert len(grafo.chamadas) == 1
    g = turno["trilha"]["grounding"]
    assert g["situacao"] == "indisponivel"


def test_rag_desligado_nao_busca(monkeypatch):
    grafo = FakeGrafoRegistrador()
    monkeypatch.setattr(service, "_executar_grafo", grafo)
    base = FakeBaseConhecimento([encontrado("5c", 0.20)])
    config_off = ConfigRag(ativo=False, limiar=0.50, top_k=3)
    turno = lana_invoke(
        "c1",
        "Como funciona a admissão?",
        base=base,
        config_rag=config_off,
    )
    assert len(grafo.chamadas) == 1
    assert base.consultas == []
    g = turno["trilha"]["grounding"]
    assert g["situacao"] == "desligado"


def test_quando_obter_base_levanta_segue_sem_rag(monkeypatch):
    grafo = FakeGrafoRegistrador()
    monkeypatch.setattr(service, "_executar_grafo", grafo)

    def _fabrica_quebrada():
        raise RuntimeError("modelo ausente no disco")

    monkeypatch.setattr(service, "obter_base_conhecimento", _fabrica_quebrada)
    turno = lana_invoke(
        "c1",
        "Como funciona a admissão?",
        base=None,
        config_rag=CONFIG_050,
    )
    assert len(grafo.chamadas) == 1
    g = turno["trilha"]["grounding"]
    assert g["situacao"] == "indisponivel"

