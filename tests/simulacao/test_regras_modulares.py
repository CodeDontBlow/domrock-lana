"""Testes unitários dos submódulos extraídos em app.simulacao.regras."""
from datetime import date
from decimal import Decimal
from fractions import Fraction
import pandas as pd
import pytest

from app.simulacao.regras.afastamento import ajuste_afastamento, coletar_afastamentos, descrever_afastamento
from app.simulacao.regras.aplicador import ajustar_comissao, ajustar_linha_rh, aplicar_ajustes, calcular_ajustes
from app.simulacao.regras.ferias import ajuste_ferias
from app.simulacao.regras.piso import descrever_piso, detalhar_base
from app.simulacao.regras.tipos import (
    PISO_AFASTAMENTO,
    AjusteMatricula,
    EventoIntercorrencia,
    RegraAplicada,
    formatar_moeda,
    formatar_pct,
)
from app.simulacao.regras.validacao import (
    datas_validadas,
    dias_intersecao,
    intercorrencias_vazias,
    para_data,
    validar_e_extrair_eventos,
)
from app.simulacao.regras.vinculo import ajuste_vinculo


def test_tipos_formatacao() -> None:
    assert formatar_pct(1.5) == "1,5%"
    assert formatar_pct(2.0) == "2%"
    assert formatar_moeda(3500.0) == "R$ 3.500,00"
    assert formatar_moeda(Decimal("1234.50")) == "R$ 1.234,50"


def test_validacao_datas() -> None:
    assert para_data("2025-10-01") == date(2025, 10, 1)
    assert para_data(None) is None
    inicio, fim = datas_validadas("M1", "ferias", "2025-10-01", "2025-10-15")
    assert inicio == date(2025, 10, 1)
    assert fim == date(2025, 10, 15)

    with pytest.raises(ValueError, match="data_inicio nula"):
        datas_validadas("M1", "ferias", None, "2025-10-15")

    with pytest.raises(ValueError, match="anterior à data de início"):
        datas_validadas("M1", "ferias", "2025-10-15", "2025-10-01")


def test_intersecao_dias() -> None:
    dias = dias_intersecao(date(2025, 10, 5), date(2025, 10, 10), date(2025, 10, 1), date(2025, 10, 31))
    assert len(dias) == 6
    assert date(2025, 10, 5) in dias
    assert date(2025, 10, 10) in dias


def test_vinculo_regras_5c_5d() -> None:
    fator_adm, regras_adm = ajuste_vinculo(date(2025, 10, 11), None, 2025, 10, 31)
    assert fator_adm == Fraction(20, 31)
    assert any(r.regra == "5c" for r in regras_adm)

    fator_dem, regras_dem = ajuste_vinculo(None, date(2025, 10, 15), 2025, 10, 31)
    assert fator_dem == Fraction(15, 31)
    assert any(r.regra == "5d" for r in regras_dem)


def test_ferias_regra_5g() -> None:
    evento = EventoIntercorrencia("ferias", date(2025, 10, 1), date(2025, 10, 10))
    fator, regras = ajuste_ferias([evento], date(2025, 10, 1), date(2025, 10, 31), 31)
    assert fator == Fraction(21, 31)
    assert len(regras) == 1
    assert regras[0].regra == "5g"


def test_afastamento_regras_5e_5f() -> None:
    # <= 15 dias (5e)
    evt_curto = EventoIntercorrencia("afastamento", date(2025, 10, 1), date(2025, 10, 10))
    fator_e, zera_e, piso_e, regras_e = ajuste_afastamento([evt_curto], date(2025, 10, 1), date(2025, 10, 31), 31)
    assert any(r.regra == "5e" for r in regras_e)
    assert piso_e is True
    assert zera_e is False

    # Mês inteiro afastado (zera e aplica piso)
    evt_longo = EventoIntercorrencia("afastamento", date(2025, 10, 1), date(2025, 10, 31))
    fator_f, zera_f, piso_f, regras_f = ajuste_afastamento([evt_longo], date(2025, 10, 1), date(2025, 10, 31), 31)
    assert any(r.regra == "5f" for r in regras_f)
    assert zera_f is True
    assert piso_f is True


def test_piso_e_detalhar_base() -> None:
    desc_abaixo = descrever_piso(2000.0)
    assert "recebe o fixo de R$ 3.500,00" in desc_abaixo.descricao

    desc_acima = descrever_piso(4000.0)
    assert "recebe a comissão de R$ 4.000,00" in desc_acima.descricao

    linha = pd.Series({"pct_comiss": 1.5, "cod_cargo": "150", "cod_loja": "1"})
    base_gerente = detalhar_base(linha)
    assert len(base_gerente) == 2
    assert base_gerente[0].regra == "5a"
    assert base_gerente[1].regra == "5b"
