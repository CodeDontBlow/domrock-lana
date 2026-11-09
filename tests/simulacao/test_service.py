import pytest

from app.simulacao.bases import BasesSimulacao
from app.simulacao.dtos import ResultadoSimulacao
from app.simulacao.service import SimulacaoFalhouError, SimuladorCampanha
from app.tools.code_tool.gerador import GeradorCodigoModelo
from app.tools.code_tool.runner import SubprocessRunner
from app.tools.regra_tool.parametros import RegraInvalidaError, montar_regra
from tests.fakes import (
    FakeExplicador, FakeFonteBases, FakeGeradorLlmIndisponivel, FakeGeradorSequencial,
    bases_com_admissao_no_mes, bases_com_afastamento_piso, bases_pequenas, fonte_modelo,
    parametros_black_friday,
)

VALORES = {
    "periodo": {"data_inicio": "2025-11-24", "data_fim": "2025-11-30"},
    "pct_acrescimo": 1.0, "marcas_alvo": ["10", "30"], "cargos_alvo": ["100", "200", "300"],
    "meta_vendas": 1000.0, "orcamento_limite": 20.0,
}
CODIGO_QUEBRADO = "def aplicar_regra(bases, apuracao_base, competencias):\n    raise ValueError('bug')\n"


def _simulador(
    gerador: FakeGeradorSequencial | FakeGeradorLlmIndisponivel,
    bases: BasesSimulacao | None = None,
) -> SimuladorCampanha:
    return SimuladorCampanha(FakeFonteBases(bases or bases_pequenas()), gerador, SubprocessRunner(), FakeExplicador())


def _conferir_soma_por_pessoa(resultado: ResultadoSimulacao) -> None:
    """A tela "Quanto cada pessoa recebe" (A6-109) precisa somar o mesmo que os totais."""
    atual = sum(p.comissao_atual for p in resultado.apuracao_por_pessoa)
    com_campanha = sum(p.comissao_com_campanha for p in resultado.apuracao_por_pessoa)
    assert atual == pytest.approx(resultado.totais.baseline, abs=0.01)
    assert com_campanha == pytest.approx(resultado.totais.simulado, abs=0.01)


def test_simular_black_friday_calcula_totais_orcamento_e_meta() -> None:
    gerador = FakeGeradorSequencial([fonte_modelo(parametros_black_friday())])

    resultado = _simulador(gerador).simular(montar_regra(VALORES, "bf", "draft-1"))

    # Janela 24–30/11: M1 vendeu 500 (+5,00) e M2 800 (+8,00); G1 (gerente) fora.
    assert resultado.totais.diferenca == 13.0
    assert resultado.orcamento.cabe_no_orcamento and resultado.orcamento.folga == 7.0
    assert resultado.meta.vendas_periodo == 1300.0 and resultado.meta.atingida
    assert resultado.tentativas == 1 and resultado.explicacao == "explicação fake"
    assert resultado.impacto.pessoas_impactadas == 2 and resultado.maiores_lojas[0].codigo == "2"
    assert resultado.ressalvas
    _conferir_soma_por_pessoa(resultado)


def test_simular_com_admissao_no_mes_aplica_proporcao_e_detalha_5c() -> None:
    gerador = FakeGeradorSequencial([fonte_modelo(parametros_black_friday())])
    simulador = _simulador(gerador, bases=bases_com_admissao_no_mes())

    resultado = simulador.simular(montar_regra(VALORES, "bf", "draft-1"))

    # M1 admitido em 10/11 (20/30): base 30 * 2/3 = 20.0, simulado 35 * 2/3 = 23.33;
    # G1: 17.0 nos dois; M2: 24.0 e 32.0. Totais: base 61.0, simulado 72.33, dif 11.33.
    assert resultado.totais.baseline == 61.0
    assert resultado.totais.simulado == 72.33
    assert resultado.totais.diferenca == 11.33

    _conferir_soma_por_pessoa(resultado)

    pessoa_m1 = next(p for p in resultado.apuracao_por_pessoa if p.matricula == "M1")
    assert pessoa_m1.comissao_atual == 20.0
    assert pessoa_m1.comissao_com_campanha == 23.33
    assert any("5c — admissão em 10/11: 20 de 30 dias" in r.descricao for r in pessoa_m1.detalhamento)
    # A trilha somava o baseline bruto (só 5a/5b) e divergia dos totais.
    passo = next(p for p in resultado.trilha.passos if p.ferramenta == "comissao_atual")
    assert "R$ 61,00" in passo.descricao


def test_simular_com_afastamento_leva_ao_piso_com_diferenca_zero() -> None:
    gerador = FakeGeradorSequencial([fonte_modelo(parametros_black_friday())])
    simulador = _simulador(gerador, bases=bases_com_afastamento_piso())

    resultado = simulador.simular(montar_regra(VALORES, "bf", "draft-1"))

    # M1 tem afastamento 5e (fator 1.5): base 30 * 1.5 = 45 -> piso 3500;
    # simulado 35 * 1.5 = 52.5 -> piso 3500; diferença de M1 é zero.
    pessoa_m1 = next(p for p in resultado.apuracao_por_pessoa if p.matricula == "M1")
    assert pessoa_m1.comissao_atual == 3500.0
    assert pessoa_m1.comissao_com_campanha == 3500.0
    assert (pessoa_m1.comissao_com_campanha - pessoa_m1.comissao_atual) == 0.0

    piso = next(r for r in pessoa_m1.detalhamento if r.regra == "piso")
    assert piso.descricao == "piso — recebe o fixo de R$ 3.500,00 (a comissão daria R$ 52,50)"

    _conferir_soma_por_pessoa(resultado)


def test_simular_sem_orcamento_traz_meta_retorno_e_nenhum_veredito() -> None:
    gerador = FakeGeradorSequencial([fonte_modelo(parametros_black_friday())])
    regra = montar_regra({**VALORES, "orcamento_limite": None}, "bf", "draft-1")

    resultado = _simulador(gerador).simular(regra)

    # Custo 13,00 sobre a venda de 1.300,00 (300,00 acima da meta de 1.000,00).
    assert resultado.orcamento is None and resultado.meta.diferenca == 300.0
    assert resultado.retorno.custo_pct_venda == 1.0 and resultado.retorno.custo_por_real_acima_meta == 0.04
    assert all(c.tipo != "ajustar_acrescimo" for c in resultado.cenarios)


def test_simular_propoe_percentual_que_cabe_simulado_de_novo() -> None:
    gerador = FakeGeradorSequencial([fonte_modelo(parametros_black_friday())])
    regra = montar_regra({**VALORES, "orcamento_limite": 10.0}, "bf", "draft-1")

    resultado = _simulador(gerador).simular(regra)

    # +1% custa 13,00; com 10,00 cabe 0,76% (M1 500 * 0,76% = 3,80 e M2 800 * 0,76% = 6,08).
    percentual = next(c for c in resultado.cenarios if c.tipo == "ajustar_acrescimo")
    assert percentual.pct_acrescimo == 0.76 and percentual.custo_incremental == 9.88
    assert percentual.cabe_no_orcamento


def test_simular_tenta_de_novo_com_o_erro_da_primeira_tentativa() -> None:
    gerador = FakeGeradorSequencial([CODIGO_QUEBRADO, fonte_modelo(parametros_black_friday())])

    resultado = _simulador(gerador).simular(montar_regra(VALORES, "bf", "draft-1"))

    assert resultado.tentativas == 2
    assert gerador.erros_recebidos[0] is None
    assert "ValueError: bug" in (gerador.erros_recebidos[1] or "")


def test_simular_falha_sem_resultado_parcial_quando_as_tentativas_acabam() -> None:
    gerador = FakeGeradorSequencial([CODIGO_QUEBRADO])

    with pytest.raises(SimulacaoFalhouError) as erro:
        _simulador(gerador).simular(montar_regra(VALORES, "bf", "draft-1"))

    assert erro.value.etapa == "geracao_codigo" and erro.value.codigo == CODIGO_QUEBRADO


def test_simular_recusa_regra_incompleta_antes_de_gerar_codigo() -> None:
    gerador = FakeGeradorSequencial([CODIGO_QUEBRADO])

    with pytest.raises(RegraInvalidaError):
        _simulador(gerador).simular(montar_regra({**VALORES, "meta_vendas": None}, "bf", "d"))

    assert gerador.erros_recebidos == []


def test_simular_recusa_competencia_sem_dados() -> None:
    periodo_sem_dados = {"data_inicio": "2025-12-01", "data_fim": "2025-12-31"}

    with pytest.raises(SimulacaoFalhouError, match="2025-12"):
        _simulador(FakeGeradorSequencial([CODIGO_QUEBRADO])).simular(
            montar_regra({**VALORES, "periodo": periodo_sem_dados}, "dez", "d")
        )


def test_simular_tenta_de_novo_quando_a_llm_falha() -> None:
    gerador = FakeGeradorLlmIndisponivel(fonte_modelo(parametros_black_friday()))

    resultado = _simulador(gerador).simular(montar_regra(VALORES, "bf", "draft-1"))

    assert resultado.tentativas == 2


def test_simular_trata_comissao_em_texto_como_tentativa_falha() -> None:
    comissao_texto = fonte_modelo(parametros_black_friday()).replace(
        '    return {"apuracao_simulada"', '    simulada["comissao"] = simulada["comissao"].astype(str)\n    return {"apuracao_simulada"'
    )

    with pytest.raises(SimulacaoFalhouError) as erro:
        _simulador(FakeGeradorSequencial([comissao_texto])).simular(montar_regra(VALORES, "bf", "d"))

    assert erro.value.etapa == "geracao_codigo"


# Gerente sobre a própria venda em vez da venda da loja: passa nas asserções de escopo,
# mas diverge do cálculo determinístico (caso real visto na LLM em 2026-09-26).
GERENTE_SOBRE_PROPRIA_VENDA = """import pandas as pd

def aplicar_regra(bases, apuracao_base, competencias):
    simulada = apuracao_base.copy()
    vendas = bases["vendas"]
    janela = vendas[(vendas["data_venda"] >= pd.Timestamp("2025-11-24")) & (vendas["cod_cargo"] == "150")]
    propria = janela.groupby("matricula")["vlr_venda"].sum()
    delta = simulada["matricula"].map(propria).fillna(0.0).mul(0.01).round(2)
    simulada["comissao"] = (simulada["comissao"] + delta).round(2)
    contrib = simulada[["matricula", "competencia"]].copy()
    contrib["elemento_ref"] = "pct_acrescimo"
    contrib["delta"] = delta
    return {"apuracao_simulada": simulada, "contribuicoes": contrib[contrib["delta"] != 0]}
"""
VALORES_GERENTE = {**VALORES, "cargos_alvo": ["150"]}


def _simulador_conferido(gerador: FakeGeradorSequencial) -> SimuladorCampanha:
    return SimuladorCampanha(
        FakeFonteBases(bases_pequenas()), gerador, SubprocessRunner(), FakeExplicador(),
        referencia=GeradorCodigoModelo(),
    )


def test_simular_conferido_aceita_codigo_da_ia_que_bate_com_a_referencia() -> None:
    fonte = fonte_modelo(parametros_black_friday(cargos_alvo=["150"]))

    resultado = _simulador_conferido(FakeGeradorSequencial([fonte])).simular(montar_regra(VALORES_GERENTE, "g", "d"))

    assert resultado.totais.diferenca == 5.0  # G1: 500 da loja 1 na janela * 1%
    assert resultado.origem_codigo == "fake" and "conferido" in resultado.observacao


def test_simular_conferido_devolve_a_divergencia_para_a_ia_e_usa_a_referencia_no_fim() -> None:
    gerador = FakeGeradorSequencial([GERENTE_SOBRE_PROPRIA_VENDA])

    resultado = _simulador_conferido(gerador).simular(montar_regra(VALORES_GERENTE, "g", "d"))

    assert "venda TOTAL da loja" in (gerador.erros_recebidos[1] or "")
    assert resultado.totais.diferenca == 5.0
    assert resultado.origem_codigo == "modelo" and "divergiu" in resultado.observacao


def test_simular_monta_a_trilha_com_os_6_passos_do_contrato() -> None:
    gerador = FakeGeradorSequencial([fonte_modelo(parametros_black_friday())])

    trilha = _simulador(gerador).simular(montar_regra(VALORES, "bf", "draft-1")).trilha

    assert [(p.ordem, p.ferramenta) for p in trilha.passos] == [
        (1, "carregar_bases"), (2, "comissao_atual"), (3, "gerar_codigo"),
        (4, "executar_sandbox"), (5, "conferir"), (6, "resumir"),
    ]
    assert all(p.situacao == "SUCESSO" and p.tempo_ms >= 0 for p in trilha.passos)
    assert trilha.tentativas == 1 and "Gerentes (150) excluídos" in trilha.premissas
    assert trilha.passos[5].descricao == "Custo adicional de R$ 13,00"


def test_trilha_conta_as_vendas_do_periodo_e_nao_do_mes_inteiro() -> None:
    # Regressão A6-70: contava as 4 vendas de nov; na janela 24–30/11 são 2 (M1 em 25/11, M2 em 26/11).
    gerador = FakeGeradorSequencial([fonte_modelo(parametros_black_friday())])

    carga = _simulador(gerador).simular(montar_regra(VALORES, "bf", "draft-1")).trilha.passos[0]

    assert carga.descricao == "Bases de nov/2025: 3 pessoas no RH, 2 vendas de 24/11 a 30/11, 8 linhas de % por marca e cargo"
    assert "venda" in carga.tabelas_acessadas and carga.competencias == ["2025-11"]
    assert carga.sql_executado and "FROM venda v" in carga.sql_executado


def test_trilha_diz_quando_o_codigo_foi_conferido_com_a_referencia() -> None:
    fonte = fonte_modelo(parametros_black_friday(cargos_alvo=["150"]))

    trilha = _simulador_conferido(FakeGeradorSequencial([fonte])).simular(montar_regra(VALORES_GERENTE, "g", "d")).trilha

    assert trilha.passos[2].descricao.endswith("em 1 tentativa, conferido com o cálculo de referência")
    assert trilha.passos[4].descricao.startswith("6 conferências passaram:")
    assert trilha.passos[4].descricao.endswith("cálculo de referência")


def test_trilha_diz_quando_valeu_o_calculo_de_referencia() -> None:
    gerador = FakeGeradorSequencial([GERENTE_SOBRE_PROPRIA_VENDA])

    trilha = _simulador_conferido(gerador).simular(montar_regra(VALORES_GERENTE, "g", "d")).trilha

    assert "divergiu do cálculo de referência em 2 tentativas" in trilha.passos[2].descricao
    assert trilha.passos[4].descricao.startswith("5 conferências passaram:")

