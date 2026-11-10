"""Contagens das regras 5c a 5g na comissão atual: `regras_base_aplicadas` e `pessoas_no_piso` (contrato 2.3, A6-77).

As regras 5a e 5b valem para todos e não entram na contagem.
"""
from dataclasses import replace

import pandas as pd

from app.simulacao.dtos import RegraBaseAplicada
from app.simulacao.regras_base import PISO_AFASTAMENTO, AjusteMatricula, ajustar_comissao

# Código e descrição do contrato 2.3: 5e e 5f contam juntas como afastamento.
GRUPO_DA_REGRA = {
    "5c": ("5c", "Admissão no mês"),
    "5d": ("5d", "Demissão no mês"),
    "5e": ("5e_5f", "Afastamento"),
    "5f": ("5e_5f", "Afastamento"),
    "5g": ("5g", "Férias"),
}


def contar_regras_aplicadas(ajustes: dict[tuple[str, str], AjusteMatricula]) -> list[RegraBaseAplicada]:
    """Pessoas (matrículas distintas) por regra, só as regras com alguém.

    Ex.: contar_regras_aplicadas(ajustes) -> [RegraBaseAplicada(regra="5c", descricao="Admissão no mês", pessoas=15)]
    """
    matriculas: dict[tuple[str, str], set[str]] = {}
    for (matricula, _), ajuste in ajustes.items():
        for regra in ajuste.regras:
            matriculas.setdefault(GRUPO_DA_REGRA[regra.regra], set()).add(matricula)
    return [
        RegraBaseAplicada(regra=codigo, descricao=descricao, pessoas=len(pessoas))
        for (codigo, descricao), pessoas in sorted(matriculas.items())
    ]


def contar_pessoas_no_piso(comparacao: pd.DataFrame, ajustes: dict[tuple[str, str], AjusteMatricula]) -> int:
    """Matrículas cuja comissão atual ficou no fixo de R$ 3.500. Ex.: contar_pessoas_no_piso(comparacao, ajustes) -> 3

    `comparacao` precisa da coluna `comissao_bruta` (antes dos ajustes), gravada por service._aplicar_regras_base.
    """
    linhas = zip(comparacao["matricula"], comparacao["competencia"], comparacao["comissao_bruta"])
    no_piso = {str(m) for m, c, bruta in linhas if _piso_venceu(float(bruta), ajustes.get((str(m), str(c))))}
    return len(no_piso)


def _piso_venceu(comissao_bruta: float, ajuste: AjusteMatricula | None) -> bool:
    if ajuste is None or not ajuste.aplica_piso:
        return False
    return ajustar_comissao(comissao_bruta, replace(ajuste, aplica_piso=False)) < PISO_AFASTAMENTO
