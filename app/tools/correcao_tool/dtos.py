from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.tools.dtos import ToolResultBase


class TipoCorrecao(StrEnum):
    """Tipos de solicitação de alteração com rótulos amigáveis para visualização."""

    TRANSFERENCIA_LOJA = "Transferência de loja"
    MUDANCA_CARGO = "Mudança de cargo"
    DATA_DEMISSAO = "Data de demissão"
    DATA_ADMISSAO = "Data de admissão"
    CORRECAO_VENDA = "Correção de venda"
    EXCLUSAO = "Exclusão"
    ATUALIZACAO = "Atualização"
    CORRECAO = "Correção"


def normalizar_tipo(tipo: str) -> str:
    t = tipo.strip().lower()
    if "loja" in t or "transf" in t:
        return TipoCorrecao.TRANSFERENCIA_LOJA.value
    if "cargo" in t:
        return TipoCorrecao.MUDANCA_CARGO.value
    if "demiss" in t or "deslig" in t:
        return TipoCorrecao.DATA_DEMISSAO.value
    if "admiss" in t:
        return TipoCorrecao.DATA_ADMISSAO.value
    if "venda" in t:
        return TipoCorrecao.CORRECAO_VENDA.value
    if "exclu" in t or "delet" in t or "remov" in t:
        return TipoCorrecao.EXCLUSAO.value
    if "atualiz" in t:
        return TipoCorrecao.ATUALIZACAO.value
    if "correc" in t or "correç" in t:
        return TipoCorrecao.CORRECAO.value
    return tipo.strip().capitalize()


def codigo_backend_tipo(tipo: str) -> str:
    t = tipo.strip().lower()
    if "loja" in t or "transf" in t:
        return "TRANSFERENCIA_LOJA"
    if "cargo" in t:
        return "TROCA_CARGO"
    if "demiss" in t or "deslig" in t:
        return "DATA_DEMISSAO"
    if "admiss" in t:
        return "DATA_ADMISSAO"
    return "TRANSFERENCIA_LOJA"


class SolicitacaoCorrecao(BaseModel):
    id: str = Field(
        default_factory=lambda: f"solic-{uuid4().hex[:8]}",
        description="Identificador único da solicitação no front",
    )
    tipo: str = Field(
        ...,
        description="Nome amigável do tipo da alteração (ex: 'Transferência de loja')",
    )
    tipo_alteracao: str = Field(
        ...,
        description="Código técnico da alteração no backend (ex: 'TRANSFERENCIA_LOJA')",
    )
    matricula: str = Field(
        ...,
        description="Matrícula do funcionário afetado (ex: 'MATRIC-38')",
    )
    competencia: str = Field(
        ...,
        description="Competência estritamente no formato MM/yyyy (ex: '10/2025')",
    )
    competencia_iso: str = Field(
        default="",
        description="Competência no formato ISO yyyy-MM (ex: '2025-10')",
    )
    antes: str = Field(
        ...,
        description="Valor anterior confirmado na base (ex: 'loja 5')",
    )
    depois: str = Field(
        ...,
        description="Valor novo solicitado (ex: 'loja 8')",
    )
    valor_antes: str = Field(
        default="",
        description="Código de negócio do valor anterior (ex: '5')",
    )
    valor_depois: str = Field(
        default="",
        description="Código de negócio do valor novo (ex: '8')",
    )
    motivo: str = Field(
        ...,
        description="Motivo ou sugestão de justificativa para a alteração",
    )
    origem: str = Field(
        default="LANA",
        description="Origem da solicitação: sempre 'LANA'",
    )
    status: str = Field(
        default="PENDENTE_APROVACAO",
        description="Estado da solicitação: 'PENDENTE_APROVACAO', 'APROVADO' ou 'REPROVADO'",
    )
    sql: str = Field(
        ...,
        description="Código SQL de alteração gerado para avaliação dos supervisores",
    )
    criado_em: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp de criação da solicitação em UTC",
    )


class SolicitacaoCorrecaoToolResult(ToolResultBase):
    """Retorno unificado da ferramenta de registro de solicitação de correção."""

    solicitacao: dict[str, Any] = Field(
        default_factory=dict,
        description="Dicionário completo da solicitação registrada",
    )
