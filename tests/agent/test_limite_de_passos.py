"""Testes para o limite de passos no grafo da Lana (A6-128)."""
import json
import logging
from typing import Any
import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.errors import GraphRecursionError

from app.agent import service
from app.agent.service import MENSAGEM_LIMITE_DE_PASSOS, _executar_grafo
from app.core.config import Settings, get_settings


class FakeGrafoEmLoop:
    """Simula um grafo preso em loop infinito que estoura a contagem de passos."""

    def __init__(self) -> None:
        self.chamadas: list[tuple[dict[str, list[BaseMessage]], dict[str, Any] | None]] = []

    def invoke(
        self,
        entrada: dict[str, list[BaseMessage]],
        config: dict[str, Any] | None = None,
    ) -> dict[str, list[BaseMessage]]:
        self.chamadas.append((entrada, config))
        raise GraphRecursionError("Recursion limit of 25 reached.")


def test_configuracao_padrao_limite_de_passos() -> None:
    """Verifica que o padrão de LANA_LIMITE_PASSOS é 25 conforme definido na A6-128."""
    config = get_settings()
    assert config.LANA_LIMITE_PASSOS == 25


def test_limite_de_passos_vira_mensagem_amigavel(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Garante captura de GraphRecursionError, mensagem amigável e log de observabilidade."""
    grafo_fake = FakeGrafoEmLoop()
    monkeypatch.setattr(service, "lana", grafo_fake)

    entrada = [HumanMessage(content="loop infinito")]
    with caplog.at_level(logging.WARNING):
        novas = _executar_grafo(entrada)

    assert len(novas) == 1
    assert isinstance(novas[0], AIMessage)
    assert novas[0].content == MENSAGEM_LIMITE_DE_PASSOS
    assert "Não consegui concluir dentro do limite de passos" in novas[0].content

    # Confere se passou recursion_limit do Settings
    assert len(grafo_fake.chamadas) == 1
    _, config_recebido = grafo_fake.chamadas[0]
    assert config_recebido == {"recursion_limit": 25}

    # Confere emissão do log JSON
    registros = [r.message for r in caplog.records if "limite_de_passos" in r.message]
    assert len(registros) == 1
    dados_log = json.loads(registros[0])
    assert dados_log == {"evento": "limite_de_passos", "limite": 25}


def test_limite_de_passos_respeita_valor_customizado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica se _executar_grafo utiliza o limite dinâmico configurado no Settings."""
    grafo_fake = FakeGrafoEmLoop()
    monkeypatch.setattr(service, "lana", grafo_fake)
    monkeypatch.setattr(service, "get_settings", lambda: Settings(
        AI_PROVIDER="GEMINI",
        AI_MODEL="fake",
        GEMINI_API_KEY="fake",
        LANA_LIMITE_PASSOS=10,
    ))

    entrada = [HumanMessage(content="loop com limite menor")]
    novas = _executar_grafo(entrada)

    assert len(novas) == 1
    assert novas[0].content == MENSAGEM_LIMITE_DE_PASSOS
    _, config_recebido = grafo_fake.chamadas[0]
    assert config_recebido == {"recursion_limit": 10}
