"""Aplicação de ajustes de RH na linha de apuração e no DataFrame consolidado."""
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
import pandas as pd

from app.simulacao.regras.afastamento import ajuste_afastamento
from app.simulacao.regras.ferias import ajuste_ferias
from app.simulacao.regras.tipos import AjusteMatricula, EventoIntercorrencia, PISO_AFASTAMENTO
from app.simulacao.regras.validacao import para_data, validar_e_extrair_eventos
from app.simulacao.regras.vinculo import ajuste_vinculo


def ajustar_linha_rh(linha: object, demissoes: dict[str, date], eventos: list[EventoIntercorrencia]) -> AjusteMatricula | None:
    """Calcula os fatores combinados de vínculo, férias e afastamento para uma linha do RH."""
    matricula, competencia = str(getattr(linha, "matricula")), str(getattr(linha, "competencia"))
    ano, mes = map(int, competencia.split("-"))
    dias_mes = calendar.monthrange(ano, mes)[1]
    inicio_mes, fim_mes = date(ano, mes, 1), date(ano, mes, dias_mes)

    admissao = para_data(getattr(linha, "data_admissao", None))
    demissao = demissoes.get(matricula, para_data(getattr(linha, "data_demissao", None)))

    fator_vinc, regras_vinc = ajuste_vinculo(admissao, demissao, ano, mes, dias_mes)
    fator_fer, regras_fer = ajuste_ferias(eventos, inicio_mes, fim_mes, dias_mes)
    fator_afast, zera, aplica_piso, regras_afast = ajuste_afastamento(eventos, inicio_mes, fim_mes, dias_mes)

    regras = tuple(regras_vinc + regras_fer + regras_afast)
    if not regras:
        return None
    return AjusteMatricula(matricula, competencia, fator_vinc * fator_fer * fator_afast, zera, aplica_piso, regras)


def calcular_ajustes(rh: pd.DataFrame, intercorrencias: pd.DataFrame) -> dict[tuple[str, str], AjusteMatricula]:
    """Um ajuste por (matricula, competencia) do RH com regra de 5c a 5g. Ex.: calcular_ajustes(rh, intercorrencias)"""
    demissoes, eventos_por_matricula = validar_e_extrair_eventos(intercorrencias)
    ajustes: dict[tuple[str, str], AjusteMatricula] = {}
    vistos: set[tuple[str, str]] = set()

    for linha in rh.itertuples(index=False):
        chave = (str(linha.matricula), str(linha.competencia))
        if chave in vistos:
            continue
        vistos.add(chave)
        ajuste = ajustar_linha_rh(linha, demissoes, eventos_por_matricula.get(chave[0], []))
        if ajuste is not None:
            ajustes[chave] = ajuste
    return ajustes


def ajustar_comissao(comissao: float, ajuste: AjusteMatricula | None) -> float:
    """Aplica fator, zera e piso, nessa ordem. Ex.: ajustar_comissao(3100.0, ajuste)"""
    if ajuste is None:
        return float(comissao)
    produto = Fraction(str(comissao)) * ajuste.fator
    num, den = Decimal(produto.numerator), Decimal(produto.denominator)
    valor = (num / den).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    if ajuste.zera:
        valor = Decimal("0.00")
    if ajuste.aplica_piso:
        valor = max(valor, Decimal(str(PISO_AFASTAMENTO)))
    return float(valor)


def aplicar_ajustes(
    apuracao: pd.DataFrame,
    ajustes: dict[tuple[str, str], AjusteMatricula],
    colunas: list[str],
) -> pd.DataFrame:
    """Cópia da apuração com colunas ajustadas linha a linha. Ex.: aplicar_ajustes(df, ajustes, ['comissao'])"""
    copia = apuracao.copy()
    for col in colunas:
        copia[col] = [
            ajustar_comissao(float(val), ajustes.get((str(m), str(c))))
            for m, c, val in zip(copia["matricula"], copia["competencia"], copia[col])
        ]
    return copia
