import os

os.environ.setdefault("AI_PROVIDER", "GEMINI")
os.environ.setdefault("AI_MODEL", "gemini-3.5-flash-lite")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")
os.environ.setdefault("RAG_ATIVO", "false")


import pytest


class BaseIndisponivel:
    """Fake da busca do `antes` na base: sem banco nos testes, a conferência é pulada (como em produção sem acesso)."""

    def __call__(self, tipo: str, matricula: str, competencia: str) -> list[str | None]:
        raise ConnectionError(f"sem banco nos testes: {tipo} {matricula} {competencia}")


@pytest.fixture(autouse=True)
def _sem_banco_na_conferencia_do_antes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tools.correcao_tool import tool

    monkeypatch.setattr(tool, "buscar_valores_na_base", BaseIndisponivel())
