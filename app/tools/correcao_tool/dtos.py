from typing import Any
from pydantic import BaseModel, Field

from app.tools.dtos import ToolResultBase

TIPOS_CORRECAO: dict[str, str] = {
    "TRANSFERENCIA_LOJA": "Transferência de loja",
    "TROCA_CARGO": "Troca de cargo",
    "DATA_ADMISSAO": "Data de admissão",
    "DATA_DEMISSAO": "Data de demissão",
}


class SolicitacaoCorrecao(BaseModel):
    """Objeto Solicitacao de correção da base de dados conforme contrato A6-81."""

    categoria: str = "CORRECAO"
    tipo: str
    tipo_rotulo: str
    matricula: str
    competencia: str
    antes: str | None = None
    depois: str
    antes_rotulo: str | None = None
    depois_rotulo: str
    motivo: str


class SolicitacaoCorrecaoToolResult(ToolResultBase):
    """Retorno unificado da ferramenta de registro de solicitação de correção."""

    solicitacao: dict[str, Any] = Field(
        default_factory=dict,
        description="Dicionário completo da solicitação registrada",
    )
