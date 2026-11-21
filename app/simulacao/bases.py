"""Carga das bases de uma simulação a partir do Postgres do backend.

As linhas nunca passam pelo contexto da LLM: vão para o baseline e para o executor.
Competência é sempre texto `YYYY-MM`; `data_venda` guarda a data real (em nov/25 há vendas
de 24 a 28/11), enquanto loja e cargo são vínculos mensais (dia 1º).
"""
import calendar
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Protocol

import pandas as pd

from app.simulacao.regras_base import COLUNAS_INTERCORRENCIAS, intercorrencias_vazias

logger = logging.getLogger(__name__)

SQL_RH = """
SELECT f.matricula, to_char(fl.date_ref, 'YYYY-MM') AS competencia,
       l.cod_loja, m.cod_marca, c.cod_cargo,
       f.data_admissao, f.data_demissao
FROM funcionario f
JOIN funcionario_loja fl ON fl.funcionario_id = f.id
JOIN loja l ON l.id = fl.loja_id
JOIN marca m ON m.id = l.marca_id
JOIN funcionario_cargo fc ON fc.funcionario_id = f.id AND fc.date_ref = fl.date_ref
JOIN cargo c ON c.id = fc.cargo_id
WHERE to_char(fl.date_ref, 'YYYY-MM') = ANY(%(competencias)s)
"""

SQL_VENDAS = """
SELECT f.matricula, to_char(v.date_ref, 'YYYY-MM') AS competencia,
       v.date_ref AS data_venda, v.vlr_venda::float8 AS vlr_venda,
       l.cod_loja, m.cod_marca, c.cod_cargo
FROM venda v
JOIN funcionario f ON f.id = v.funcionario_id
JOIN funcionario_loja fl ON fl.funcionario_id = v.funcionario_id
     AND fl.date_ref = date_trunc('month', v.date_ref)::date
JOIN loja l ON l.id = fl.loja_id
JOIN marca m ON m.id = l.marca_id
JOIN funcionario_cargo fc ON fc.funcionario_id = v.funcionario_id AND fc.date_ref = fl.date_ref
JOIN cargo c ON c.id = fc.cargo_id
WHERE to_char(v.date_ref, 'YYYY-MM') = ANY(%(competencias)s)
"""

# A tabela de % é única (não varia por competência); vale a importação mais recente.
SQL_COMISSOES = """
SELECT m.cod_marca, c.cod_cargo, mc.pct_comiss::float8 AS pct_comiss
FROM marca_cargo mc
JOIN marca m ON m.id = mc.marca_id
JOIN cargo c ON c.id = mc.cargo_id
WHERE mc.date_ref = (SELECT max(date_ref) FROM marca_cargo)
"""

SQL_INTERCORRENCIAS = """
SELECT DISTINCT matricula, tipo, data_inicio, data_fim
FROM evento_rh
WHERE data_inicio IS NOT NULL
  AND (
      (tipo = 'demissao' AND to_char(data_inicio, 'YYYY-MM') = ANY(%(competencias)s))
      OR (tipo <> 'demissao' AND data_fim IS NULL AND data_inicio <= %(fim_periodo)s)
      OR (tipo <> 'demissao' AND data_fim IS NOT NULL
          AND data_inicio <= %(fim_periodo)s AND data_fim >= %(inicio_periodo)s)
  )
ORDER BY data_inicio, matricula, tipo
"""

SQL_INTERCORRENCIAS_PENDENTES = r"""
SELECT COUNT(*)::int AS total
FROM solicitacao_alteracao
WHERE status = 'PENDENTE'
  AND tipo IN ('AFASTAMENTO', 'FERIAS', 'LICENCA_MATERNIDADE', 'COBERTURA_LOJA', 'DEMISSAO')
  AND (
      (
          tipo = 'DEMISSAO'
          AND to_char(
              CASE WHEN (valor_depois->>'data_inicio') ~ '^\d{4}-\d{2}-\d{2}$'
                   THEN (valor_depois->>'data_inicio')::date END,
              'YYYY-MM'
          ) = ANY(%(competencias)s)
      )
      OR (
          tipo <> 'DEMISSAO'
          AND (
              CASE WHEN (valor_depois->>'data_inicio') ~ '^\d{4}-\d{2}-\d{2}$'
                   THEN (valor_depois->>'data_inicio')::date END
          ) <= %(fim_periodo)s
          AND (
              valor_depois->>'data_fim' IS NULL
              OR (
                  CASE WHEN (valor_depois->>'data_fim') ~ '^\d{4}-\d{2}-\d{2}$'
                       THEN (valor_depois->>'data_fim')::date END
              ) >= %(inicio_periodo)s
          )
      )
  )
"""

COLUNAS_DATA = ("data_venda", "data_admissao", "data_demissao", "data_inicio", "data_fim")

# As tabelas que as queries das bases leem, para a trilha (contrato 2.2).
TABELAS_DAS_BASES = (
    "cargo", "evento_rh", "funcionario", "funcionario_cargo", "funcionario_loja",
    "loja", "marca", "marca_cargo", "solicitacao_alteracao", "venda",
)
SQL_DAS_BASES = "\n".join(
    sql.strip() + ";"
    for sql in (SQL_RH, SQL_VENDAS, SQL_COMISSOES, SQL_INTERCORRENCIAS, SQL_INTERCORRENCIAS_PENDENTES)
)


@dataclass(frozen=True)
class BasesSimulacao:
    """As bases de um período: `rh`, `vendas`, `comissoes` (pct literal: 2.5 = 2,5%) e intercorrências."""

    rh: pd.DataFrame
    vendas: pd.DataFrame
    comissoes: pd.DataFrame
    intercorrencias: pd.DataFrame = field(default_factory=intercorrencias_vazias)
    intercorrencias_pendentes: int = 0

    def como_dict(self) -> dict[str, pd.DataFrame]:
        return {"rh": self.rh, "vendas": self.vendas, "comissoes": self.comissoes}


class FonteBases(Protocol):
    def carregar(self, competencias: list[str]) -> BasesSimulacao: ...


class ConexaoDb(Protocol):
    def cursor(self) -> Any: ...


class PostgresFonteBases:
    """Lê as bases do Postgres. Ex.: PostgresFonteBases(get_connection).carregar(["2025-10"])"""

    def __init__(self, abrir_conexao: Callable[[], AbstractContextManager[ConexaoDb]]) -> None:
        self._abrir_conexao = abrir_conexao

    def carregar(self, competencias: list[str]) -> BasesSimulacao:
        parametros = {"competencias": competencias}
        with self._abrir_conexao() as conexao:
            rh = _consultar(conexao, SQL_RH, parametros)
            vendas = _consultar(conexao, SQL_VENDAS, parametros)
            comissoes = _consultar(conexao, SQL_COMISSOES, {})
            if competencias:
                inicio_periodo, fim_periodo = _limites_competencias(competencias)
                params_inter = {
                    "competencias": competencias,
                    "inicio_periodo": inicio_periodo,
                    "fim_periodo": fim_periodo,
                }
                intercorrencias = _consultar_intercorrencias(conexao, params_inter)
                pendentes = _contar_pendentes(conexao, params_inter)
            else:
                intercorrencias = intercorrencias_vazias()
                pendentes = 0
            return BasesSimulacao(
                rh=rh,
                vendas=vendas,
                comissoes=comissoes,
                intercorrencias=intercorrencias,
                intercorrencias_pendentes=pendentes,
            )


def _limites_competencias(competencias: list[str]) -> tuple[date, date]:
    ordenadas = sorted(competencias)
    ano_i, mes_i = map(int, ordenadas[0].split("-"))
    ano_f, mes_f = map(int, ordenadas[-1].split("-"))
    return date(ano_i, mes_i, 1), date(ano_f, mes_f, calendar.monthrange(ano_f, mes_f)[1])


def _consultar_intercorrencias(conexao: ConexaoDb, parametros: dict[str, Any]) -> pd.DataFrame:
    tabela = _consultar(conexao, SQL_INTERCORRENCIAS, parametros)
    if tabela.empty:
        return intercorrencias_vazias()
    tabela.loc[tabela["tipo"] == "demissao", "data_fim"] = pd.NaT
    total_antes = len(tabela)
    valida = (
        tabela["tipo"].isin(["demissao", "cobertura_loja"])
        | (tabela["data_fim"].notna() & (tabela["data_fim"] >= tabela["data_inicio"]))
    )
    tabela = tabela.loc[valida, COLUNAS_INTERCORRENCIAS].reset_index(drop=True)
    descartadas = total_antes - len(tabela)
    if descartadas > 0:
        logger.warning(
            "%d intercorrência(s) de RH ignorada(s): sem data_fim ou data_fim anterior a data_inicio.",
            descartadas,
        )
    if tabela.empty:
        return intercorrencias_vazias()
    return tabela


def _contar_pendentes(conexao: ConexaoDb, parametros: dict[str, Any]) -> int:
    with conexao.cursor() as cursor:
        cursor.execute(SQL_INTERCORRENCIAS_PENDENTES, parametros)
        linha = cursor.fetchone()
    return int(linha[0]) if linha and linha[0] is not None else 0


def _consultar(conexao: ConexaoDb, sql: str, parametros: dict[str, Any]) -> pd.DataFrame:
    with conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        colunas = [coluna[0] for coluna in cursor.description]
        tabela = pd.DataFrame(cursor.fetchall(), columns=colunas)
    return _tipar_datas(tabela)


def _tipar_datas(tabela: pd.DataFrame) -> pd.DataFrame:
    for coluna in COLUNAS_DATA:
        if coluna in tabela.columns:
            tabela[coluna] = pd.to_datetime(tabela[coluna])
    return tabela


def competencias_do_periodo(inicio: date, fim: date) -> list[str]:
    """Meses tocados pelo período. Ex.: (2025-11-24, 2025-12-05) -> ["2025-11", "2025-12"]"""
    meses = pd.period_range(start=inicio, end=fim, freq="M")
    return [str(mes) for mes in meses]


def deslocar_bases(bases: BasesSimulacao, meses: int, fator: float) -> BasesSimulacao:
    """As bases da competência de referência no período da campanha (ADR-006): sem previsão.

    Datas e competências andam `meses` (o dia é mantido, ou vira o último do mês mais curto) e cada
    venda é multiplicada por `fator` (1 + crescimento). Admissão e demissão andam junto, para as
    regras 5c e 5d darem o mesmo resultado da referência.
    Ex.: deslocar_bases(bases_nov25, 12, 1.1).vendas["data_venda"] -> datas de nov/2026, vendas +10%
    """
    rh = _deslocar(bases.rh, meses)
    vendas = _deslocar(bases.vendas, meses)
    vendas["vlr_venda"] = vendas["vlr_venda"] * fator
    intercorrencias = _deslocar(bases.intercorrencias, meses, colunas=("data_inicio", "data_fim"))
    # replace, não um BasesSimulacao novo: o resto das bases (ex.: intercorrencias_pendentes, A6-108) vem junto.
    return replace(bases, rh=rh, vendas=vendas, intercorrencias=intercorrencias)


def _deslocar(tabela: pd.DataFrame, meses: int, colunas: tuple[str, ...] = COLUNAS_DATA) -> pd.DataFrame:
    copia = tabela.copy()
    for coluna in colunas:
        if coluna in copia.columns:
            copia[coluna] = pd.to_datetime(copia[coluna]) + pd.DateOffset(months=meses)
    if "competencia" in copia.columns:
        copia["competencia"] = [
            str(pd.Period(c, freq="M") + meses) for c in copia["competencia"]
        ]
    return copia
