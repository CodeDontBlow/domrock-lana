from typing import Any
from pydantic import BaseModel, Field

from app.tools.dtos import ToolResultBase

TIPOS_INTERCORRENCIA: dict[str, str] = {
    "FERIAS": "Férias",
    "AFASTAMENTO": "Afastamento",
    "LICENCA_MATERNIDADE": "Licença-maternidade",
    "COBERTURA_LOJA": "Cobertura de loja",
    "DEMISSAO": "Demissão",
}


class SolicitacaoIntercorrencia(BaseModel):
    """Objeto Solicitacao de intercorrência de RH conforme contrato A6-81 / A6-124."""

    categoria: str = "INTERCORRENCIA"
    tipo: str
    tipo_rotulo: str
    matricula: str
    competencia: str
    antes: None = None
    depois: dict[str, Any]
    antes_rotulo: None = None
    depois_rotulo: str
    motivo: str


class SolicitacaoIntercorrenciaToolResult(ToolResultBase):
    """Retorno da ferramenta de registro de intercorrência."""

    solicitacao: dict[str, Any] = Field(
        default_factory=dict,
        description="Dicionário completo da solicitação registrada",
    )
