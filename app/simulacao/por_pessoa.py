"""Montagem do resultado detalhado por pessoa da simulação (A6-77).

Combina os valores apurados com o detalhamento das regras base (5a/5b),
proporcionais de vínculo (5c/5d), intercorrências (5e a 5g) e piso de afastamento.
"""
from dataclasses import replace

import pandas as pd

from app.simulacao.dtos import ApuracaoPessoa, RegraAplicadaResultado
from app.simulacao.regras_base import (
    AjusteMatricula,
    RegraAplicada,
    ajustar_comissao,
    descrever_piso,
    detalhar_base,
)


def montar_apuracao_por_pessoa(
    comparacao: pd.DataFrame,
    ajustes: dict[tuple[str, str], AjusteMatricula],
) -> list[ApuracaoPessoa]:
    """Monta a apuração detalhada ordenada por matrícula e competência.

    Ex.: montar_apuracao_por_pessoa(comparacao, ajustes)
    """
    ordenada = comparacao.sort_values(["matricula", "competencia"], ignore_index=True)
    return [
        _montar_pessoa(linha, ajustes.get((str(linha["matricula"]), str(linha["competencia"]))))
        for _, linha in ordenada.iterrows()
    ]


def _montar_pessoa(linha: pd.Series, ajuste: AjusteMatricula | None) -> ApuracaoPessoa:
    regras = _regras_da_pessoa(linha, ajuste)
    detalhamento = [RegraAplicadaResultado(regra=r.regra, descricao=r.descricao) for r in regras]
    return ApuracaoPessoa(
        matricula=str(linha["matricula"]),
        competencia=str(linha["competencia"]),
        cod_loja=str(linha["cod_loja"]),
        cod_marca=str(linha["cod_marca"]),
        cod_cargo=str(linha["cod_cargo"]),
        base_calculo=float(linha["base_calculo"]),
        pct_comiss=float(linha["pct_comiss"]),
        detalhamento=detalhamento,
        comissao_atual=float(linha["comissao"]),
        comissao_com_campanha=float(linha["comissao_simulada"]),
    )


def _regras_da_pessoa(linha: pd.Series, ajuste: AjusteMatricula | None) -> list[RegraAplicada]:
    regras = list(detalhar_base(linha))
    if ajuste is None:
        return regras
    regras.extend(ajuste.regras)
    if ajuste.aplica_piso:
        regras.append(_regra_piso(linha, ajuste))
    return regras


def _regra_piso(linha: pd.Series, ajuste: AjusteMatricula) -> RegraAplicada:
    ajuste_sem_piso = replace(ajuste, aplica_piso=False)
    # A bruta vem de service._aplicar_regras_base; reaplicar o fator na já ajustada daria outro valor.
    comissao_sem_piso = ajustar_comissao(float(linha["comissao_simulada_bruta"]), ajuste_sem_piso)
    return descrever_piso(comissao_sem_piso)
