"""Validação e extração de intercorrências de RH e cálculo de intersecções de períodos."""
from datetime import date, timedelta
import pandas as pd

from app.simulacao.regras.tipos import COLUNAS_INTERCORRENCIAS, EventoIntercorrencia


def intercorrencias_vazias() -> pd.DataFrame:
    """DataFrame vazio com COLUNAS_INTERCORRENCIAS e as datas tipadas. Ex.: intercorrencias_vazias().empty"""
    tipos = {"matricula": "string", "tipo": "string", "data_inicio": "datetime64[ns]", "data_fim": "datetime64[ns]"}
    return pd.DataFrame({coluna: pd.Series(dtype=tipo) for coluna, tipo in tipos.items()})


def para_data(valor: object) -> date | None:
    """Converte valor para date ou None."""
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, date) and not isinstance(valor, pd.Timestamp):
        return valor
    return pd.Timestamp(valor).date()


def datas_validadas(matricula: str, tipo: str, inicio_bruto: object, fim_bruto: object) -> tuple[date, date | None]:
    """Valida formato e consistência das datas de início e fim da intercorrência."""
    # demissao (correção da data, dec-090) pode vir sem data_fim; afastamento e ferias não.
    inicio, fim = para_data(inicio_bruto), para_data(fim_bruto)
    if inicio is None:
        raise ValueError(f"Intercorrência de {matricula!r} com data_inicio nula; esperado data YYYY-MM-DD")
    if fim is not None and fim < inicio:
        raise ValueError(
            f"Data de fim ({fim.isoformat()}) anterior à data de início ({inicio.isoformat()}) "
            f"na intercorrência de {matricula!r}; esperado fim >= inicio"
        )
    if fim is None and tipo != "demissao":
        raise ValueError(f"Intercorrência {tipo!r} de {matricula!r} sem data_fim; esperado data YYYY-MM-DD")
    return inicio, fim


def validar_e_extrair_eventos(intercorrencias: pd.DataFrame) -> tuple[dict[str, date], dict[str, list[EventoIntercorrencia]]]:
    """Separa demissões e eventos temporais agrupados por matrícula."""
    demissoes: dict[str, date] = {}
    eventos: dict[str, list[EventoIntercorrencia]] = {}
    for linha in intercorrencias.itertuples(index=False):
        matricula, tipo = str(linha.matricula), str(linha.tipo)
        # Regras provisórias aguardando definição do PO: nunca derrubam a apuração com ValueError
        # quando vêm da base da especificação sem data_inicio ou data_fim.
        if tipo == "cobertura_loja":
            continue
        if tipo == "licenca_maternidade":
            inicio, fim = para_data(linha.data_inicio), para_data(linha.data_fim)
            if inicio is None or fim is None or fim < inicio:
                continue
            eventos.setdefault(matricula, []).append(EventoIntercorrencia(tipo, inicio, fim))
            continue
        inicio, fim = datas_validadas(matricula, tipo, linha.data_inicio, linha.data_fim)
        if tipo == "demissao":
            demissoes[matricula] = inicio
        elif fim is not None:
            eventos.setdefault(matricula, []).append(EventoIntercorrencia(tipo, inicio, fim))
    return demissoes, eventos


def dias_intersecao(inicio: date, fim: date, limite_inicio: date, limite_fim: date) -> set[date]:
    """Retorna o conjunto de dias entre inicio e fim que caem dentro de [limite_inicio, limite_fim]."""
    primeiro = max(inicio, limite_inicio)
    ultimo = min(fim, limite_fim)
    if primeiro > ultimo:
        return set()
    return {primeiro + timedelta(days=i) for i in range((ultimo - primeiro).days + 1)}
