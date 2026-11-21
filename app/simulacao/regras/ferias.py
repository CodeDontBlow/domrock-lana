"""Regra de negócio 5g: dias de férias sem remuneração proporcional de comissão."""
from datetime import date
from fractions import Fraction

from app.simulacao.regras.tipos import EventoIntercorrencia, RegraAplicada
from app.simulacao.regras.validacao import dias_intersecao


def ajuste_ferias(
    eventos: list[EventoIntercorrencia], inicio_mes: date, fim_mes: date, dias_mes: int,
) -> tuple[Fraction, list[RegraAplicada]]:
    """Calcula redução proporcional de dias de férias na competência."""
    regras: list[RegraAplicada] = []
    dias_ferias: set[date] = set()

    for evt in eventos:
        if evt.tipo != "ferias":
            continue
        inter = dias_intersecao(evt.inicio, evt.fim, inicio_mes, fim_mes)
        if inter:
            dias_ferias.update(inter)
            qtd = len(inter)
            s = "s" if qtd != 1 else ""
            periodo = f"{evt.inicio:%d/%m} a {evt.fim:%d/%m}"
            regras.append(RegraAplicada("5g", f"5g — férias de {periodo}: {qtd} dia{s} sem remuneração"))

    if not dias_ferias:
        return Fraction(1, 1), []
    return Fraction(dias_mes - len(dias_ferias), dias_mes), regras
