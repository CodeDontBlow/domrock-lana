"""Tipos de dados e constantes compartilhadas para o cálculo de regras de RH (5c a 5g e piso)."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction

PISO_AFASTAMENTO: float = 3500.0
COLUNAS_INTERCORRENCIAS: list[str] = ["matricula", "tipo", "data_inicio", "data_fim"]


@dataclass(frozen=True)
class RegraAplicada:
    regra: str
    descricao: str


@dataclass(frozen=True)
class AjusteMatricula:
    matricula: str
    competencia: str
    fator: Fraction
    zera: bool
    aplica_piso: bool
    regras: tuple[RegraAplicada, ...]


@dataclass(frozen=True)
class EventoIntercorrencia:
    tipo: str
    inicio: date
    fim: date


# Alias para retrocompatibilidade
_Evento = EventoIntercorrencia


def formatar_pct(pct: float) -> str:
    """Formata percentual com vírgula e remove zeros extras (ex.: 1.5 -> '1,5%')."""
    texto = f"{pct:.4f}".rstrip("0").rstrip(".")
    return (texto or "0").replace(".", ",") + "%"


def formatar_moeda(valor: float | Decimal) -> str:
    """Formata valor em Real brasileiro no padrão 'R$ 1.234,56'."""
    d = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    partes = f"{d:,.2f}".split(".")
    return f"R$ {partes[0].replace(',', '.')},{partes[1]}"
