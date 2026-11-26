"""Testes das funções de grounding e guardrail de escopo (A6-128)."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.rag.grounding import (
    CARACTERES_MAXIMOS_HISTORICO,
    MENSAGEM_FORA_DO_ESCOPO,
    FECHO_DOS_TRECHOS,
    ROTULOS_FONTES,
    ConfigRag,
    avaliar_grounding,
    contexto_documental,
    texto_de_busca,
)
from tests.rag.fakes_rag import encontrado


def test_limiar_configuravel_cenario_do_gherkin():
    achados = [encontrado("5c", distancia=0.50)]
    assert avaliar_grounding(achados, limiar=0.45).situacao == "fora_do_escopo"
    assert avaliar_grounding(achados, limiar=0.55).situacao == "no_escopo"


def test_fora_do_escopo_registra_distancia_e_limiar():
    r = avaliar_grounding([encontrado("5c", distancia=0.62)], limiar=0.50)
    assert (r.situacao, r.distancia, r.limiar, r.item) == ("fora_do_escopo", 0.62, 0.50, "5c")
    assert r.assunto_mais_proximo == "Regra 5c"
    assert r.trechos == ["especificacao:5c"]


def test_sem_trechos_e_fora_do_escopo():
    r = avaliar_grounding([], limiar=0.50)
    assert r.situacao == "fora_do_escopo"
    assert r.distancia is None
    assert r.item is None
    assert r.assunto_mais_proximo is None
    assert r.trechos == []


def test_texto_de_busca_inclui_a_ultima_troca():
    historico = [
        HumanMessage(content="crie a campanha"),
        AIMessage(content="Confirma 2%?"),
    ]
    busca = texto_de_busca("sim, pode registrar", historico)
    assert busca.startswith("sim, pode registrar")
    assert "crie a campanha" in busca
    assert "Confirma 2%?" in busca


def test_texto_de_busca_sem_historico_e_so_a_mensagem():
    busca = texto_de_busca("Qual a previsão do tempo?", [])
    assert busca == "Qual a previsão do tempo?"


def test_texto_de_busca_ignora_mensagens_de_sistema():
    historico = [
        HumanMessage(content="crie a campanha"),
        SystemMessage(content="instruções internas"),
        AIMessage(content="Confirma 2%?"),
    ]
    busca = texto_de_busca("sim", historico)
    assert "instruções internas" not in busca
    assert "crie a campanha" in busca
    assert "Confirma 2%?" in busca


def test_texto_de_busca_ordem_mensagem_atual_primeiro():
    historico = [
        HumanMessage(content="mensagem anterior do usuário"),
        AIMessage(content="resposta anterior da lana"),
    ]
    busca = texto_de_busca("e para a marca 20?", historico)
    linhas = busca.split("\n")
    assert linhas[0] == "e para a marca 20?"
    assert linhas[1] == "mensagem anterior do usuário"
    assert linhas[2] == "resposta anterior da lana"


def test_texto_de_busca_resposta_longa_no_fluxo_inclui_historico():
    # A6-128: regressão. Uma resposta longa no meio do fluxo era buscada sozinha e cortada.
    historico = [
        HumanMessage(content="campanha de +1% na Black Friday, exceto gerentes"),
        AIMessage(content="Qual mês de referência e qual crescimento?"),
    ]
    resposta = "Pode usar novembro de 2025 como referência, com 0% de crescimento. Sem meta."
    busca = texto_de_busca(resposta, historico)
    assert busca.startswith(resposta)
    assert "Black Friday" in busca and "mês de referência" in busca


def test_texto_de_busca_mensagem_curta_inclui_historico():
    historico = [
        HumanMessage(content="detalhes da campanha da marca 10"),
        AIMessage(content="deseja confirmar os parâmetros?"),
    ]
    busca = texto_de_busca("sim, pode registrar", historico)
    assert busca.startswith("sim, pode registrar")
    assert "detalhes da campanha" in busca
    assert "deseja confirmar os parâmetros?" in busca


def test_texto_de_busca_corte_em_300_caracteres():
    mensagem_longa = "A" * 500
    historico = [HumanMessage(content=mensagem_longa)]
    busca = texto_de_busca("sim", historico)
    assert "A" * CARACTERES_MAXIMOS_HISTORICO in busca
    assert "A" * (CARACTERES_MAXIMOS_HISTORICO + 1) not in busca


def test_rotulos_fontes_tem_estrategias():
    assert "estrategias" in ROTULOS_FONTES
    assert ROTULOS_FONTES["estrategias"] == "guia de estratégias de campanha"


def test_contexto_documental_inclui_orientacao_sobre_estrategias():
    texto = contexto_documental([encontrado("5c", distancia=0.3)])
    assert "guia de estratégias" in texto
    assert "prós e riscos" in texto


def test_contexto_documental_manda_usar_apenas_os_trechos_e_citar_o_item():
    texto = contexto_documental([encontrado("5c", distancia=0.3)])
    assert "APENAS" in texto
    assert "item 5c" in texto
    assert "não encontrei" in texto.lower()
    assert "[especificação]" in texto


def test_contexto_documental_vazio_devolve_string_vazia():
    assert contexto_documental([]) == ""


def test_config_rag_do_settings():
    config = ConfigRag.do_settings()
    assert isinstance(config.ativo, bool)
    assert isinstance(config.limiar, float)
    assert isinstance(config.top_k, int)



def test_contexto_documental_nao_leva_exemplos_ao_prompt():
    # A6-128: exemplos servem só para o corte; não são conhecimento para a resposta.
    achados = [encontrado("ex-estrategia-1", 0.2, fonte="exemplos"), encontrado("5c", 0.4)]
    texto = contexto_documental(achados)
    assert "item 5c" in texto and "ex-estrategia-1" not in texto


def test_contexto_documental_so_com_exemplos_fica_vazio():
    assert contexto_documental([encontrado("ex-oi", 0.1, fonte="exemplos")]) == ""


def test_contexto_documental_fecha_os_trechos_antes_da_mensagem_do_usuario():
    # A6-128: regressão. Sem o fecho, um comando de campanha era lido como mais um trecho.
    assert contexto_documental([encontrado("6f", 0.3)]).endswith(FECHO_DOS_TRECHOS)
