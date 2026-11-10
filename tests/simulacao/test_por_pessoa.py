"""Testes da montagem da apuração por pessoa (A6-77)."""
from fractions import Fraction

import pandas as pd

from app.simulacao.por_pessoa import montar_apuracao_por_pessoa
from app.simulacao.regras_base import AjusteMatricula, RegraAplicada


def test_montar_apuracao_por_pessoa_ordena_por_matricula_e_competencia() -> None:
    df = pd.DataFrame([
        {
            "matricula": "M2", "competencia": "2025-11", "cod_loja": "2", "cod_marca": "10",
            "cod_cargo": "100", "base_calculo": 800.0, "pct_comiss": 3.0,
            "comissao": 24.0, "comissao_simulada": 32.0,
        },
        {
            "matricula": "M1", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "30",
            "cod_cargo": "100", "base_calculo": 1500.0, "pct_comiss": 2.0,
            "comissao": 30.0, "comissao_simulada": 35.0,
        },
    ])
    resultado = montar_apuracao_por_pessoa(df, {})

    assert [p.matricula for p in resultado] == ["M1", "M2"]
    assert resultado[0].comissao_atual == 30.0
    assert resultado[0].comissao_com_campanha == 35.0
    assert resultado[0].detalhamento[0].regra == "5a"


def test_detalhamento_gerente_inclui_5a_e_5b() -> None:
    df = pd.DataFrame([{
        "matricula": "G1", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "30",
        "cod_cargo": "150", "base_calculo": 1700.0, "pct_comiss": 1.0,
        "comissao": 17.0, "comissao_simulada": 17.0,
    }])
    resultado = montar_apuracao_por_pessoa(df, {})

    regras = [(r.regra, r.descricao) for r in resultado[0].detalhamento]
    assert regras == [
        ("5a", "5a — % da base: 1%"),
        ("5b", "5b — base: venda total da loja 1"),
    ]


def test_detalhamento_com_ajuste_de_admissao_5c() -> None:
    df = pd.DataFrame([{
        "matricula": "M1", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "30",
        "cod_cargo": "100", "base_calculo": 1500.0, "pct_comiss": 2.0,
        "comissao": 20.0, "comissao_simulada": 23.33,
    }])
    ajuste = AjusteMatricula(
        matricula="M1", competencia="2025-11", fator=Fraction(20, 30),
        zera=False, aplica_piso=False,
        regras=(RegraAplicada("5c", "5c — admissão em 10/11: 20 de 30 dias"),),
    )
    resultado = montar_apuracao_por_pessoa(df, {("M1", "2025-11"): ajuste})

    regras = [r.regra for r in resultado[0].detalhamento]
    assert regras == ["5a", "5c"]
    assert resultado[0].detalhamento[1].descricao == "5c — admissão em 10/11: 20 de 30 dias"


def test_detalhamento_com_piso_quando_comissao_fica_abaixo_do_fixo() -> None:
    df = pd.DataFrame([{
        "matricula": "M1", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "30",
        "cod_cargo": "100", "base_calculo": 1500.0, "pct_comiss": 2.0,
        "comissao": 3500.0, "comissao_simulada": 3500.0, "comissao_simulada_bruta": 35.0,
    }])
    ajuste = AjusteMatricula(
        matricula="M1", competencia="2025-11", fator=Fraction(30, 20),
        zera=False, aplica_piso=True,
        regras=(RegraAplicada("5e", "5e — afastamento de 06/11 a 15/11: 10 dias, todos remunerados"),),
    )
    resultado = montar_apuracao_por_pessoa(df, {("M1", "2025-11"): ajuste})

    regras = [r.regra for r in resultado[0].detalhamento]
    assert regras == ["5a", "5e", "piso"]
    piso = resultado[0].detalhamento[2]
    # 35.0 * 1.5 = 52.50
    assert piso.descricao == "piso — recebe o fixo de R$ 3.500,00 (a comissão daria R$ 52,50)"


def test_detalhamento_com_piso_quando_comissao_vence_o_fixo() -> None:
    df = pd.DataFrame([{
        "matricula": "M1", "competencia": "2025-11", "cod_loja": "1", "cod_marca": "30",
        "cod_cargo": "100", "base_calculo": 200000.0, "pct_comiss": 2.0,
        "comissao": 6000.0, "comissao_simulada": 6000.0, "comissao_simulada_bruta": 4000.0,
    }])
    ajuste = AjusteMatricula(
        matricula="M1", competencia="2025-11", fator=Fraction(30, 20),
        zera=False, aplica_piso=True,
        regras=(RegraAplicada("5e", "5e — afastamento de 01/11 a 10/11: 10 dias, todos remunerados"),),
    )
    resultado = montar_apuracao_por_pessoa(df, {("M1", "2025-11"): ajuste})

    piso = next(r for r in resultado[0].detalhamento if r.regra == "piso")
    # 4000.0 * 1.5 = 6000.00
    assert piso.descricao == "piso — recebe a comissão de R$ 6.000,00 (acima do fixo de R$ 3.500,00)"
