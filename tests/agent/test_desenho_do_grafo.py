"""Testes para o desenho do grafo Mermaid da Lana (A6-128)."""
from pathlib import Path
import pytest
from app.agent.desenho_do_grafo import mermaid_do_grafo
from scripts.desenhar_grafo import CAMINHO_DOCUMENTO, gerar_arquivo_do_grafo, montar_conteudo_documento


def test_mermaid_tem_os_nos_agent_e_tools() -> None:
    """Garante que a função mermaid_do_grafo devolve o diagrama contendo os nós agent e tools."""
    mermaid = mermaid_do_grafo()

    assert isinstance(mermaid, str)
    assert len(mermaid) > 0
    assert "agent" in mermaid
    assert "tools" in mermaid


def test_montar_conteudo_documento_inclui_cabecalho_e_nos() -> None:
    """Verifica se o Markdown gerado possui aviso de regeneração, bloco mermaid e nós explicados."""
    texto = montar_conteudo_documento("graph TD;\n\tagent --> tools;")

    assert "# Grafo de Execução da Lana" in texto
    assert "scripts/desenhar_grafo.py" in texto
    assert "```mermaid\ngraph TD;\n\tagent --> tools;\n```" in texto
    assert "- `agent`:" in texto
    assert "- `tools`:" in texto
    assert "- `__start__`:" in texto
    assert "- `__end__`:" in texto


def test_gerar_arquivo_do_grafo_grava_arquivo(tmp_path: Path) -> None:
    """Verifica se a função grava o arquivo no caminho de destino especificado."""
    destino = tmp_path / "grafo-teste.md"
    arquivo_gerado = gerar_arquivo_do_grafo(destino)

    assert arquivo_gerado.exists()
    conteudo = arquivo_gerado.read_text(encoding="utf-8")
    assert "# Grafo de Execução da Lana" in conteudo
    assert "```mermaid" in conteudo
