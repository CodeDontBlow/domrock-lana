"""Testes das bases da simulação (A6-77)."""
import pandas as pd
import pytest

from app.simulacao.bases import BasesSimulacao, deslocar_bases
from tests.fakes import bases_pequenas


def test_bases_simulacao_sem_intercorrencias_usa_padrao_vazio() -> None:
    bases = bases_pequenas()

    assert bases.intercorrencias.empty
    assert list(bases.intercorrencias.columns) == ["matricula", "tipo", "data_inicio", "data_fim"]
    dicionario = bases.como_dict()
    assert set(dicionario.keys()) == {"rh", "vendas", "comissoes"}
    assert len(dicionario) == 3


def test_bases_simulacao_com_intercorrencias_preserva_dataframe() -> None:
    inter = pd.DataFrame([{"matricula": "M1", "tipo": "ferias", "data_inicio": "2025-11-01", "data_fim": "2025-11-10"}])
    bases = BasesSimulacao(rh=bases_pequenas().rh, vendas=bases_pequenas().vendas, comissoes=bases_pequenas().comissoes, intercorrencias=inter)

    assert len(bases.intercorrencias) == 1
    assert bases.como_dict() == {"rh": bases.rh, "vendas": bases.vendas, "comissoes": bases.comissoes}


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


def test_deslocar_bases_usa_o_ultimo_dia_do_mes_mais_curto() -> None:
    bases = bases_pequenas()
    bases.vendas.loc[0, "data_venda"] = pd.Timestamp("2025-01-31")

    deslocadas = deslocar_bases(bases, 1, 1.0)

    assert deslocadas.vendas.loc[0, "data_venda"] == pd.Timestamp("2025-02-28")
