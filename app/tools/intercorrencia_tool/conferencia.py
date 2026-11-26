"""Confere na base se a matrícula da intercorrência existe, com SQL fixo (A6-124).

Antes a Lana precisava do `consultar_banco` para isso; o text-to-SQL às vezes inventava tabelas
("funcionarios") e a Lana repetia a consulta até o limite de passos do grafo (A6-128).
"""
import json
import logging
from collections.abc import Callable

from app.core.db import executar_select

logger = logging.getLogger(__name__)

BuscarMatricula = Callable[[str], bool]

SQL_MATRICULA = "SELECT 1 AS existe FROM funcionario WHERE UPPER(matricula) = %(matricula)s LIMIT 1"


def matricula_existe(matricula: str) -> bool:
    """True quando a matrícula está na tabela funcionario.

    Ex.: matricula_existe("MATRIC-12") -> True
    """
    return bool(executar_select(SQL_MATRICULA, {"matricula": matricula.strip().upper()}))


def conferir_matricula(matricula: str, buscar: BuscarMatricula = matricula_existe) -> str | None:
    """Mensagem de erro para a Lana quando a matrícula não existe; None quando existe ou sem acesso ao banco.

    Ex.: conferir_matricula("MATRIC-9999") -> "A matrícula MATRIC-9999 não existe na base; ..."
    """
    try:
        existe = buscar(matricula)
    except Exception as erro:
        logger.warning(json.dumps({"evento": "conferencia_matricula_indisponivel", "erro": str(erro)}, ensure_ascii=False))
        return None
    if existe:
        return None
    return f"A matrícula {matricula} não existe na base; avise o usuário e não abra o pedido."
