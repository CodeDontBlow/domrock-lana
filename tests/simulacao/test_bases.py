"""Testes das bases da simulação (A6-77)."""
import pandas as pd

from app.simulacao.bases import BasesSimulacao
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
