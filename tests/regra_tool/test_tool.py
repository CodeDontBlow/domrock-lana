import json

from langchain_core.messages import AIMessage, ToolMessage

from app.tools.regra_tool.tool import NOME_TOOL_REGRA, registrar_parametros_regra


def _chamar(args: dict[str, object]) -> ToolMessage:
    chamada = {"name": NOME_TOOL_REGRA, "args": {"explicacao": "Registrando a campanha", **args}, "id": "call-1", "type": "tool_call"}
    return registrar_parametros_regra.invoke(chamada)


def test_tool_devolve_faltantes_para_a_llm_e_contrato_como_artifact() -> None:
    mensagem = _chamar({"comando_original": "+1% na black friday", "pct_acrescimo": 1.0})

    assert json.loads(mensagem.content)["faltantes"][0] == "periodo"
    assert mensagem.artifact["raw_prompt"] == "+1% na black friday"
    assert mensagem.artifact["status"] == "DRAFT_PENDING_REVIEW"


def test_tool_pede_o_periodo_e_nao_pede_o_orcamento() -> None:
    # Critério do A6-72: "quero +1% para todas as marcas, exceto gerentes".
    mensagem = _chamar({
        "comando_original": "quero +1% para todas as marcas, exceto gerentes",
        "pct_acrescimo": 1.0, "marcas_alvo": ["ALL"], "cargos_alvo": ["100", "200", "300"],
    })

    faltantes = json.loads(mensagem.content)["faltantes"]
    assert "periodo" in faltantes and "orcamento_limite" not in faltantes


def test_tool_guarda_a_data_ja_informada_e_pede_a_outra() -> None:
    mensagem = _chamar({"comando_original": "a partir de 24/11", "data_inicio": "2025-11-24"})

    periodo = next(p for p in mensagem.artifact["parametros"] if p["key"] == "periodo")
    assert periodo["value"] == {"data_inicio": "2025-11-24", "data_fim": None}
    assert "periodo" in mensagem.artifact["faltantes"]


def _valor(mensagem: ToolMessage, key: str) -> object:
    return next(p for p in mensagem.artifact["parametros"] if p["key"] == key)["value"]


def test_tool_sugere_a_referencia_no_periodo_futuro_para_a_lana_confirmar() -> None:
    # Ano distante para o teste não depender da data de hoje; a regra é a mesma da Black Friday 2026.
    mensagem = _chamar({"comando_original": "+1% na black friday de 2099",
                        "data_inicio": "2099-11-24", "data_fim": "2099-11-30"})

    conteudo = json.loads(mensagem.content)
    assert conteudo["referencia_sugerida"] == "2098-11"
    assert _valor(mensagem, "competencia_referencia") == "2098-11"
    assert _valor(mensagem, "pct_crescimento") == 0.0
    assert "competencia_referencia" not in conteudo["faltantes"]


def test_tool_registra_a_referencia_confirmada_sem_sugerir_de_novo() -> None:
    mensagem = _chamar({"comando_original": "pode usar nov/2098 com 10%",
                        "data_inicio": "2099-11-24", "data_fim": "2099-11-30",
                        "competencia_referencia": "2098-11", "pct_crescimento": 10.0})

    assert json.loads(mensagem.content)["referencia_sugerida"] is None
    assert _valor(mensagem, "pct_crescimento") == 10.0


def test_tool_nao_sugere_referencia_no_periodo_historico() -> None:
    mensagem = _chamar({"comando_original": "+1% na black friday",
                        "data_inicio": "2025-11-24", "data_fim": "2025-11-30"})

    assert json.loads(mensagem.content)["referencia_sugerida"] is None
    assert _valor(mensagem, "competencia_referencia") is None


def test_extrair_regra_pega_o_ultimo_artifact_do_turno() -> None:
    from app.agent.service import extrair_regra

    primeira = _chamar({"comando_original": "a", "pct_acrescimo": 1.0})
    segunda = _chamar({"comando_original": "a", "pct_acrescimo": 2.0})
    turno = [AIMessage("x"), primeira, segunda, AIMessage("fim")]

    regra = extrair_regra(turno)

    assert regra is not None
    assert next(p for p in regra["parametros"] if p["key"] == "pct_acrescimo")["value"] == 2.0
    assert extrair_regra([AIMessage("sem tool")]) is None


def test_contexto_do_painel_leva_os_valores_editados_ao_agente() -> None:
    from app.agent.service import contexto_do_painel

    regra = {"parametros": [{"key": "pct_acrescimo", "value": 2.0}, {"key": "marcas_alvo", "value": ["30"]}]}

    contexto = contexto_do_painel(regra)

    assert '"pct_acrescimo": 2.0' in contexto and '"marcas_alvo": ["30"]' in contexto
    assert contexto_do_painel(None) == ""
