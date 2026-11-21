"""Testes das bases da simulação (A6-77 / A6-108)."""
import logging
from contextlib import contextmanager
from datetime import date
from typing import Any

import pandas as pd
import pytest

from app.simulacao.bases import (
    BasesSimulacao,
    PostgresFonteBases,
    SQL_INTERCORRENCIAS,
    SQL_INTERCORRENCIAS_PENDENTES,
    TABELAS_DAS_BASES,
    _consultar_intercorrencias,
    deslocar_bases,
)
from tests.fakes import bases_pequenas


def test_bases_simulacao_sem_intercorrencias_usa_padrao_vazio() -> None:
    bases = bases_pequenas()

    assert bases.intercorrencias.empty
    assert bases.intercorrencias_pendentes == 0
    assert list(bases.intercorrencias.columns) == ["matricula", "tipo", "data_inicio", "data_fim"]
    dicionario = bases.como_dict()
    assert set(dicionario.keys()) == {"rh", "vendas", "comissoes"}
    assert len(dicionario) == 3


def test_bases_simulacao_com_intercorrencias_preserva_dataframe() -> None:
    inter = pd.DataFrame([{"matricula": "M1", "tipo": "ferias", "data_inicio": "2025-11-01", "data_fim": "2025-11-10"}])
    bases = BasesSimulacao(
        rh=bases_pequenas().rh, vendas=bases_pequenas().vendas, comissoes=bases_pequenas().comissoes,
        intercorrencias=inter, intercorrencias_pendentes=2,
    )

    assert len(bases.intercorrencias) == 1
    assert bases.intercorrencias_pendentes == 2
    assert bases.como_dict() == {"rh": bases.rh, "vendas": bases.vendas, "comissoes": bases.comissoes}


class _FakeCursor:
    def __init__(self, respostas: list[tuple[list[str], list[tuple[Any, ...]]]]) -> None:
        self._respostas = iter(respostas)
        self.executadas: list[tuple[str, dict[str, Any]]] = []
        self.description: list[tuple[str]] = []
        self._linhas: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, parametros: dict[str, Any]) -> None:
        self.executadas.append((sql, parametros))
        colunas, linhas = next(self._respostas)
        self.description = [(col,) for col in colunas]
        self._linhas = linhas

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._linhas

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._linhas[0] if self._linhas else None


class _FakeConexao:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _FakeCursor:
        return self._cursor


def test_postgres_fonte_bases_carrega_intercorrencias_aprovadas_e_conta_pendentes() -> None:
    cursor = _FakeCursor([
        (
            ["matricula", "competencia", "cod_loja", "cod_marca", "cod_cargo", "data_admissao", "data_demissao"],
            [("MATRIC-58", "2025-07", "1", "10", "100", date(2020, 1, 1), None)],
        ),
        (
            ["matricula", "competencia", "data_venda", "vlr_venda", "cod_loja", "cod_marca", "cod_cargo"],
            [("MATRIC-58", "2025-07", date(2025, 7, 5), 50000.0, "1", "10", "100")],
        ),
        (
            ["cod_marca", "cod_cargo", "pct_comiss"],
            [("10", "100", 2.0)],
        ),
        (
            ["matricula", "tipo", "data_inicio", "data_fim"],
            [
                ("MATRIC-58", "afastamento", date(2025, 7, 10), date(2025, 7, 25)),
                ("MATRIC-62", "demissao", date(2025, 7, 15), None),
            ],
        ),
        (["total"], [(1,)]),
    ])

    @contextmanager
    def abrir():
        yield _FakeConexao(cursor)

    bases = PostgresFonteBases(abrir).carregar(["2025-07"])

    assert list(bases.intercorrencias.columns) == ["matricula", "tipo", "data_inicio", "data_fim"]
    assert len(bases.intercorrencias) == 2
    assert pd.api.types.is_datetime64_any_dtype(bases.intercorrencias["data_inicio"])
    assert pd.api.types.is_datetime64_any_dtype(bases.intercorrencias["data_fim"])
    assert bases.intercorrencias_pendentes == 1

    sql_inter, params_inter = cursor.executadas[3]
    sql_pend, params_pend = cursor.executadas[4]
    assert sql_inter == SQL_INTERCORRENCIAS
    assert sql_pend == SQL_INTERCORRENCIAS_PENDENTES
    assert params_inter == {
        "competencias": ["2025-07"],
        "inicio_periodo": date(2025, 7, 1),
        "fim_periodo": date(2025, 7, 31),
    }
    assert params_pend == params_inter
    assert {"evento_rh", "solicitacao_alteracao"} <= set(TABELAS_DAS_BASES)


def test_postgres_fonte_bases_sem_intercorrencias_devolve_dataframe_vazio_tipado() -> None:
    cursor = _FakeCursor([
        (["matricula", "competencia", "cod_loja", "cod_marca", "cod_cargo", "data_admissao", "data_demissao"], []),
        (["matricula", "competencia", "data_venda", "vlr_venda", "cod_loja", "cod_marca", "cod_cargo"], []),
        (["cod_marca", "cod_cargo", "pct_comiss"], []),
        (["matricula", "tipo", "data_inicio", "data_fim"], []),
        (["total"], [(0,)]),
    ])

    @contextmanager
    def abrir():
        yield _FakeConexao(cursor)

    bases = PostgresFonteBases(abrir).carregar(["2025-10"])

    assert bases.intercorrencias.empty
    assert list(bases.intercorrencias.columns) == ["matricula", "tipo", "data_inicio", "data_fim"]
    assert pd.api.types.is_datetime64_any_dtype(bases.intercorrencias["data_inicio"])
    assert bases.intercorrencias_pendentes == 0


def test_consultar_intercorrencias_ignora_linhas_invalidas() -> None:
    cursor = _FakeCursor([
        (
            ["matricula", "tipo", "data_inicio", "data_fim"],
            [
                ("MATRIC-1", "ferias", date(2025, 7, 1), date(2025, 7, 10)),
                ("MATRIC-2", "ferias", date(2025, 7, 5), None),
                ("MATRIC-3", "ferias", date(2025, 7, 15), date(2025, 7, 10)),
                ("MATRIC-4", "afastamento", date(2025, 7, 8), date(2025, 7, 8)),
                ("MATRIC-5", "afastamento", date(2025, 7, 10), None),
                ("MATRIC-6", "afastamento", date(2025, 7, 20), date(2025, 7, 10)),
                ("MATRIC-7", "licenca_maternidade", date(2025, 7, 1), None),
                ("MATRIC-8", "demissao", date(2025, 7, 15), None),
                ("MATRIC-9", "cobertura_loja", date(2025, 7, 20), None),
                ("MATRIC-10", "demissao", date(2025, 7, 20), date(2025, 7, 10)),
            ],
        ),
    ])

    resultado = _consultar_intercorrencias(
        _FakeConexao(cursor),
        {
            "competencias": ["2025-07"],
            "inicio_periodo": date(2025, 7, 1),
            "fim_periodo": date(2025, 7, 31),
        },
    )

    assert list(resultado.columns) == ["matricula", "tipo", "data_inicio", "data_fim"]
    assert list(resultado["matricula"]) == ["MATRIC-1", "MATRIC-4", "MATRIC-8", "MATRIC-9", "MATRIC-10"]
    assert list(resultado["tipo"]) == ["ferias", "afastamento", "demissao", "cobertura_loja", "demissao"]
    assert list(resultado.index) == [0, 1, 2, 3, 4]
    assert pd.api.types.is_datetime64_any_dtype(resultado["data_inicio"])
    assert pd.api.types.is_datetime64_any_dtype(resultado["data_fim"])
    assert pd.isna(resultado.loc[resultado["matricula"] == "MATRIC-10", "data_fim"].iloc[0])
    assert resultado.loc[resultado["tipo"] == "demissao", "data_fim"].isna().all()


def test_consultar_intercorrencias_todas_invalidas_retorna_vazio_tipado() -> None:
    cursor = _FakeCursor([
        (
            ["matricula", "tipo", "data_inicio", "data_fim"],
            [
                ("MATRIC-1", "ferias", date(2025, 7, 5), None),
                ("MATRIC-2", "afastamento", date(2025, 7, 15), date(2025, 7, 10)),
            ],
        ),
    ])

    resultado = _consultar_intercorrencias(
        _FakeConexao(cursor),
        {
            "competencias": ["2025-07"],
            "inicio_periodo": date(2025, 7, 1),
            "fim_periodo": date(2025, 7, 31),
        },
    )

    assert resultado.empty
    assert list(resultado.columns) == ["matricula", "tipo", "data_inicio", "data_fim"]
    assert pd.api.types.is_datetime64_any_dtype(resultado["data_inicio"])
    assert pd.api.types.is_datetime64_any_dtype(resultado["data_fim"])


def test_queries_intercorrencias_determinismo_e_blindagem_jsonb() -> None:
    assert SQL_INTERCORRENCIAS.strip().endswith("ORDER BY data_inicio, matricula, tipo")
    assert "to_char(competencia" not in SQL_INTERCORRENCIAS_PENDENTES
    assert r"CASE WHEN (valor_depois->>'data_inicio') ~ '^\d{4}-\d{2}-\d{2}$'" in SQL_INTERCORRENCIAS_PENDENTES
    assert r"CASE WHEN (valor_depois->>'data_fim') ~ '^\d{4}-\d{2}-\d{2}$'" in SQL_INTERCORRENCIAS_PENDENTES


def test_consultar_intercorrencias_emite_warning_apenas_para_datas_invalidas(
    caplog: pytest.LogCaptureFixture,
) -> None:
    parametros = {
        "competencias": ["2025-07"],
        "inicio_periodo": date(2025, 7, 1),
        "fim_periodo": date(2025, 7, 31),
    }

    cursor_invalidas = _FakeCursor([
        (
            ["matricula", "tipo", "data_inicio", "data_fim"],
            [
                ("MATRIC-1", "ferias", date(2025, 7, 1), date(2025, 7, 10)),
                ("MATRIC-2", "ferias", date(2025, 7, 5), None),
                ("MATRIC-3", "afastamento", date(2025, 7, 15), date(2025, 7, 10)),
            ],
        ),
    ])

    with caplog.at_level(logging.WARNING, logger="app.simulacao.bases"):
        resultado_invalidas = _consultar_intercorrencias(_FakeConexao(cursor_invalidas), parametros)

    assert len(resultado_invalidas) == 1
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert (
        caplog.records[0].getMessage()
        == "2 intercorrência(s) de RH ignorada(s): sem data_fim ou data_fim anterior a data_inicio."
    )

    caplog.clear()

    cursor_validas = _FakeCursor([
        (
            ["matricula", "tipo", "data_inicio", "data_fim"],
            [
                ("MATRIC-1", "ferias", date(2025, 7, 1), date(2025, 7, 10)),
                ("MATRIC-2", "afastamento", date(2025, 7, 8), date(2025, 7, 8)),
                ("MATRIC-3", "demissao", date(2025, 7, 15), date(2025, 7, 10)),
                ("MATRIC-4", "cobertura_loja", date(2025, 7, 20), None),
            ],
        ),
    ])

    with caplog.at_level(logging.WARNING, logger="app.simulacao.bases"):
        resultado_validas = _consultar_intercorrencias(_FakeConexao(cursor_validas), parametros)

    assert len(resultado_validas) == 4
    assert caplog.records == []


def test_deslocar_bases_leva_a_referencia_ao_periodo_e_aplica_o_crescimento() -> None:
    # ADR-006: nov/2025 vira nov/2026 com +10% nas vendas; nada mais muda.
    bases = bases_pequenas()

    deslocadas = deslocar_bases(bases, 12, 1.1)

    assert set(deslocadas.rh["competencia"]) == set(deslocadas.vendas["competencia"]) == {"2026-11"}
    assert list(deslocadas.vendas["data_venda"]) == list(bases.vendas["data_venda"] + pd.DateOffset(years=1))
    assert list(deslocadas.rh["data_admissao"].dt.year) == [2021] * 3
    assert list(deslocadas.vendas["vlr_venda"]) == pytest.approx([1100.0, 550.0, 220.0, 880.0])
    assert deslocadas.comissoes.equals(bases.comissoes)
    assert list(bases.vendas["vlr_venda"]) == [1000.0, 500.0, 200.0, 800.0]  # a referência fica intacta


def test_deslocar_bases_mantem_as_intercorrencias_pendentes() -> None:
    # Regressão: campanha futura (ADR-006) perdia o aviso de pendentes da referência (A6-108).
    bases = BasesSimulacao(
        rh=bases_pequenas().rh, vendas=bases_pequenas().vendas, comissoes=bases_pequenas().comissoes,
        intercorrencias_pendentes=2,
    )

    assert deslocar_bases(bases, 12, 1.0).intercorrencias_pendentes == 2


def test_deslocar_bases_usa_o_ultimo_dia_do_mes_mais_curto() -> None:
    bases = bases_pequenas()
    bases.vendas.loc[0, "data_venda"] = pd.Timestamp("2025-01-31")

    deslocadas = deslocar_bases(bases, 1, 1.0)

    assert deslocadas.vendas.loc[0, "data_venda"] == pd.Timestamp("2025-02-28")
