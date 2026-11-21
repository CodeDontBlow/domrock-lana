"""Regras de negócio de vínculo empregatício proporcional: 5c (admissão) e 5d (demissão)."""
from datetime import date
from fractions import Fraction

from app.simulacao.regras.tipos import RegraAplicada


def ajuste_vinculo(
    admissao: date | None, demissao: date | None, ano: int, mes: int, dias_mes: int,
) -> tuple[Fraction, list[RegraAplicada]]:
    """Calcula a fração dos dias trabalhados no mês em caso de admissão ou demissão."""
    adm_no_mes = admissao is not None and admissao.year == ano and admissao.month == mes
    dem_no_mes = demissao is not None and demissao.year == ano and demissao.month == mes
    if adm_no_mes and dem_no_mes:
        assert admissao is not None and demissao is not None
        dias = demissao.day - admissao.day
        if dias < 0:
            raise ValueError(
                f"Data de demissão ({demissao.isoformat()}) anterior à admissão ({admissao.isoformat()}) "
                f"na competência {ano:04d}-{mes:02d}; esperado demissao >= admissao"
            )
        return Fraction(dias, dias_mes), [
            RegraAplicada("5c", f"5c — admissão em {admissao:%d/%m}: {dias} de {dias_mes} dias"),
            RegraAplicada("5d", f"5d — demissão em {demissao:%d/%m}: {dias} de {dias_mes} dias"),
        ]
    if adm_no_mes:
        assert admissao is not None
        dias = dias_mes - admissao.day
        return Fraction(dias, dias_mes), [
            RegraAplicada("5c", f"5c — admissão em {admissao:%d/%m}: {dias} de {dias_mes} dias"),
        ]
    if dem_no_mes:
        assert demissao is not None
        return Fraction(demissao.day, dias_mes), [
            RegraAplicada("5d", f"5d — demissão em {demissao:%d/%m}: {demissao.day} de {dias_mes} dias"),
        ]
    return Fraction(1, 1), []
