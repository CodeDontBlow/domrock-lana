from fractions import Fraction

import pandas as pd

from app.simulacao.dtos import RegraBaseAplicada
from app.simulacao.regras_aplicadas import contar_pessoas_no_piso, contar_regras_aplicadas
from app.simulacao.regras_base import AjusteMatricula, RegraAplicada


def _ajuste(matricula: str, competencia: str, regras: list[str], fator: Fraction = Fraction(1), piso: bool = False) -> AjusteMatricula:
    return AjusteMatricula(
        matricula=matricula, competencia=competencia, fator=fator, zera=False, aplica_piso=piso,
        regras=tuple(RegraAplicada(regra, f"{regra} — teste") for regra in regras),
    )


def test_conta_matriculas_distintas_por_regra_e_junta_5e_com_5f() -> None:
    ajustes = {
        ("M1", "2025-10"): _ajuste("M1", "2025-10", ["5c"]),
        ("M1", "2025-11"): _ajuste("M1", "2025-11", ["5g"]),
        ("M2", "2025-10"): _ajuste("M2", "2025-10", ["5e"], piso=True),
        ("M3", "2025-10"): _ajuste("M3", "2025-10", ["5f"], piso=True),
        ("M3", "2025-11"): _ajuste("M3", "2025-11", ["5f"], piso=True),
    }

    assert contar_regras_aplicadas(ajustes) == [
        RegraBaseAplicada(regra="5c", descricao="Admissão no mês", pessoas=1),
        RegraBaseAplicada(regra="5e_5f", descricao="Afastamento", pessoas=2),
        RegraBaseAplicada(regra="5g", descricao="Férias", pessoas=1),
    ]


def test_sem_ajustes_a_lista_fica_vazia() -> None:
    assert contar_regras_aplicadas({}) == []


def test_piso_conta_so_quem_ficou_abaixo_do_fixo() -> None:
    # M1: 400 × 1,5 = 600 → fica no piso. M2: 4.000 × 1,5 = 6.000 → a comissão vence. M3 não tem afastamento.
    comparacao = pd.DataFrame({
        "matricula": ["M1", "M2", "M3"], "competencia": ["2025-10"] * 3,
        "comissao_bruta": [400.0, 4000.0, 100.0],
    })
    ajustes = {
        ("M1", "2025-10"): _ajuste("M1", "2025-10", ["5e"], Fraction(3, 2), piso=True),
        ("M2", "2025-10"): _ajuste("M2", "2025-10", ["5e"], Fraction(3, 2), piso=True),
    }

    assert contar_pessoas_no_piso(comparacao, ajustes) == 1
