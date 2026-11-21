"""Simulação da campanha caso as vendas alcancem a meta (A6-93).

Quando a meta é maior que o realizado, escala as vendas do período e recalcula a comissão
de forma determinística para estimar o custo incremental nesse cenário hipotético.
"""
from dataclasses import replace

from app.simulacao.bases import BasesSimulacao
from app.simulacao.dtos import AtingimentoMeta, SimulacaoNaMeta, TotaisSimulacao
from app.simulacao.resumo import mascara_vendas_periodo
from app.tools.regra_tool.dtos import ParametrosSimulacao


def fator_na_meta(meta: AtingimentoMeta) -> float | None:
    """Calcula o fator de escala (meta / realizado) se a meta supera as vendas (A6-93).

    Ex.: fator_na_meta(AtingimentoMeta(meta_vendas=2000.0, vendas_periodo=1000.0, ...)) -> 2.0
    """
    if meta.meta_vendas <= meta.vendas_periodo or meta.vendas_periodo <= 0:
        return None
    # Sem arredondar: com 4 casas, as vendas escaladas ficariam ~R$ 22 longe da meta de R$ 3 mi.
    # Só o DTO arredonda o fator, para exibir.
    return meta.meta_vendas / meta.vendas_periodo


def escalar_vendas(bases: BasesSimulacao, parametros: ParametrosSimulacao, fator: float) -> BasesSimulacao:
    """Devolve novas bases com as vendas do período e marcas da campanha escaladas (A6-93).

    Ex.: escalar_vendas(bases, parametros, 1.25).vendas.loc[mascara, "vlr_venda"]
    """
    vendas_escaladas = bases.vendas.copy()
    mascara = mascara_vendas_periodo(vendas_escaladas, parametros)
    vendas_escaladas.loc[mascara, "vlr_venda"] = (vendas_escaladas.loc[mascara, "vlr_venda"] * fator).round(2)
    return replace(bases, vendas=vendas_escaladas)


def montar_simulacao_na_meta(
    fator: float,
    vendas_escaladas: float,
    totais: TotaisSimulacao,
    orcamento_limite: float | None,
) -> SimulacaoNaMeta:
    """Monta o DTO com os resultados da apuração determinística na meta (A6-93).

    Ex.: montar_simulacao_na_meta(1.25, 2500.0, totais, 20.0).cabe_no_orcamento -> True
    """
    cabe = (totais.diferenca <= orcamento_limite) if orcamento_limite is not None else None
    return SimulacaoNaMeta(
        fator=round(fator, 4),
        vendas_na_meta=round(vendas_escaladas, 2),
        comissao_sem_campanha=totais.baseline,
        comissao_com_campanha=totais.simulado,
        custo_adicional=totais.diferenca,
        cabe_no_orcamento=cabe,
    )
