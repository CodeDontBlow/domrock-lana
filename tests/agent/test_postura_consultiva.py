"""Testes de validação da postura consultiva da Lana nas regras de sistema (A6-128)."""
from app.agent.prompts import SYSTEM_RULES
from scripts.conversas_de_postura import formatar_ferramentas, verificar_pergunta_generica


def test_postura_consultiva_presente_sem_registro_imediato() -> None:
    """Garante que perguntas e análises priorizam resposta e dados sem registrar campanha."""
    textos = [r.content for r in SYSTEM_RULES]
    regra_encontrada = any(
        "postura consultiva" in t.lower()
        and "sem chamar `registrar_parametros_regra`" in t
        for t in textos
    )
    assert regra_encontrada, "SYSTEM_RULES deve orientar a responder perguntas e análises sem chamar tool de regra"


def test_proibe_pergunta_generica_no_fechamento() -> None:
    """Garante proibição de perguntas genéricas de empurrar campanha no fechamento."""
    textos = [r.content for r in SYSTEM_RULES]
    regra_encontrada = any(
        "vamos criar uma campanha?" in t.lower()
        and "quer fazer uma campanha?" in t.lower()
        and "nunca" in t.lower()
        for t in textos
    )
    assert regra_encontrada, "SYSTEM_RULES deve proibir perguntas genéricas no fechamento"


def test_permite_sugerir_mas_proibe_assumir_valores_sem_usuario() -> None:
    """Garante remoção da trava cega de sugestão mantendo a proteção contra assumir valores."""
    textos = [r.content for r in SYSTEM_RULES]
    assert not any("sem sugerir nem assumir valores" in t.lower() for t in textos), (
        "SYSTEM_RULES não deve mais conter a frase impeditiva 'sem sugerir nem assumir valores'"
    )
    protecao_mantida = any(
        "nunca registre nem assuma valores" in t.lower()
        for t in textos
    )
    assert protecao_mantida, "SYSTEM_RULES deve manter proteção contra registrar/assumir valores não confirmados"


def test_conversa_sem_campanha_e_uma_conversa_uma_campanha() -> None:
    """Garante que conversas de dúvidas/análises são válidas sem campanha mantendo a regra 1 para 1."""
    textos = [r.content for r in SYSTEM_RULES]
    regra_encontrada = any(
        "uma conversa, uma campanha" in t.lower()
        and "sem nenhuma campanha" in t.lower()
        and "nova conversa" in t.lower()
        for t in textos
    )
    assert regra_encontrada, "SYSTEM_RULES deve admitir conversas sem campanha mantendo regra de nova conversa"


def test_verificar_pergunta_generica_detecta_fechamento_inadequado() -> None:
    """Garante detecção de perguntas genéricas empurrando campanha no fim da mensagem."""
    assert verificar_pergunta_generica("Análise pronta. Quer fazer uma campanha?")
    assert verificar_pergunta_generica("Totais conferidos! Vamos criar uma campanha?")
    assert not verificar_pergunta_generica("Quer que eu compare 1% e 2% para a marca 10?")
    assert not verificar_pergunta_generica("")


def test_formatar_ferramentas_retorna_nomes_ou_nenhuma() -> None:
    """Garante formatação legível da lista de ferramentas nos eventos."""
    assert formatar_ferramentas([]) == "nenhuma"
    eventos = [{"ferramenta": "consultar_banco"}, {"tool": "registrar_parametros_regra"}]
    assert formatar_ferramentas(eventos) == "consultar_banco, registrar_parametros_regra"
