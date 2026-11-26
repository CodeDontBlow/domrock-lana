"""Script para desenhar o grafo de execução da Lana e gerar documentação Markdown (A6-128)."""
from pathlib import Path
from app.agent.desenho_do_grafo import mermaid_do_grafo

CAMINHO_DOCUMENTO = Path(__file__).resolve().parent.parent / "docs" / "grafo-lana.md"


def montar_conteudo_documento(diagrama_mermaid: str) -> str:
    """Gera o texto em Markdown contendo o diagrama Mermaid e a descrição de cada nó.

    Exemplo:
        >>> texto = montar_conteudo_documento("graph TD; agent --> tools;")
        >>> assert "# Grafo de Execução da Lana" in texto
    """
    bloco_mermaid = diagrama_mermaid.strip()
    return (
        "# Grafo de Execução da Lana\n\n"
        "> Este arquivo é gerado automaticamente pelo script `scripts/desenhar_grafo.py`.\n"
        "> Para regenerar, execute:\n"
        "> ```bash\n"
        "> docker run --rm -v \"$PWD\":/app -w /app -e AI_PROVIDER=GEMINI -e AI_MODEL=fake "
        "-e GEMINI_API_KEY=fake python:3.12.14-slim sh -c \"pip install -q -r requirements-dev.txt "
        "&& PYTHONPATH=. python scripts/desenhar_grafo.py\"\n"
        "> ```\n\n"
        "## Diagrama de Estados e Transições\n\n"
        "```mermaid\n"
        f"{bloco_mermaid}\n"
        "```\n\n"
        "## Nós do Grafo\n\n"
        "- `__start__`: Ponto de entrada da execução no LangGraph, direcionando as mensagens iniciais ao nó `agent`.\n"
        "- `agent`: Nó supervisor do agente (`app/agent/supervisor.py`), responsável por invocar a LLM e decidir se chama ferramentas ou encerra o turno.\n"
        "- `tools`: Nó executor (`ToolNode` em `app/agent/graph.py`), que executa `consultar_banco` ou `registrar_parametros_regra` e devolve os resultados ao estado.\n"
        "- `__end__`: Ponto final do fluxo quando o nó `agent` gera uma resposta direta sem novas chamadas a ferramentas.\n"
    )


def gerar_arquivo_do_grafo(destino: Path = CAMINHO_DOCUMENTO) -> Path:
    """Gera e grava a documentação do grafo no caminho de destino especificado.

    Exemplo:
        >>> arquivo = gerar_arquivo_do_grafo(Path('/tmp/grafo-teste.md'))
        >>> assert arquivo.exists()
    """
    diagrama = mermaid_do_grafo()
    conteudo = montar_conteudo_documento(diagrama)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    return destino


if __name__ == "__main__":
    gerado = gerar_arquivo_do_grafo()
    print(f"Grafo documentado com sucesso em: {gerado}")
