"""Script de verificação da postura consultiva da Lana em 6 cenários típicos (A6-128)."""
import uuid
from typing import Any

from app.agent.service import lana_invoke

# Seis mensagens de exemplo cobrindo saudação, análise de dados, ideias, percentual, sugestão e campanha.
MENSAGENS_EXEMPLO: list[str] = [
    "oi",
    "como foram as vendas da marca 10?",
    "que campanha faz sentido para novembro?",
    "2% é muito?",
    "monta uma sugestão para mim",
    "crie uma campanha de 2% para a marca 10 em novembro",
]


def verificar_pergunta_generica(texto: str) -> bool:
    """Verifica se o texto encerra com perguntas genéricas de empurrar campanha.

    Exemplo:
        >>> verificar_pergunta_generica("Dados exibidos. Quer fazer uma campanha?")
        True
    """
    if not texto:
        return False
    # A6-128: avalia o fechamento da resposta para detectar se a Lana empurrou campanha no fim.
    fechamento = texto.strip().lower()[-200:]
    padroes = (
        "vamos criar uma campanha",
        "vamos fazer uma campanha",
        "quer criar uma campanha",
        "quer fazer uma campanha",
        "deseja criar uma campanha",
        "deseja fazer uma campanha",
    )
    return any(padrao in fechamento for padrao in padroes)


def formatar_ferramentas(eventos: list[dict[str, Any]]) -> str:
    """Formata a lista de ferramentas chamadas a partir dos eventos do turno.

    Exemplo:
        >>> formatar_ferramentas([{"ferramenta": "consultar_banco"}])
        'consultar_banco'
    """
    if not eventos:
        return "nenhuma"
    nomes = [e.get("ferramenta") or e.get("tool") or "desconhecida" for e in eventos]
    return ", ".join(nomes)


def executar_cenario(mensagem: str) -> None:
    """Executa um turno isolado da Lana com uma nova conversa e exibe os resultados.

    Exemplo:
        >>> executar_cenario("oi")
    """
    thread_id = f"postura-teste-{uuid.uuid4().hex[:8]}"
    resultado = lana_invoke(thread_id, mensagem)
    resposta = resultado.get("response", "")
    eventos = resultado.get("events", [])
    termina_generica = verificar_pergunta_generica(resposta)

    print("=" * 60)
    print(f"Pergunta: {mensagem}")
    print(f"Ferramentas chamadas: {formatar_ferramentas(eventos)}")
    print(f"Termina com pergunta genérica de campanha: {'SIM' if termina_generica else 'NÃO'}")
    print(f"Resposta:\n{resposta}\n")


def main() -> None:
    """Executa a sequência de 6 mensagens de teste de postura consultiva.

    Exemplo:
        >>> main()
    """
    print("Iniciando avaliação de postura consultiva da Lana (A6-128)...\n")
    for mensagem in MENSAGENS_EXEMPLO:
        executar_cenario(mensagem)


if __name__ == "__main__":
    main()
