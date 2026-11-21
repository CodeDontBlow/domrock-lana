"""Regras de negócio de afastamento médico e licença: 5e (<=15 dias) e 5f (>15 dias)."""
from datetime import date, timedelta
from fractions import Fraction

from app.simulacao.regras.tipos import EventoIntercorrencia, RegraAplicada
from app.simulacao.regras.validacao import dias_intersecao


def coletar_afastamentos(
    eventos: list[EventoIntercorrencia],
    inicio_mes: date,
    fim_mes: date,
) -> tuple[set[date], set[date], int, list[tuple[EventoIntercorrencia, int, int]]]:
    """Coleta dias totais e remunerados (primeiros 15 dias pelo empregador) no mês."""
    dias_total: set[date] = set()
    dias_remunerados: set[date] = set()
    duracao_max = 0
    eventos_mes: list[tuple[EventoIntercorrencia, int, int]] = []

    for evt in eventos:
        if evt.tipo not in ("afastamento", "licenca_maternidade"):
            continue
        inter = dias_intersecao(evt.inicio, evt.fim, inicio_mes, fim_mes)
        if not inter:
            continue
        duracao = (evt.fim - evt.inicio).days + 1
        duracao_max = max(duracao_max, duracao)
        fim_remun = min(evt.fim, evt.inicio + timedelta(days=14))
        remun = dias_intersecao(evt.inicio, fim_remun, inicio_mes, fim_mes)
        dias_total.update(inter)
        dias_remunerados.update(remun)
        eventos_mes.append((evt, len(inter), len(remun)))

    return dias_total, dias_remunerados, duracao_max, eventos_mes


def descrever_afastamento(evt: EventoIntercorrencia, regra_cod: str, qtd_total: int, qtd_remun: int) -> RegraAplicada:
    """Monta a descrição legível da aplicação da regra 5e ou 5f."""
    desc = "todos remunerados" if qtd_remun == qtd_total else f"{qtd_remun} remunerado{'s' if qtd_remun != 1 else ''}"
    s = "s" if qtd_total != 1 else ""
    periodo = f"{evt.inicio:%d/%m} a {evt.fim:%d/%m}"
    return RegraAplicada(regra_cod, f"{regra_cod} — afastamento de {periodo}: {qtd_total} dia{s}, {desc}")


def ajuste_afastamento(
    eventos: list[EventoIntercorrencia],
    inicio_mes: date,
    fim_mes: date,
    dias_mes: int,
) -> tuple[Fraction, bool, bool, list[RegraAplicada]]:
    """Calcula fator, se zera a comissão e se aplica o piso de afastamento."""
    dias_total, dias_remunerados, duracao_max, eventos_mes = coletar_afastamentos(eventos, inicio_mes, fim_mes)
    if not eventos_mes:
        return Fraction(1, 1), False, False, []

    regra_cod = "5e" if duracao_max <= 15 else "5f"
    regras = [descrever_afastamento(evt, regra_cod, total, remun) for evt, total, remun in eventos_mes]
    dias_trabalhados = dias_mes - len(dias_total)
    aplica_piso = len(dias_remunerados) > 0
    if dias_trabalhados == 0:
        return Fraction(1, 1), True, aplica_piso, regras

    fator = Fraction(dias_trabalhados + len(dias_remunerados), dias_trabalhados)
    return fator, False, aplica_piso, regras
