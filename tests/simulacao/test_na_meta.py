"""Testes da simulação de vendas na meta (A6-93)."""
from app.simulacao.dtos import AtingimentoMeta, TotaisSimulacao
from app.simulacao.na_meta import escalar_vendas, fator_na_meta, montar_simulacao_na_meta
from tests.fakes import bases_pequenas, parametros_black_friday

TOTAIS_DE_EXEMPLO = TotaisSimulacao(baseline=110.0, simulado=136.0, diferenca=26.0, diferenca_pct=23.64)


def _meta(meta_vendas: float, vendas_periodo: float) -> AtingimentoMeta:
    pct = round(vendas_periodo / meta_vendas * 100, 2) if meta_vendas else 0.0
    return AtingimentoMeta(
        meta_vendas=meta_vendas,
        vendas_periodo=vendas_periodo,
        pct_atingimento=pct,
        atingida=vendas_periodo >= meta_vendas,
        diferenca=round(vendas_periodo - meta_vendas, 2),
    )


def test_fator_na_meta_com_meta_acima_calcula_proporcao() -> None:
    # Meta de R$ 2.000,00 com R$ 1.600,00 realizados gera fator 1.25 (A6-93).
    meta = _meta(2000.0, 1600.0)
    assert fator_na_meta(meta) == 1.25

    # Sem arredondar: escalar com 1.4286 erraria a meta; só o DTO mostra 4 casas.
    assert fator_na_meta(_meta(1000.0, 700.0)) == 1000.0 / 700.0
    assert montar_simulacao_na_meta(1000.0 / 700.0, 1000.0, TOTAIS_DE_EXEMPLO, None).fator == 1.4286


def test_fator_na_meta_com_meta_igual_ou_abaixo_devolve_none() -> None:
    # Quando a meta já foi alcançada ou superada, não há cenário na meta a calcular.
    assert fator_na_meta(_meta(1000.0, 1000.0)) is None
    assert fator_na_meta(_meta(1000.0, 1200.0)) is None


def test_fator_na_meta_com_venda_zero_ou_negativa_devolve_none() -> None:
    # Sem vendas no período, divisão por zero é evitada com early return.
    assert fator_na_meta(_meta(1000.0, 0.0)) is None
    assert fator_na_meta(_meta(1000.0, -50.0)) is None


def test_escalar_vendas_afeta_apenas_periodo_e_marcas_sem_mutar_original() -> None:
    # bases_pequenas tem vendas fora do período (01/11), no período (25/11 marca 30 e 26/11 marca 10).
    bases = bases_pequenas()
    parametros = parametros_black_friday(marcas_alvo=["10"])
    fator = 1.5

    escaladas = escalar_vendas(bases, parametros, fator)

    # Apenas a venda de 26/11 da marca 10 (800.0) foi multiplicada por 1.5 -> 1200.0.
    # A venda de 25/11 da marca 30 (500.0) ficou igual por ser de outra marca.
    # As vendas de 01/11 ficaram iguais por estarem fora do período da campanha.
    assert list(escaladas.vendas["vlr_venda"]) == [1000.0, 500.0, 200.0, 1200.0]

    # As bases originais não foram mutadas (imutabilidade exigida pelo A6-93).
    assert list(bases.vendas["vlr_venda"]) == [1000.0, 500.0, 200.0, 800.0]


def test_montar_simulacao_na_meta_com_e_sem_orcamento() -> None:
    totais = TOTAIS_DE_EXEMPLO

    # Sem orçamento informado na ficha.
    na_meta_sem = montar_simulacao_na_meta(2.0, 2600.0, totais, None)
    assert na_meta_sem.fator == 2.0
    assert na_meta_sem.vendas_na_meta == 2600.0
    assert na_meta_sem.comissao_sem_campanha == 110.0
    assert na_meta_sem.comissao_com_campanha == 136.0
    assert na_meta_sem.custo_adicional == 26.0
    assert na_meta_sem.cabe_no_orcamento is None

    # Com orçamento suficiente (26.0 <= 30.0).
    na_meta_cabe = montar_simulacao_na_meta(2.0, 2600.0, totais, 30.0)
    assert na_meta_cabe.cabe_no_orcamento is True

    # Com orçamento estourado (26.0 > 20.0).
    na_meta_estoura = montar_simulacao_na_meta(2.0, 2600.0, totais, 20.0)
    assert na_meta_estoura.cabe_no_orcamento is False
