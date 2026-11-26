from datetime import date

import pytest

from app.tools.regra_tool.referencia import (
    ReferenciaCalculo, completar_referencia, ler_referencia, periodo_futuro, sugerir_referencia,
)

HOJE = date(2026, 11, 20)
BLACK_FRIDAY_2026 = {"data_inicio": "2026-11-24", "data_fim": "2026-11-30"}
INICIO, FIM = date(2026, 11, 24), date(2026, 11, 30)


def test_periodo_futuro_e_o_que_ainda_nao_terminou() -> None:
    assert periodo_futuro(FIM, HOJE)
    assert periodo_futuro(HOJE, HOJE)  # o dia de hoje ainda não está na base
    assert not periodo_futuro(date(2025, 11, 30), HOJE)


def test_sugere_o_mesmo_mes_do_ano_anterior() -> None:
    assert sugerir_referencia(INICIO) == "2025-11"
    assert sugerir_referencia(date(2027, 1, 10)) == "2026-01"


def test_periodo_futuro_sem_referencia_recebe_sugestao_e_crescimento_zero() -> None:
    # Critério 3: Black Friday 2026 sem referência -> a Lana sugere nov/2025 e pede confirmação.
    valores, sugerida = completar_referencia({"periodo": BLACK_FRIDAY_2026}, HOJE)

    assert sugerida == "2025-11"
    assert valores["competencia_referencia"] == "2025-11"
    assert valores["pct_crescimento"] == 0.0


def test_referencia_informada_nao_e_sugerida_de_novo() -> None:
    valores, sugerida = completar_referencia(
        {"periodo": BLACK_FRIDAY_2026, "competencia_referencia": "2025-10", "pct_crescimento": 10.0}, HOJE,
    )

    assert sugerida is None
    assert (valores["competencia_referencia"], valores["pct_crescimento"]) == ("2025-10", 10.0)


def test_periodo_historico_tira_a_referencia_da_ficha() -> None:
    historico = {"data_inicio": "2025-11-24", "data_fim": "2025-11-30"}

    valores, sugerida = completar_referencia(
        {"periodo": historico, "competencia_referencia": "2024-11", "pct_crescimento": 5.0}, HOJE,
    )

    assert sugerida is None
    assert valores["competencia_referencia"] is None and valores["pct_crescimento"] is None


def test_periodo_incompleto_nao_sugere_nada() -> None:
    valores = {"periodo": {"data_inicio": "2026-11-24", "data_fim": None}}

    assert completar_referencia(valores, HOJE) == (valores, None)


def test_ler_referencia_desloca_doze_meses_e_aplica_o_crescimento() -> None:
    referencia, erros = ler_referencia(
        {"competencia_referencia": "2025-11", "pct_crescimento": 10}, INICIO, FIM, HOJE,
    )

    assert erros == []
    assert referencia == ReferenciaCalculo("2025-11", 10.0, 12)
    assert referencia.fator == pytest.approx(1.1)
    assert referencia.competencias_lidas(["2026-11", "2026-12"]) == ["2025-11", "2025-12"]
    assert referencia.descrever() == "Calculado sobre nov/2025 (referência), crescimento de 10%."


def test_ler_referencia_sem_crescimento_vale_zero() -> None:
    referencia, _ = ler_referencia({"competencia_referencia": "2025-11"}, INICIO, FIM, HOJE)

    assert referencia.pct_crescimento == 0.0
    assert referencia.descrever() == "Calculado sobre nov/2025 (referência), crescimento de 0%."


def test_ler_referencia_ignora_os_campos_no_periodo_historico() -> None:
    assert ler_referencia({"competencia_referencia": "lixo"}, date(2025, 11, 24), date(2025, 11, 30), HOJE) == (None, [])


@pytest.mark.parametrize(("valores", "trecho"), [
    ({}, "obrigatória para período futuro (sugestão: 2025-11)"),
    ({"competencia_referencia": "nov/2025"}, "esperado mês em YYYY-MM"),
    ({"competencia_referencia": "2025-11", "pct_crescimento": -5}, "de 0 a 100"),
    ({"competencia_referencia": "2025-11", "pct_crescimento": "dez"}, "esperado número"),
    ({"competencia_referencia": "2026-11"}, "ainda não tem histórico completo"),
])
def test_ler_referencia_recusa_valor_invalido(valores: dict[str, object], trecho: str) -> None:
    referencia, erros = ler_referencia(valores, INICIO, FIM, HOJE)

    assert referencia is None
    assert any(trecho in erro for erro in erros), erros
