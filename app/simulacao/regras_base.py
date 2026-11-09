"""Regras base 5c a 5g da apuração de comissões (A6-77).

Calcula os fatores proporcionais de vínculo, férias e afastamento,
além do piso remuneratório de R$ 3.500,00 quando cabível.
"""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction

import pandas as pd

PISO_AFASTAMENTO = 3500.0
COLUNAS_INTERCORRENCIAS = ["matricula", "tipo", "data_inicio", "data_fim"]


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
class _Evento:
    tipo: str
    inicio: date
    fim: date


def intercorrencias_vazias() -> pd.DataFrame:
    """DataFrame vazio com COLUNAS_INTERCORRENCIAS e as datas tipadas. Ex.: intercorrencias_vazias().empty"""
    tipos = {"matricula": "string", "tipo": "string", "data_inicio": "datetime64[ns]", "data_fim": "datetime64[ns]"}
    return pd.DataFrame({coluna: pd.Series(dtype=tipo) for coluna, tipo in tipos.items()})


def calcular_ajustes(rh: pd.DataFrame, intercorrencias: pd.DataFrame) -> dict[tuple[str, str], AjusteMatricula]:
    """Um ajuste por (matricula, competencia) do RH com regra de 5c a 5g. Ex.: calcular_ajustes(rh, intercorrencias)"""
    demissoes, eventos_por_matricula = _validar_e_extrair_eventos(intercorrencias)
    ajustes: dict[tuple[str, str], AjusteMatricula] = {}
    vistos: set[tuple[str, str]] = set()

    for linha in rh.itertuples(index=False):
        chave = (str(linha.matricula), str(linha.competencia))
        if chave in vistos:
            continue
        vistos.add(chave)
        ajuste = _ajustar_linha_rh(linha, demissoes, eventos_por_matricula.get(chave[0], []))
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


def detalhar_base(linha_apuracao: pd.Series) -> list[RegraAplicada]:
    """5a sempre; 5b quando cod_cargo == '150'. Ex.: detalhar_base(linha)"""
    pct = _formatar_pct(float(linha_apuracao["pct_comiss"]))
    regras = [RegraAplicada("5a", f"5a — % da base: {pct}")]
    if str(linha_apuracao["cod_cargo"]) == "150":
        regras.append(RegraAplicada("5b", f"5b — base: venda total da loja {linha_apuracao['cod_loja']}"))
    return regras


def descrever_piso(comissao_sem_piso: float) -> RegraAplicada:
    """Descreve a aplicação do piso de afastamento frente à comissão. Ex.: descrever_piso(600.0)"""
    fixo, comiss = _formatar_moeda(PISO_AFASTAMENTO), _formatar_moeda(comissao_sem_piso)
    if comissao_sem_piso < PISO_AFASTAMENTO:
        return RegraAplicada("piso", f"piso — recebe o fixo de {fixo} (a comissão daria {comiss})")
    return RegraAplicada("piso", f"piso — recebe a comissão de {comiss} (acima do fixo de {fixo})")


def _ajustar_linha_rh(linha: object, demissoes: dict[str, date], eventos: list[_Evento]) -> AjusteMatricula | None:
    matricula, competencia = str(getattr(linha, "matricula")), str(getattr(linha, "competencia"))
    ano, mes = map(int, competencia.split("-"))
    dias_mes = calendar.monthrange(ano, mes)[1]
    inicio_mes, fim_mes = date(ano, mes, 1), date(ano, mes, dias_mes)

    admissao = _para_data(getattr(linha, "data_admissao", None))
    demissao = demissoes.get(matricula, _para_data(getattr(linha, "data_demissao", None)))

    fator_vinc, regras_vinc = _ajuste_vinculo(admissao, demissao, ano, mes, dias_mes)
    fator_fer, regras_fer = _ajuste_ferias(eventos, inicio_mes, fim_mes, dias_mes)
    fator_afast, zera, aplica_piso, regras_afast = _ajuste_afastamento(eventos, inicio_mes, fim_mes, dias_mes)

    regras = tuple(regras_vinc + regras_fer + regras_afast)
    if not regras:
        return None
    return AjusteMatricula(matricula, competencia, fator_vinc * fator_fer * fator_afast, zera, aplica_piso, regras)


def _ajuste_vinculo(
    admissao: date | None, demissao: date | None, ano: int, mes: int, dias_mes: int,
) -> tuple[Fraction, list[RegraAplicada]]:
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


def _ajuste_ferias(
    eventos: list[_Evento], inicio_mes: date, fim_mes: date, dias_mes: int,
) -> tuple[Fraction, list[RegraAplicada]]:
    regras: list[RegraAplicada] = []
    dias_ferias: set[date] = set()

    for evt in eventos:
        if evt.tipo != "ferias":
            continue
        inter = _dias_intersecao(evt.inicio, evt.fim, inicio_mes, fim_mes)
        if inter:
            dias_ferias.update(inter)
            qtd = len(inter)
            s = "s" if qtd != 1 else ""
            periodo = f"{evt.inicio:%d/%m} a {evt.fim:%d/%m}"
            regras.append(RegraAplicada("5g", f"5g — férias de {periodo}: {qtd} dia{s} sem remuneração"))

    if not dias_ferias:
        return Fraction(1, 1), []
    return Fraction(dias_mes - len(dias_ferias), dias_mes), regras


def _ajuste_afastamento(
    eventos: list[_Evento],
    inicio_mes: date,
    fim_mes: date,
    dias_mes: int,
) -> tuple[Fraction, bool, bool, list[RegraAplicada]]:
    dias_total, dias_remunerados, duracao_max, eventos_mes = _coletar_afastamentos(eventos, inicio_mes, fim_mes)
    if not eventos_mes:
        return Fraction(1, 1), False, False, []

    regra_cod = "5e" if duracao_max <= 15 else "5f"
    regras = [_descrever_afastamento(evt, regra_cod, total, remun) for evt, total, remun in eventos_mes]
    dias_trabalhados = dias_mes - len(dias_total)
    aplica_piso = len(dias_remunerados) > 0
    if dias_trabalhados == 0:
        return Fraction(1, 1), True, aplica_piso, regras

    fator = Fraction(dias_trabalhados + len(dias_remunerados), dias_trabalhados)
    return fator, False, aplica_piso, regras


def _coletar_afastamentos(
    eventos: list[_Evento],
    inicio_mes: date,
    fim_mes: date,
) -> tuple[set[date], set[date], int, list[tuple[_Evento, int, int]]]:
    dias_total: set[date] = set()
    dias_remunerados: set[date] = set()
    duracao_max = 0
    eventos_mes: list[tuple[_Evento, int, int]] = []

    for evt in eventos:
        if evt.tipo not in ("afastamento", "licenca_maternidade"):
            continue
        inter = _dias_intersecao(evt.inicio, evt.fim, inicio_mes, fim_mes)
        if not inter:
            continue
        duracao = (evt.fim - evt.inicio).days + 1
        duracao_max = max(duracao_max, duracao)
        fim_remun = min(evt.fim, evt.inicio + timedelta(days=14))
        remun = _dias_intersecao(evt.inicio, fim_remun, inicio_mes, fim_mes)
        dias_total.update(inter)
        dias_remunerados.update(remun)
        eventos_mes.append((evt, len(inter), len(remun)))

    return dias_total, dias_remunerados, duracao_max, eventos_mes


def _descrever_afastamento(evt: _Evento, regra_cod: str, qtd_total: int, qtd_remun: int) -> RegraAplicada:
    desc = "todos remunerados" if qtd_remun == qtd_total else f"{qtd_remun} remunerado{'s' if qtd_remun != 1 else ''}"
    s = "s" if qtd_total != 1 else ""
    periodo = f"{evt.inicio:%d/%m} a {evt.fim:%d/%m}"
    return RegraAplicada(regra_cod, f"{regra_cod} — afastamento de {periodo}: {qtd_total} dia{s}, {desc}")


def _dias_intersecao(inicio: date, fim: date, limite_inicio: date, limite_fim: date) -> set[date]:
    primeiro = max(inicio, limite_inicio)
    ultimo = min(fim, limite_fim)
    if primeiro > ultimo:
        return set()
    return {primeiro + timedelta(days=i) for i in range((ultimo - primeiro).days + 1)}


def _validar_e_extrair_eventos(intercorrencias: pd.DataFrame) -> tuple[dict[str, date], dict[str, list[_Evento]]]:
    demissoes: dict[str, date] = {}
    eventos: dict[str, list[_Evento]] = {}
    for linha in intercorrencias.itertuples(index=False):
        matricula, tipo = str(linha.matricula), str(linha.tipo)
        inicio, fim = _datas_validadas(matricula, tipo, linha.data_inicio, linha.data_fim)
        if tipo == "demissao":
            demissoes[matricula] = inicio
        elif tipo != "cobertura_loja" and fim is not None:
            eventos.setdefault(matricula, []).append(_Evento(tipo, inicio, fim))
    return demissoes, eventos


def _datas_validadas(matricula: str, tipo: str, inicio_bruto: object, fim_bruto: object) -> tuple[date, date | None]:
    # demissao (correção da data, dec-090) e cobertura_loja podem vir sem data_fim; os demais não.
    inicio, fim = _para_data(inicio_bruto), _para_data(fim_bruto)
    if inicio is None:
        raise ValueError(f"Intercorrência de {matricula!r} com data_inicio nula; esperado data YYYY-MM-DD")
    if fim is not None and fim < inicio:
        raise ValueError(
            f"Data de fim ({fim.isoformat()}) anterior à data de início ({inicio.isoformat()}) "
            f"na intercorrência de {matricula!r}; esperado fim >= inicio"
        )
    if fim is None and tipo not in ("demissao", "cobertura_loja"):
        raise ValueError(f"Intercorrência {tipo!r} de {matricula!r} sem data_fim; esperado data YYYY-MM-DD")
    return inicio, fim


def _para_data(valor: object) -> date | None:
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, date) and not isinstance(valor, pd.Timestamp):
        return valor
    return pd.Timestamp(valor).date()


def _formatar_pct(pct: float) -> str:
    texto = f"{pct:.4f}".rstrip("0").rstrip(".")
    return (texto or "0").replace(".", ",") + "%"


def _formatar_moeda(valor: float | Decimal) -> str:
    d = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    partes = f"{d:,.2f}".split(".")
    return f"R$ {partes[0].replace(',', '.')},{partes[1]}"
