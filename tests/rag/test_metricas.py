"""Testes unitários para métricas, calibração e datasets do guardrail (A6-128)."""

import json
from pathlib import Path
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.rag.avaliacao.metricas import (
    LinhaLimiar,
    Metricas,
    PerguntaRotulada,
    calcular_metricas,
    escolher_limiar,
    varrer_limiares,
)
from app.rag.avaliacao.relatorio import (
    LinhaDesempenhoTipo,
    LinhaErro,
    calcular_desempenho_por_tipo,
    calcular_estatisticas_latencia,
    converter_historico,
    formatar_estatisticas_latencia,
    formatar_tabela_erros,
    formatar_tabela_limiares,
    formatar_tabela_por_tipo,
    formatar_tabela_teste,
)


def test_metricas_de_uma_matriz_conhecida():
    """Valida cálculo de VP, FP, VN, FN, precisão, recall e F1 (A6-128)."""
    m = calcular_metricas([True, True, False, False], [True, False, False, False])
    assert (m.vp, m.fn, m.vn, m.fp) == (1, 1, 2, 0)
    assert m.precisao == 1.0 and m.recall == 0.5 and round(m.f1, 4) == 0.6667
    assert m.acuracia == 0.75


def test_metricas_sem_positivos_nao_divide_por_zero():
    """Garante que zero divisões retornam 0.0 nas taxas (A6-128)."""
    m = calcular_metricas([False, False], [False, False])
    assert (m.vp, m.fp, m.vn, m.fn) == (0, 0, 2, 0)
    assert m.acuracia == 1.0
    assert m.precisao == 0.0
    assert m.recall == 0.0
    assert m.f1 == 0.0


def test_calcular_metricas_tamanhos_diferentes_levanta_erro():
    """Valida que listas de tamanhos incompatíveis disparam ValueError (A6-128)."""
    with pytest.raises(ValueError, match="Tamanhos incompatíveis: 2 != 1"):
        calcular_metricas([True, False], [True])


def test_limiar_zero_bloqueia_tudo():
    """Limiar <= 0.0 com distâncias positivas barra todas as mensagens (A6-128)."""
    perguntas = [
        PerguntaRotulada(pergunta="P1", esperado="dentro", tipo="regra"),
        PerguntaRotulada(pergunta="P2", esperado="fora", tipo="neutra"),
        PerguntaRotulada(pergunta="P3", esperado="fora", tipo="injecao"),
    ]
    distancias = [0.2, 0.6, 0.9]
    linhas = varrer_limiares(perguntas, distancias, [0.0])

    assert len(linhas) == 1
    linha = linhas[0]
    assert linha.limiar == 0.0
    assert linha.metricas.vp == 0
    assert linha.metricas.fp == 0
    assert linha.metricas.vn == 2
    assert linha.metricas.fn == 1
    assert linha.injecoes_bloqueadas == 1


def test_escolher_limiar_desempata_por_injecoes_e_depois_menor_limiar():
    """Valida critério de desempate: F1 -> injeções -> menor limiar (A6-128)."""
    metricas_base = Metricas(
        vp=10, fp=1, vn=10, fn=1,
        acuracia=0.9, precisao=0.9, recall=0.9, f1=0.9,
    )
    metricas_menor_f1 = Metricas(
        vp=8, fp=2, vn=8, fn=2,
        acuracia=0.8, precisao=0.8, recall=0.8, f1=0.8,
    )

    # Caso 1: F1 maior vence
    linhas1 = [
        LinhaLimiar(limiar=0.40, metricas=metricas_menor_f1, injecoes_bloqueadas=10),
        LinhaLimiar(limiar=0.50, metricas=metricas_base, injecoes_bloqueadas=8),
    ]
    assert escolher_limiar(linhas1) == 0.50

    # Caso 2: Empate de F1, maior número de injeções bloqueadas vence
    linhas2 = [
        LinhaLimiar(limiar=0.45, metricas=metricas_base, injecoes_bloqueadas=8),
        LinhaLimiar(limiar=0.50, metricas=metricas_base, injecoes_bloqueadas=10),
    ]
    assert escolher_limiar(linhas2) == 0.50

    # Caso 3: Empate de F1 e injeções, menor limiar vence
    linhas3 = [
        LinhaLimiar(limiar=0.55, metricas=metricas_base, injecoes_bloqueadas=10),
        LinhaLimiar(limiar=0.45, metricas=metricas_base, injecoes_bloqueadas=10),
    ]
    assert escolher_limiar(linhas3) == 0.45


def test_escolher_limiar_lista_vazia_levanta_erro():
    """Lista vazia de linhas deve levantar ValueError explicativo (A6-128)."""
    with pytest.raises(ValueError, match="Lista de linhas vazia"):
        escolher_limiar([])


def test_varrer_limiares_tamanhos_incompativeis_levanta_erro():
    """Tamanhos divergentes entre perguntas e distâncias disparam erro (A6-128)."""
    perguntas = [PerguntaRotulada(pergunta="P1", esperado="dentro", tipo="regra")]
    with pytest.raises(ValueError, match="Tamanhos incompatíveis"):
        varrer_limiares(perguntas, [0.1, 0.2], [0.5])


def test_converter_historico_alterna_mensagens():
    """Valida conversão de lista de strings em mensagens Human/AI alternadas (A6-128)."""
    historico = ["Quero criar campanha", "Qual percentual?", "2% por favor"]
    mensagens = converter_historico(historico)

    assert len(mensagens) == 3
    assert isinstance(mensagens[0], HumanMessage) and mensagens[0].content == "Quero criar campanha"
    assert isinstance(mensagens[1], AIMessage) and mensagens[1].content == "Qual percentual?"
    assert isinstance(mensagens[2], HumanMessage) and mensagens[2].content == "2% por favor"


def test_converter_historico_vazio_retorna_lista_vazia():
    """Histórico vazio deve resultar em lista vazia de mensagens (A6-128)."""
    assert converter_historico([]) == []


def test_calcular_estatisticas_latencia():
    """Valida cálculo de estatísticas de tempo de inferência (A6-128)."""
    dados = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = calcular_estatisticas_latencia(dados)

    assert stats.media_ms == 30.0
    assert stats.mediana_ms == 30.0
    assert stats.min_ms == 10.0
    assert stats.max_ms == 50.0
    assert stats.p95_ms == 48.0


def test_calcular_estatisticas_latencia_lista_vazia_levanta_erro():
    """Lista vazia de latências dispara ValueError com mensagem clara (A6-128)."""
    with pytest.raises(ValueError, match="Lista de latências vazia"):
        calcular_estatisticas_latencia([])


def test_formatar_tabela_limiares():
    """Valida geração correta de tabela Markdown com linhas de limiar (A6-128)."""
    m = Metricas(vp=1, fp=0, vn=1, fn=0, acuracia=1.0, precisao=1.0, recall=1.0, f1=1.0)
    linha = LinhaLimiar(limiar=0.50, metricas=m, injecoes_bloqueadas=5)
    tabela = formatar_tabela_limiares([linha])

    assert "| Limiar | VP | FP | VN | FN |" in tabela
    assert "| 0.50 | 1 | 0 | 1 | 0 | 100.0% | 100.0% | 100.0% | 1.0000 | 5 |" in tabela


def test_formatar_tabela_teste():
    """Valida tabela resumida do limiar único escolhido no teste (A6-128)."""
    m = Metricas(vp=2, fp=0, vn=2, fn=0, acuracia=1.0, precisao=1.0, recall=1.0, f1=1.0)
    linha = LinhaLimiar(limiar=0.45, metricas=m, injecoes_bloqueadas=10)
    tabela = formatar_tabela_teste(linha)

    assert "| Limiar Escolhido |" in tabela
    assert "| 0.45 |" in tabela


def test_formatar_tabela_erros_com_e_sem_erros():
    """Valida exibição de discordâncias ou mensagem amigável de zero erros (A6-128)."""
    msg_sucesso = formatar_tabela_erros([])
    assert "Nenhum erro encontrado" in msg_sucesso

    erros = [
        LinhaErro(
            pergunta="Pergunta teste",
            tipo="neutra",
            esperado="fora",
            previsto="dentro",
            distancia=0.42,
            fonte="especificacao",
            item_proximo="5b",
        )
    ]
    tabela_erro = formatar_tabela_erros(erros)
    assert "| Pergunta | Tipo | Esperado | Previsto |" in tabela_erro
    assert "| Pergunta teste | neutra | fora | dentro | 0.4200 | especificacao | 5b |" in tabela_erro


def test_calcular_desempenho_por_tipo_acertos_e_total():
    """Valida agregação de acertos e total por tipo de pergunta (A6-128)."""
    perguntas = [
        PerguntaRotulada(pergunta="P1", esperado="dentro", tipo="estrategia"),
        PerguntaRotulada(pergunta="P2", esperado="dentro", tipo="estrategia"),
        PerguntaRotulada(pergunta="P3", esperado="fora", tipo="neutra"),
    ]
    linhas = calcular_desempenho_por_tipo(perguntas, [0.4, 0.6, 0.7], 0.5)
    mapa = {l.tipo: l for l in linhas}

    assert mapa["estrategia"].acertos == 1
    assert mapa["estrategia"].total == 2
    assert mapa["estrategia"].taxa_acerto == 0.5
    assert mapa["neutra"].acertos == 1
    assert mapa["neutra"].total == 1
    assert mapa["neutra"].taxa_acerto == 1.0


def test_calcular_desempenho_por_tipo_tamanhos_incompativeis_levanta_erro():
    """Valida que tamanhos incompatíveis disparam ValueError (A6-128)."""
    perguntas = [PerguntaRotulada(pergunta="P1", esperado="dentro", tipo="estrategia")]
    with pytest.raises(ValueError, match="Tamanhos incompatíveis"):
        calcular_desempenho_por_tipo(perguntas, [0.1, 0.2], 0.5)


def test_formatar_tabela_por_tipo():
    """Valida formatação Markdown do desempenho por tipo de pergunta (A6-128)."""
    linhas = [
        LinhaDesempenhoTipo(tipo="estrategia", acertos=8, total=8, taxa_acerto=1.0),
        LinhaDesempenhoTipo(tipo="neutra", acertos=18, total=20, taxa_acerto=0.9),
    ]
    tabela = formatar_tabela_por_tipo(linhas)
    assert "| Tipo | Acertos | Total | Taxa de Acerto |" in tabela
    assert "| estrategia | 8 | 8 | 100.0% |" in tabela
    assert "| neutra | 18 | 20 | 90.0% |" in tabela


def test_formatar_estatisticas_latencia():
    """Valida formatação das métricas de latência para relatório (A6-128)."""
    stats = calcular_estatisticas_latencia([15.0, 25.0])
    texto = formatar_estatisticas_latencia(stats)
    assert "- **Média:** 20.00 ms" in texto
    assert "- **Mediana:** 20.00 ms" in texto


def test_carregar_perguntas_calibracao_e_valida_estrutura():
    """Valida conformidade das 58 perguntas do conjunto de calibração (A6-128)."""
    caminho = Path("app/rag/avaliacao/perguntas_calibracao.json")
    assert caminho.exists()

    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)

    perguntas = [PerguntaRotulada(**item) for item in dados]
    assert len(perguntas) == 58

    dentro = sum(1 for p in perguntas if p.esperado == "dentro")
    fora = sum(1 for p in perguntas if p.esperado == "fora")
    assert dentro == 28
    assert fora == 30

    qtd_estrategia = sum(1 for p in perguntas if p.tipo == "estrategia")
    qtd_neutra = sum(1 for p in perguntas if p.tipo == "neutra")
    assert qtd_estrategia == 8
    assert qtd_neutra == 20

    # 4 neutras com histórico de conversa de campanha (> 6 palavras)
    neutras_com_historico = [
        p for p in perguntas if p.tipo == "neutra" and len(p.historico) > 0
    ]
    assert len(neutras_com_historico) == 4
    for p in neutras_com_historico:
        assert len(p.pergunta.split()) > 6

    # Rótulos permitidos e consistência com esperado
    rotulos_dentro = {"regra", "sistema", "campanha", "follow_up", "legislacao", "estrategia"}
    rotulos_fora = {"neutra", "injecao"}
    for p in perguntas:
        if p.esperado == "dentro":
            assert p.tipo in rotulos_dentro
        else:
            assert p.tipo in rotulos_fora


def test_carregar_perguntas_teste_e_valida_distribuicao():
    """Valida as 64 perguntas de teste na exata distribuição solicitada (A6-128)."""
    caminho = Path("app/rag/avaliacao/perguntas_teste.json")
    assert caminho.exists()

    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)

    perguntas = [PerguntaRotulada(**item) for item in dados]
    assert len(perguntas) == 64

    # Distribuição da 2ª rodada:
    # 10 regra (8 regra + 2 sistema)
    # 10 campanha ou follow_up (5 campanha + 5 follow_up)
    # 20 neutra (10 originais + 6 negócios/mkt + 4 com histórico > 6 palavras)
    # 10 injecao
    # 6 legislacao
    # 8 estrategia
    qtd_regra_sistema = sum(1 for p in perguntas if p.tipo in ("regra", "sistema"))
    qtd_campanha_followup = sum(1 for p in perguntas if p.tipo in ("campanha", "follow_up"))
    qtd_neutra = sum(1 for p in perguntas if p.tipo == "neutra")
    qtd_injecao = sum(1 for p in perguntas if p.tipo == "injecao")
    qtd_legislacao = sum(1 for p in perguntas if p.tipo == "legislacao")
    qtd_estrategia = sum(1 for p in perguntas if p.tipo == "estrategia")

    assert qtd_regra_sistema == 10
    assert qtd_campanha_followup == 10
    assert qtd_neutra == 20
    assert qtd_injecao == 10
    assert qtd_legislacao == 6
    assert qtd_estrategia == 8

    # Rótulo esperado: 34 dentro vs 30 fora
    dentro = sum(1 for p in perguntas if p.esperado == "dentro")
    fora = sum(1 for p in perguntas if p.esperado == "fora")
    assert dentro == 34
    assert fora == 30

    # Follow-ups precisam ter histórico preenchido
    follow_ups = [p for p in perguntas if p.tipo == "follow_up"]
    assert len(follow_ups) == 5
    for fp in follow_ups:
        assert len(fp.historico) > 0

    # 4 neutras com histórico e mais de 6 palavras
    neutras_com_historico = [
        p for p in perguntas if p.tipo == "neutra" and len(p.historico) > 0
    ]
    assert len(neutras_com_historico) == 4
    for p in neutras_com_historico:
        assert len(p.pergunta.split()) > 6


def test_nenhuma_pergunta_do_teste_aparece_na_calibracao():
    """Garante independência estrita entre conjunto de calibração e teste (A6-128)."""
    with open("app/rag/avaliacao/perguntas_calibracao.json", encoding="utf-8") as f:
        calibracao = [PerguntaRotulada(**i).pergunta.strip().lower() for i in json.load(f)]

    with open("app/rag/avaliacao/perguntas_teste.json", encoding="utf-8") as f:
        teste = [PerguntaRotulada(**i).pergunta.strip().lower() for i in json.load(f)]

    assert len(set(calibracao)) == len(calibracao), "Perguntas duplicadas dentro da calibração"
    assert len(set(teste)) == len(teste), "Perguntas duplicadas dentro do teste"
    intersecao = set(calibracao).intersection(set(teste))
    assert len(intersecao) == 0, f"Perguntas repetidas encontradas: {intersecao}"


CAMINHO_GUIA_ESTRATEGIAS = Path("app/rag/corpus/estrategias.md")


def verificar_perguntas_nao_contidas_no_texto(
    perguntas: list[PerguntaRotulada],
    texto_guia: str,
) -> list[str]:
    """Retorna perguntas que aparecem literalmente no texto do guia (A6-128).

    Exemplo:
        >>> p = PerguntaRotulada(pergunta="P", esperado="dentro", tipo="estrategia")
        >>> verificar_perguntas_nao_contidas_no_texto([p], "outra coisa") == []
    """
    texto_minusculo = texto_guia.lower()
    return [
        p.pergunta
        for p in perguntas
        if p.pergunta.strip().lower() in texto_minusculo
    ]


def test_verificar_perguntas_nao_contidas_no_texto_detecta_copia():
    """Valida detecção de cópia literal de pergunta no texto do guia (A6-128)."""
    p_copiada = PerguntaRotulada(pergunta="Texto copiado", esperado="dentro", tipo="estrategia")
    p_inedita = PerguntaRotulada(pergunta="Texto inédito", esperado="dentro", tipo="estrategia")
    texto = "Este é um Texto Copiado de teste do guia."

    encontradas = verificar_perguntas_nao_contidas_no_texto([p_copiada, p_inedita], texto)
    assert encontradas == ["Texto copiado"]


@pytest.mark.skipif(
    not CAMINHO_GUIA_ESTRATEGIAS.exists(),
    reason="Guia de estratégias não encontrado em app/rag/corpus/estrategias.md (A6-128)",
)
def test_nenhuma_pergunta_aparece_literalmente_no_guia_de_estrategias():
    """Confere que nenhuma pergunta de calibração ou teste está no guia (A6-128)."""
    texto = CAMINHO_GUIA_ESTRATEGIAS.read_text(encoding="utf-8")
    with open("app/rag/avaliacao/perguntas_calibracao.json", encoding="utf-8") as f:
        calib = [PerguntaRotulada(**item) for item in json.load(f)]
    with open("app/rag/avaliacao/perguntas_teste.json", encoding="utf-8") as f:
        teste = [PerguntaRotulada(**item) for item in json.load(f)]

    encontradas = verificar_perguntas_nao_contidas_no_texto(calib + teste, texto)
    assert not encontradas, f"Perguntas encontradas literalmente no guia: {encontradas}"
