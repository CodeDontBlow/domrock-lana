"""Só abre o cartão de correção se o usuário disse a competência (A6-81).

Critério da A6-81: "Dado Gabriela não diz o mês, Então a Lana pergunta a competência antes de abrir".
O gemini-3.5-flash-lite ignorava a instrução do prompt e chutava o mês mais recente (teste de 26/11/2026),
então a conferência é feita no código, sobre o texto do usuário e o histórico, depois do turno.
"""
import re
from typing import Any

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

PERGUNTA_COMPETENCIA = (
    "Para abrir o pedido de correção, preciso da competência: em qual mês e ano essa alteração vale?"
)


def padroes_da_competencia(competencia: str) -> list[str]:
    """Formas de citar a competência yyyy-MM num texto: 10/2025, 10/25, 2025-10, outubro, out.

    Ex.: padroes_da_competencia("2025-03")[-2:] -> [r"\\bmar(ç|c)o\\b", r"\\bmar\\b"]
    """
    ano, mes = competencia.split("-")
    numero = int(mes)
    nome = MESES[numero - 1].replace("ç", "(ç|c)")
    return [
        rf"\b0?{numero}/{ano}\b",
        rf"\b0?{numero}/{ano[2:]}\b",
        rf"\b{ano}-{mes}\b",
        rf"\b{nome}\b",
        rf"\b{MESES[numero - 1][:3]}\b",
    ]


def competencia_foi_dita(competencia: str, textos: list[str]) -> bool:
    """True quando algum texto do usuário cita a competência.

    Ex.: competencia_foi_dita("2025-10", ["foi transferida em outubro de 2025"]) -> True
    """
    if not re.fullmatch(r"\d{4}-\d{2}", competencia or ""):
        return False
    padroes = padroes_da_competencia(competencia)
    return any(re.search(p, texto.lower()) for texto in textos for p in padroes)


def textos_do_usuario(user_input: str, historico: list[dict[str, Any]] | None) -> list[str]:
    """Mensagem atual e mensagens anteriores do usuário (sem as da Lana nem os trechos do RAG)."""
    anteriores = [str(item.get("texto", "")) for item in historico or [] if item.get("papel") == "usuario"]
    return [*anteriores, user_input]


def exigir_competencia_dita(
    solicitacao: dict[str, Any] | None,
    rascunho: dict[str, Any] | None,
    textos: list[str],
) -> dict[str, Any] | None:
    """A solicitação do turno, ou None quando é correção com uma competência que o usuário não disse.

    O rascunho do cartão conta como dito: ao refinar ("troque o motivo"), o usuário não repete o mês.
    Ex.: exigir_competencia_dita({"categoria": "CORRECAO", "competencia": "2025-11"}, None, ["para a loja 8"]) -> None
    """
    if not solicitacao or solicitacao.get("categoria") != "CORRECAO":
        return solicitacao
    competencia = str(solicitacao.get("competencia") or "")
    if rascunho and rascunho.get("competencia") == competencia:
        return solicitacao
    return solicitacao if competencia_foi_dita(competencia, textos) else None
