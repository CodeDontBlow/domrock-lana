"""Campanha futura calculada sobre um mês histórico (ADR-006).

Dois conceitos distintos: o período da campanha (quando ela vale) e a competência de referência
(o mês histórico usado no cálculo). Não é previsão: os dados da referência são deslocados para o
período da campanha e, opcionalmente, ajustados por um crescimento: valor × (1 + crescimento).

Ex.: Black Friday 2026 (24 a 30/11/2026) sobre nov/2025 -> sugerir_referencia(date(2026, 11, 24)) -> "2025-11"
"""
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.trilha import competencia_por_extenso

CHAVE_REFERENCIA = "competencia_referencia"
CHAVE_CRESCIMENTO = "pct_crescimento"
CRESCIMENTO_MAXIMO = 100.0


@dataclass(frozen=True)
class ReferenciaCalculo:
    """`meses`: quantos meses somar à referência para cair no período da campanha (12 de nov/25 a nov/26)."""

    competencia: str
    pct_crescimento: float
    meses: int

    @property
    def fator(self) -> float:
        """Ex.: 10% -> 1.1"""
        return 1 + self.pct_crescimento / 100

    def competencias_lidas(self, competencias_do_periodo: list[str]) -> list[str]:
        """As competências da base que viram o período. Ex.: ["2026-11"] com meses=12 -> ["2025-11"]"""
        return [_somar_meses(c, -self.meses) for c in competencias_do_periodo]

    def descrever(self) -> str:
        """Ex.: "Calculado sobre nov/2025 (referência), crescimento de 10%." """
        return (f"Calculado sobre {competencia_por_extenso(self.competencia)} (referência), "
                f"crescimento de {_formatar_pct(self.pct_crescimento)}.")


def periodo_futuro(data_fim: date, hoje: date | None = None) -> bool:
    """O período ainda não terminou, então não há histórico completo dele na base."""
    return data_fim >= (hoje or date.today())


def sugerir_referencia(data_inicio: date) -> str:
    """O mesmo mês do ano anterior. Ex.: sugerir_referencia(date(2026, 11, 24)) -> "2025-11" """
    return f"{data_inicio.year - 1}-{data_inicio.month:02d}"


def completar_referencia(valores: dict[str, Any], hoje: date | None = None) -> tuple[dict[str, Any], str | None]:
    """Valores da ficha com a referência do período futuro, e a competência sugerida (None se não sugeriu).

    Sem referência informada, sugere o mesmo mês do ano anterior e o crescimento vazio vira 0%;
    a Lana pede a confirmação dos dois. Período histórico não usa referência: os dois saem da ficha.

    Ex.: completar_referencia({"periodo": {"data_inicio": "2026-11-24", "data_fim": "2026-11-30"}})
         -> ({..., "competencia_referencia": "2025-11", "pct_crescimento": 0.0}, "2025-11")
    """
    periodo = _datas(valores.get("periodo"))
    if periodo is None:
        return valores, None
    data_inicio, data_fim = periodo
    if not periodo_futuro(data_fim, hoje):
        return {**valores, CHAVE_REFERENCIA: None, CHAVE_CRESCIMENTO: None}, None
    completos = dict(valores)
    sugerida = None
    if completos.get(CHAVE_REFERENCIA) in (None, ""):
        sugerida = completos[CHAVE_REFERENCIA] = sugerir_referencia(data_inicio)
    if completos.get(CHAVE_CRESCIMENTO) in (None, ""):
        completos[CHAVE_CRESCIMENTO] = 0.0
    return completos, sugerida


def _datas(periodo: Any) -> tuple[date, date] | None:
    try:
        return date.fromisoformat(str(periodo["data_inicio"])), date.fromisoformat(str(periodo["data_fim"]))
    except (KeyError, TypeError, ValueError):
        return None


def ler_referencia(
    valores: dict[str, Any], data_inicio: date, data_fim: date, hoje: date | None = None,
) -> tuple[ReferenciaCalculo | None, list[str]]:
    """A referência do período futuro e os erros encontrados; período histórico ignora os dois campos.

    Ex.: ler_referencia({"competencia_referencia": "2025-11", "pct_crescimento": 10}, nov26_ini, nov26_fim)
         -> (ReferenciaCalculo("2025-11", 10.0, 12), [])
    """
    hoje = hoje or date.today()
    if not periodo_futuro(data_fim, hoje):
        return None, []
    erros: list[str] = []
    competencia = _ler_competencia(valores.get(CHAVE_REFERENCIA), data_inicio, erros)
    crescimento = _ler_crescimento(valores.get(CHAVE_CRESCIMENTO), erros)
    if competencia is None or crescimento is None:
        return None, erros
    meses = _meses_entre(competencia, f"{data_inicio:%Y-%m}")
    if _somar_meses(f"{data_fim:%Y-%m}", -meses) >= f"{hoje:%Y-%m}":
        erros.append(f"{CHAVE_REFERENCIA}: o período deslocado para {competencia} ainda não tem histórico "
                     f"completo; escolha um mês anterior a {hoje:%Y-%m}")
        return None, erros
    return ReferenciaCalculo(competencia, crescimento, meses), []


def _ler_competencia(valor: Any, data_inicio: date, erros: list[str]) -> str | None:
    if valor is None or valor == "":
        erros.append(f"{CHAVE_REFERENCIA}: obrigatória para período futuro "
                     f"(sugestão: {sugerir_referencia(data_inicio)}), recebido {valor!r}")
        return None
    texto = str(valor)
    ano, _, mes = texto.partition("-")
    if not (len(ano) == 4 and ano.isdigit() and len(mes) == 2 and mes.isdigit() and 1 <= int(mes) <= 12):
        erros.append(f"{CHAVE_REFERENCIA}: esperado mês em YYYY-MM, recebido {valor!r}")
        return None
    return texto


def _ler_crescimento(valor: Any, erros: list[str]) -> float | None:
    """Vazio vale 0% (a campanha repete a referência)."""
    if valor is None or valor == "":
        return 0.0
    try:
        pct = float(valor)
    except (TypeError, ValueError):
        erros.append(f"{CHAVE_CRESCIMENTO}: esperado número, recebido {valor!r}")
        return None
    if not 0 <= pct <= CRESCIMENTO_MAXIMO:
        erros.append(f"{CHAVE_CRESCIMENTO}: esperado percentual de 0 a {CRESCIMENTO_MAXIMO:.0f}, recebido {pct}")
        return None
    return pct


def _meses_entre(de: str, ate: str) -> int:
    """Ex.: _meses_entre("2025-11", "2026-11") -> 12"""
    ano_de, mes_de = map(int, de.split("-"))
    ano_ate, mes_ate = map(int, ate.split("-"))
    return (ano_ate - ano_de) * 12 + (mes_ate - mes_de)


def _somar_meses(competencia: str, meses: int) -> str:
    """Ex.: _somar_meses("2026-01", -2) -> "2025-11" """
    ano, mes = map(int, competencia.split("-"))
    total = ano * 12 + (mes - 1) + meses
    return f"{total // 12}-{total % 12 + 1:02d}"


def _formatar_pct(valor: float) -> str:
    """Ex.: 10.0 -> "10%"; 2.5 -> "2,5%" """
    return f"{valor:g}".replace(".", ",") + "%"
