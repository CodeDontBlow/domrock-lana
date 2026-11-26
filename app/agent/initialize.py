from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.core.config import get_ai_model
from app.tools.correcao_tool.tool import registrar_solicitacao_correcao
from app.tools.intercorrencia_tool.tool import registrar_intercorrencia
from app.tools.query_tool.tool import consultar_banco
from app.tools.regra_tool.tool import registrar_parametros_regra


# Iniciando o Estado do agente
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# Compilando as Tools
lana_tools = [
    consultar_banco,
    registrar_parametros_regra,
    registrar_solicitacao_correcao,
    registrar_intercorrencia,
]

# Exportando o modelo com Tools
lana_agent = get_ai_model(ferramentas=lana_tools)
