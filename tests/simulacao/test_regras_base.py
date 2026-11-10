"""Testes unitários das regras base 5c a 5g da apuração de comissões (A6-77)."""
from fractions import Fraction
import pandas as pd
import pytest

from app.simulacao.regras_base import (
    RegraAplicada,
    ajustar_comissao,
    aplicar_ajustes,
    calcular_ajustes,
    descrever_piso,
    detalhar_base,
    intercorrencias_vazias,
)


def test_5c_admissao_no_mes_da_competencia() -> None:
    rh = pd.DataFrame([{
        "matricula": "M1", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2025-10-10", "data_demissao": None,
    }])
    ajustes = calcular_ajustes(rh, intercorrencias_vazias())
    ajuste = ajustes[("M1", "2025-10")]
    assert ajuste.fator == Fraction(21, 31)
    assert ajuste.regras == (RegraAplicada("5c", "5c — admissão em 10/10: 21 de 31 dias"),)
    assert ajustar_comissao(3100.0, ajuste) == 2100.0


def test_5d_demissao_no_mes_da_competencia() -> None:
    rh = pd.DataFrame([{
        "matricula": "M2", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": "2025-11-10",
    }])
    ajustes = calcular_ajustes(rh, intercorrencias_vazias())
    ajuste = ajustes[("M2", "2025-11")]
    assert ajuste.fator == Fraction(10, 30)
    assert ajuste.regras == (RegraAplicada("5d", "5d — demissão em 10/11: 10 de 30 dias"),)
    assert ajustar_comissao(3000.0, ajuste) == 1000.0


def test_5c_e_5d_no_mesmo_mes() -> None:
    rh = pd.DataFrame([{
        "matricula": "M3", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2025-10-05", "data_demissao": "2025-10-20",
    }])
    ajustes = calcular_ajustes(rh, intercorrencias_vazias())
    ajuste = ajustes[("M3", "2025-10")]
    assert ajuste.fator == Fraction(15, 31)
    assert ajuste.regras == (
        RegraAplicada("5c", "5c — admissão em 05/10: 15 de 31 dias"),
        RegraAplicada("5d", "5d — demissão em 20/10: 15 de 31 dias"),
    )

    rh_invalido = pd.DataFrame([{
        "matricula": "M3_INV", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2025-10-20", "data_demissao": "2025-10-05",
    }])
    with pytest.raises(ValueError, match="2025-10-05.*2025-10-20"):
        calcular_ajustes(rh_invalido, intercorrencias_vazias())


def test_5e_afastamento_ate_15_dias_piso_vence() -> None:
    rh = pd.DataFrame([{
        "matricula": "M4", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M4", "tipo": "afastamento",
        "data_inicio": pd.to_datetime("2025-11-06"), "data_fim": pd.to_datetime("2025-11-15"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("M4", "2025-11")]
    assert ajuste.fator == Fraction(30, 20)
    assert ajuste.aplica_piso is True
    assert ajuste.regras == (RegraAplicada("5e", "5e — afastamento de 06/11 a 15/11: 10 dias, todos remunerados"),)

    assert ajustar_comissao(400.0, ajuste) == 3500.0

    piso_desc = descrever_piso(600.0)
    assert piso_desc.descricao == "piso — recebe o fixo de R$ 3.500,00 (a comissão daria R$ 600,00)"


def test_5e_comissao_vence_piso() -> None:
    rh = pd.DataFrame([{
        "matricula": "M5", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M5", "tipo": "afastamento",
        "data_inicio": pd.to_datetime("2025-11-01"), "data_fim": pd.to_datetime("2025-11-10"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("M5", "2025-11")]
    assert ajuste.fator == Fraction(30, 20)
    assert ajustar_comissao(4000.0, ajuste) == 6000.0

    piso_desc = descrever_piso(6000.0)
    assert piso_desc.descricao == "piso — recebe a comissão de R$ 6.000,00 (acima do fixo de R$ 3.500,00)"


def test_5f_afastamento_mais_de_15_dias() -> None:
    rh = pd.DataFrame([{
        "matricula": "M6", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M6", "tipo": "afastamento",
        "data_inicio": pd.to_datetime("2025-11-01"), "data_fim": pd.to_datetime("2025-11-20"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("M6", "2025-11")]
    assert ajuste.fator == Fraction(25, 10)
    assert ajuste.regras == (RegraAplicada("5f", "5f — afastamento de 01/11 a 20/11: 20 dias, 15 remunerados"),)
    comissao_inicial = 8000.0 * 0.025
    assert comissao_inicial * 2.5 == 500.0
    assert ajustar_comissao(comissao_inicial, ajuste) == 3500.0


def test_afastamento_atravessa_meses() -> None:
    rh = pd.DataFrame([
        {"matricula": "M7", "competencia": "2025-08", "cod_loja": "1", "cod_marca": "10",
         "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None},
        {"matricula": "M7", "competencia": "2025-09", "cod_loja": "1", "cod_marca": "10",
         "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None},
    ])
    inter = pd.DataFrame([{
        "matricula": "M7", "tipo": "afastamento",
        "data_inicio": pd.to_datetime("2025-08-18"), "data_fim": pd.to_datetime("2025-09-08"),
    }])
    ajustes = calcular_ajustes(rh, inter)

    ajuste_ago = ajustes[("M7", "2025-08")]
    assert ajuste_ago.fator == Fraction(31, 17)
    assert ajuste_ago.regras == (RegraAplicada("5f", "5f — afastamento de 18/08 a 08/09: 14 dias, todos remunerados"),)

    ajuste_set = ajustes[("M7", "2025-09")]
    assert ajuste_set.fator == Fraction(23, 22)
    assert ajuste_set.regras == (RegraAplicada("5f", "5f — afastamento de 18/08 a 08/09: 8 dias, 1 remunerado"),)


def test_afastamento_mes_inteiro() -> None:
    rh = pd.DataFrame([{
        "matricula": "M8", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M8", "tipo": "afastamento",
        "data_inicio": pd.to_datetime("2025-11-01"), "data_fim": pd.to_datetime("2025-11-30"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("M8", "2025-11")]
    assert ajuste.zera is True
    assert ajuste.aplica_piso is True
    assert ajustar_comissao(1000.0, ajuste) == 3500.0


def test_licenca_maternidade_segue_afastamento() -> None:
    rh = pd.DataFrame([{
        "matricula": "M9", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M9", "tipo": "licenca_maternidade",
        "data_inicio": pd.to_datetime("2025-11-06"), "data_fim": pd.to_datetime("2025-11-15"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("M9", "2025-11")]
    assert ajuste.fator == Fraction(30, 20)
    assert ajuste.regras == (RegraAplicada("5e", "5e — afastamento de 06/11 a 15/11: 10 dias, todos remunerados"),)


def test_5g_ferias() -> None:
    rh = pd.DataFrame([{
        "matricula": "M10", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M10", "tipo": "ferias",
        "data_inicio": pd.to_datetime("2025-10-01"), "data_fim": pd.to_datetime("2025-10-10"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("M10", "2025-10")]
    assert ajuste.fator == Fraction(21, 31)
    assert ajuste.regras == (RegraAplicada("5g", "5g — férias de 01/10 a 10/10: 10 dias sem remuneração"),)


def test_intercorrencia_demissao_substitui_rh() -> None:
    rh = pd.DataFrame([{
        "matricula": "M11", "competencia": "2025-09", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M11", "tipo": "demissao",
        "data_inicio": pd.to_datetime("2025-09-15"), "data_fim": pd.NaT,
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("M11", "2025-09")]
    assert ajuste.fator == Fraction(15, 30)
    assert ajuste.regras == (RegraAplicada("5d", "5d — demissão em 15/09: 15 de 30 dias"),)


def test_cobertura_loja_e_ignorada() -> None:
    rh = pd.DataFrame([{
        "matricula": "M12", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M12", "tipo": "cobertura_loja",
        "data_inicio": pd.to_datetime("2025-10-01"), "data_fim": pd.to_datetime("2025-10-10"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    assert ("M12", "2025-10") not in ajustes


def test_gerente_proporcao_sobre_comissao() -> None:
    rh = pd.DataFrame([{
        "matricula": "G13", "competencia": "2025-11", "cod_loja": "5", "cod_marca": "10",
        "cod_cargo": "150", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "G13", "tipo": "afastamento",
        "data_inicio": pd.to_datetime("2025-11-06"), "data_fim": pd.to_datetime("2025-11-15"),
    }])
    ajustes = calcular_ajustes(rh, inter)
    ajuste = ajustes[("G13", "2025-11")]
    assert ajuste.fator == Fraction(30, 20)
    assert ajustar_comissao(4000.0, ajuste) == 6000.0


def test_sem_regras_nao_entra_no_dict_e_mantem_comissao() -> None:
    rh = pd.DataFrame([{
        "matricula": "M14", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    ajustes = calcular_ajustes(rh, intercorrencias_vazias())
    assert ("M14", "2025-10") not in ajustes

    apuracao = pd.DataFrame([{
        "matricula": "M14", "competencia": "2025-10", "comissao": 1500.0,
    }])
    resultado = aplicar_ajustes(apuracao, ajustes, ["comissao"])
    assert resultado.loc[0, "comissao"] == 1500.0


def test_aplicar_ajustes_duas_colunas() -> None:
    rh = pd.DataFrame([{
        "matricula": "M15", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2025-10-10", "data_demissao": None,
    }])
    ajustes = calcular_ajustes(rh, intercorrencias_vazias())
    apuracao = pd.DataFrame([{
        "matricula": "M15", "competencia": "2025-10",
        "comissao": 3100.0, "comissao_simulada": 6200.0,
    }])
    resultado = aplicar_ajustes(apuracao, ajustes, ["comissao", "comissao_simulada"])
    assert resultado.loc[0, "comissao"] == 2100.0
    assert resultado.loc[0, "comissao_simulada"] == 4200.0


def test_detalhar_base() -> None:
    linha_vendedor_1 = pd.Series({"cod_cargo": "100", "cod_loja": "1", "pct_comiss": 2.0})
    regras_v1 = detalhar_base(linha_vendedor_1)
    assert len(regras_v1) == 1
    assert regras_v1[0] == RegraAplicada("5a", "5a — % da base: 2%")

    linha_vendedor_2 = pd.Series({"cod_cargo": "100", "cod_loja": "1", "pct_comiss": 0.5})
    regras_v2 = detalhar_base(linha_vendedor_2)
    assert len(regras_v2) == 1
    assert regras_v2[0] == RegraAplicada("5a", "5a — % da base: 0,5%")

    linha_gerente = pd.Series({"cod_cargo": "150", "cod_loja": "5", "pct_comiss": 1.0})
    regras_gerente = detalhar_base(linha_gerente)
    assert len(regras_gerente) == 2
    assert regras_gerente[0] == RegraAplicada("5a", "5a — % da base: 1%")
    assert regras_gerente[1] == RegraAplicada("5b", "5b — base: venda total da loja 5")


def test_intercorrencia_data_fim_invalida_lanca_erro() -> None:
    rh = pd.DataFrame([{
        "matricula": "M17", "competencia": "2025-10", "cod_loja": "1", "cod_marca": "10",
        "cod_cargo": "100", "data_admissao": "2020-01-01", "data_demissao": None,
    }])
    inter = pd.DataFrame([{
        "matricula": "M17", "tipo": "afastamento",
        "data_inicio": pd.to_datetime("2025-10-15"), "data_fim": pd.to_datetime("2025-10-10"),
    }])
    with pytest.raises(ValueError, match="2025-10-10.*2025-10-15"):
        calcular_ajustes(rh, inter)


def test_intercorrencias_vazias_estrutura() -> None:
    df = intercorrencias_vazias()
    assert list(df.columns) == ["matricula", "tipo", "data_inicio", "data_fim"]
    assert df.empty
    assert pd.api.types.is_datetime64_any_dtype(df["data_inicio"])
    assert pd.api.types.is_datetime64_any_dtype(df["data_fim"])
