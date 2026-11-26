"""Geração do diagrama Mermaid do grafo de execução da Lana (A6-128)."""
from app.agent.graph import lana


def mermaid_do_grafo() -> str:
    """Extrai a representação Mermaid do grafo de estados compilado da Lana.

    Utilizado para documentação viva do fluxo entre agente e ferramentas
    (UA04 Seq02: 'o código vira documentação').

    Exemplo:
        >>> diagrama = mermaid_do_grafo()
        >>> assert "graph TD;" in diagrama
        >>> assert "agent" in diagrama
    """
    return lana.get_graph().draw_mermaid()
