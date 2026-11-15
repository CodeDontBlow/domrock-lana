from typing import Any

from app.tools.query_tool.dtos import QueryRequestBody
from app.tools.query_tool.service import executar as executar_consulta_banco


def consultar_dados_funcionario_no_banco(matricula: str, competencia: str) -> dict[str, Any]:
    """Reutiliza o serviço da query_tool para consultar os dados atuais do funcionário no banco.

    Evita redundância de código SQL de consulta, aproveitando o schema, prompts e guardrails
    já validados na query_tool.
    """
    pergunta = f"Qual a loja e o cargo da matrícula {matricula.strip().upper()} na competência {competencia.strip()}?"
    resultado = executar_consulta_banco(QueryRequestBody(pergunta=pergunta))
    return resultado.model_dump(mode="json")
