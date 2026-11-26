"""Conferência do `antes` com a base (A6-81): o LLM trocou a loja 33 por 75 no teste ponta a ponta de 26/11/2026."""
import json

import pytest
from langchain_core.messages import ToolMessage

from app.tools.correcao_tool import tool
from app.tools.correcao_tool.conferencia import SQL_VALOR_ATUAL, resolver_antes


class BaseFalsa:
    """Faz as vezes da busca na base: devolve valores fixos e guarda as consultas."""

    def __init__(self, valores: list[str | None]) -> None:
        self.valores = valores
        self.consultas: list[tuple[str, str, str]] = []

    def __call__(self, tipo: str, matricula: str, competencia: str) -> list[str | None]:
        self.consultas.append((tipo, matricula, competencia))
        return self.valores


class BaseQueFalha:
    def __call__(self, tipo: str, matricula: str, competencia: str) -> list[str | None]:
        raise ConnectionError("banco fora do ar")


def test_antes_igual_a_base_confere() -> None:
    base = BaseFalsa(["33"])
    assert resolver_antes("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10", "33", buscar=base)[1] is None
    assert base.consultas == [("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10")]


def test_antes_diferente_da_base_devolve_o_valor_atual() -> None:
    erro = resolver_antes("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10", "75", buscar=BaseFalsa(["33"]))[1]
    assert erro is not None
    assert "(75)" in erro and "é 33" in erro and "antes='33'" in erro


def test_matricula_sem_registro_na_competencia() -> None:
    erro = resolver_antes("TROCA_CARGO", "MATRIC-999", "2025-10", "100", buscar=BaseFalsa([]))[1]
    assert erro is not None and "não tem registro" in erro


def test_demissao_sem_data_atual_confere_com_antes_vazio() -> None:
    assert resolver_antes("DATA_DEMISSAO", "MATRIC-38", "2025-10", None, buscar=BaseFalsa([None]))[1] is None


def test_banco_fora_do_ar_nao_bloqueia() -> None:
    assert resolver_antes("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10", "33", buscar=BaseQueFalha())[1] is None


@pytest.mark.parametrize("tipo", ["TRANSFERENCIA_LOJA", "TROCA_CARGO", "DATA_ADMISSAO", "DATA_DEMISSAO"])
def test_sql_fixo_para_os_quatro_tipos_usa_parametros(tipo: str) -> None:
    assert "%(matricula)s" in SQL_VALOR_ATUAL[tipo]


def test_ferramenta_recusa_cartao_com_antes_errado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool, "buscar_valores_na_base", BaseFalsa(["33"]))
    mensagem: ToolMessage = tool.registrar_solicitacao_correcao.invoke({
        "name": tool.NOME_TOOL_CORRECAO, "id": "call-1", "type": "tool_call",
        "args": {"tipo": "TRANSFERENCIA_LOJA", "matricula": "MATRIC-38", "competencia": "2025-10",
                 "antes": "75", "depois": "8", "motivo": "Transferência a pedido da regional"},
    })
    assert mensagem.artifact == {}
    assert "não confere com a base" in json.loads(mensagem.content)["situacao"]


def test_sem_antes_usa_o_valor_unico_da_base() -> None:
    assert resolver_antes("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10", None, buscar=BaseFalsa(["33"])) == ("33", None)


def test_sem_antes_e_varios_valores_na_base_pede_conferencia() -> None:
    antes, erro = resolver_antes("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10", None, buscar=BaseFalsa(["33", "8"]))
    assert antes is None and erro is not None and "33, 8" in erro


def test_ferramenta_preenche_o_antes_vazio_com_a_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool, "buscar_valores_na_base", BaseFalsa(["33"]))
    mensagem: ToolMessage = tool.registrar_solicitacao_correcao.invoke({
        "name": tool.NOME_TOOL_CORRECAO, "id": "call-2", "type": "tool_call",
        "args": {"tipo": "TRANSFERENCIA_LOJA", "matricula": "MATRIC-38", "competencia": "2025-10",
                 "depois": "8", "motivo": "Transferência a pedido da regional"},
    })
    assert mensagem.artifact["antes"] == "33"
