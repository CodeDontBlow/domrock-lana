"""Confere o `antes` da correção com a base antes de montar o cartão (A6-81).

O LLM às vezes copia um código errado do resultado do `consultar_banco` (no teste ponta a ponta de
26/11/2026, "loja 75" para a MATRIC-38, que está na loja 33). O backend recusaria no Confirmar, mas o
usuário já teria visto um cartão errado. Conferindo aqui com SQL fixo, a ferramenta devolve o valor
atual e a Lana corrige antes de mostrar o cartão.
"""
import json
import logging
from collections.abc import Callable

from app.core.db import executar_select

logger = logging.getLogger(__name__)

# Busca os valores atuais: (tipo, matrícula, competência yyyy-MM) -> lista de valores em texto.
BuscarValoresAtuais = Callable[[str, str, str], list[str | None]]

_FILTRO_ALOCACAO = "UPPER(f.matricula) = %(matricula)s AND {tabela}.date_ref = %(competencia)s::date"

SQL_VALOR_ATUAL: dict[str, str] = {
    "TRANSFERENCIA_LOJA": (
        "SELECT l.cod_loja AS valor FROM funcionario_loja fl "
        "JOIN funcionario f ON f.id = fl.funcionario_id JOIN loja l ON l.id = fl.loja_id "
        "WHERE " + _FILTRO_ALOCACAO.format(tabela="fl")
    ),
    "TROCA_CARGO": (
        "SELECT c.cod_cargo AS valor FROM funcionario_cargo fc "
        "JOIN funcionario f ON f.id = fc.funcionario_id JOIN cargo c ON c.id = fc.cargo_id "
        "WHERE " + _FILTRO_ALOCACAO.format(tabela="fc")
    ),
    "DATA_ADMISSAO": "SELECT f.data_admissao::text AS valor FROM funcionario f WHERE UPPER(f.matricula) = %(matricula)s",
    "DATA_DEMISSAO": "SELECT f.data_demissao::text AS valor FROM funcionario f WHERE UPPER(f.matricula) = %(matricula)s",
}


def buscar_valores_atuais(tipo: str, matricula: str, competencia: str) -> list[str | None]:
    """Valores atuais na base para o tipo de correção, com SQL fixo e parâmetros (sem LLM).

    Ex.: buscar_valores_atuais("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10") -> ["33"]
    """
    parametros = {"matricula": matricula.strip().upper(), "competencia": f"{competencia}-01"}
    linhas = executar_select(SQL_VALOR_ATUAL[tipo], parametros)
    return [None if linha["valor"] is None else str(linha["valor"]) for linha in linhas]


def resolver_antes(
    tipo: str,
    matricula: str,
    competencia: str,
    antes: str | None,
    buscar: BuscarValoresAtuais = buscar_valores_atuais,
) -> tuple[str | None, str | None]:
    """(antes final, erro para a Lana). Sem `antes`, usa o valor único da base; com `antes`, confere.

    Assim a Lana não precisa do `consultar_banco` antes da ferramenta: cada passo a menos é menos chance
    de o grafo esbarrar no limite de passos (A6-128). Falha de acesso ao banco não bloqueia: o backend
    confere de novo no Confirmar.
    Ex.: resolver_antes("TRANSFERENCIA_LOJA", "MATRIC-38", "2025-10", None) -> ("33", None)
    """
    try:
        atuais = buscar(tipo, matricula, competencia)
    except Exception as erro:
        logger.warning(json.dumps({"evento": "conferencia_antes_indisponivel", "erro": str(erro)}, ensure_ascii=False))
        return antes, None
    if antes is None and len(atuais) == 1:
        return atuais[0], None
    return antes, _mensagem_divergencia(matricula, competencia, antes, atuais)


def _mensagem_divergencia(matricula: str, competencia: str, antes: str | None, atuais: list[str | None]) -> str | None:
    if not atuais:
        return f"A {matricula} não tem registro na base para a competência {competencia}; não abra o pedido e avise o usuário."
    if antes in atuais:
        return None
    atual = ", ".join("vazio" if valor is None else valor for valor in atuais)
    return (
        f"O valor 'antes' ({antes}) não confere com a base: o valor atual da {matricula} em {competencia} é {atual}. "
        f"Se o usuário informou {atual}, chame a ferramenta de novo com antes={atual!r}; "
        "se ele informou outro valor, avise o valor atual e não abra o pedido."
    )
