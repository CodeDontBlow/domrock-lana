"""Conferência da matrícula da intercorrência na base, com SQL fixo (A6-124)."""
import json

import pytest
from langchain_core.messages import ToolMessage

from app.tools.intercorrencia_tool import tool
from app.tools.intercorrencia_tool.conferencia import SQL_MATRICULA, conferir_matricula


class MatriculaFalsa:
    """Faz as vezes da busca na base: responde se a matrícula existe e guarda as consultas."""

    def __init__(self, existe: bool) -> None:
        self.existe = existe
        self.consultas: list[str] = []

    def __call__(self, matricula: str) -> bool:
        self.consultas.append(matricula)
        return self.existe


class BancoForaDoAr:
    def __call__(self, matricula: str) -> bool:
        raise ConnectionError("banco fora do ar")


def test_matricula_existente_confere() -> None:
    base = MatriculaFalsa(True)
    assert conferir_matricula("MATRIC-12", buscar=base) is None
    assert base.consultas == ["MATRIC-12"]


def test_matricula_inexistente_devolve_erro() -> None:
    erro = conferir_matricula("MATRIC-9999", buscar=MatriculaFalsa(False))
    assert erro is not None and "MATRIC-9999" in erro and "não existe" in erro


def test_banco_fora_do_ar_nao_bloqueia() -> None:
    assert conferir_matricula("MATRIC-12", buscar=BancoForaDoAr()) is None


def test_sql_usa_parametro() -> None:
    assert "%(matricula)s" in SQL_MATRICULA


def test_ferramenta_recusa_matricula_inexistente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool, "buscar_matricula_na_base", MatriculaFalsa(False))
    mensagem: ToolMessage = tool.registrar_intercorrencia.invoke({
        "name": tool.NOME_TOOL_INTERCORRENCIA, "id": "call-1", "type": "tool_call",
        "args": {"tipo": "FERIAS", "matricula": "MATRIC-9999", "data_inicio": "2025-12-01",
                 "data_fim": "2025-12-15", "motivo": "Férias programadas"},
    })
    assert mensagem.artifact == {}
    assert "não existe" in json.loads(mensagem.content)["situacao"]
