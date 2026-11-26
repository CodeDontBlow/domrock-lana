import ast
import json
import logging
import re
import threading
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from app.agent.fonte_dos_valores import conferir_fonte_dos_valores
from app.agent.graph import lana
from app.agent.prompts import SYSTEM_RULES
from app.agent.trilha import montar_trilha_chat, montar_trilha_fora_do_escopo
from app.core.config import extract_text, get_settings
from app.tools.correcao_tool.tool import NOME_TOOL_CORRECAO
from app.rag.base_vetorial import BaseConhecimento, TrechoEncontrado, obter_base_conhecimento
from app.rag.grounding import (
    MENSAGEM_FORA_DO_ESCOPO,
    ConfigRag,
    ResultadoGrounding,
    _grounding_sem_busca,
    avaliar_grounding,
    contexto_documental,
    texto_de_busca,
)
from app.tools.regra_tool.tool import NOME_TOOL_REGRA

logger = logging.getLogger(__name__)

def _parse_tool_content(conteudo: Any) -> Any:
    """Desserializa o retorno da ferramenta, suportando JSON e representações Python com Decimal."""
    if not isinstance(conteudo, str):
        return conteudo
    try:
        return json.loads(conteudo)
    except Exception:
        pass

    # Trata casos onde o Python/LangChain serializou o dict como str contendo Decimal(...) e aspas simples
    texto_limpo = re.sub(r"Decimal\((['\"]?)([0-9.-]+)\1\)", r"\2", conteudo)
    try:
        return json.loads(texto_limpo)
    except Exception:
        pass

    try:
        return ast.literal_eval(texto_limpo)
    except Exception:
        pass

    return conteudo


# Função de coleta de eventos da AI
def get_events(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    events_list = []
    paired_tools = {}
    last_reasoning = ''

    for m in messages:

        if m.type == 'ai':
            ia_text = ""
            if isinstance(m.content, str):
                ia_text = m.content
            elif isinstance(m.content, list):
                # Trata casos onde o Gemini devolve conteúdo como lista de blocos
                ia_text = " ".join([block["text"] for block in m.content if isinstance(block, dict) and "text" in block])

            if ia_text and not (hasattr(m, "tool_calls") and m.tool_calls):
                continue
            
            if ia_text:
                last_reasoning = ia_text.strip()

            if hasattr(m, "tool_calls") and m.tool_calls:
                for call in m.tool_calls:
                    call_id = call["id"]
                    desc = call["args"].get("explicacao") or last_reasoning or f"Executando ação em {call['name']}."
                    paired_tools[call_id] = {
                        "ferramenta": call["name"],
                        "descricao_legivel": desc,
                        "tempo": 0,
                        "situacao": "executando",
                        "tabelas": None,
                        "competencias": None,
                        "filtros": None,
                        "registros": None,
                        "sql": None,
                        "args": call["args"],
                        "result": None,
                        "tool": call["name"],
                        "reasoning": desc,
                    }
                    events_list.append(paired_tools[call_id])

                last_reasoning = ''

        elif m.type == "tool":
            call_id = getattr(m, "tool_call_id", None)
            if call_id in paired_tools:
                conteudo = m.content
                dados_resultado = _parse_tool_content(conteudo)

                paired_tools[call_id]["result"] = dados_resultado

                if isinstance(dados_resultado, dict):
                    if "tempo" in dados_resultado:
                        try:
                            paired_tools[call_id]["tempo"] = int(dados_resultado["tempo"])
                        except (ValueError, TypeError):
                            paired_tools[call_id]["tempo"] = 0
                    elif "tempo_ms" in dados_resultado:
                        paired_tools[call_id]["tempo"] = int(round(dados_resultado["tempo_ms"]))

                    if "situacao" in dados_resultado:
                        paired_tools[call_id]["situacao"] = str(dados_resultado["situacao"])
                    else:
                        paired_tools[call_id]["situacao"] = "ok"

                    paired_tools[call_id]["tabelas"] = dados_resultado.get("tabelas")
                    paired_tools[call_id]["competencias"] = dados_resultado.get("competencias")
                    paired_tools[call_id]["filtros"] = dados_resultado.get("filtros")
                    paired_tools[call_id]["registros"] = dados_resultado.get("registros")
                    paired_tools[call_id]["sql"] = dados_resultado.get("sql") or dados_resultado.get("sql_gerado")
                    paired_tools[call_id]["motivo"] = dados_resultado.get("motivo")
                    paired_tools[call_id]["horario"] = dados_resultado.get("horario")
                    paired_tools[call_id]["status"] = dados_resultado.get("status")
                else:
                    paired_tools[call_id]["situacao"] = "ok"

    return events_list


def extrair_regra(messages: list[BaseMessage]) -> dict[str, Any] | None:
    """Última regra registrada no turno (artifact da tool de parâmetros), ou None."""
    for m in reversed(messages):
        if isinstance(m, ToolMessage) and m.name == NOME_TOOL_REGRA and m.artifact:
            return m.artifact
    return None


def extrair_solicitacao(messages: list[BaseMessage]) -> dict[str, Any] | None:
    """Última solicitação de alteração/correção registrada no turno (artifact da tool), ou None."""
    for m in reversed(messages):
        if isinstance(m, ToolMessage) and m.name == NOME_TOOL_CORRECAO and m.artifact:
            return m.artifact
    return None


def contexto_do_painel(regra: dict[str, Any] | None) -> str:
    """Valores atuais do painel, que o usuário pode ter editado sem o agente saber.

    Ex.: contexto_do_painel({"parametros": [{"key": "pct_acrescimo", "value": 2.0}]})
    """
    if not regra:
        return ""
    valores = {p["key"]: p.get("value") for p in regra.get("parametros", [])}
    return (
        "[Parâmetros atuais no painel, já revisados pelo usuário. Parta deles ao registrar a "
        f"regra e mude só o que ele pedir: {json.dumps(valores, ensure_ascii=False)}]\n\n"
    )


def contexto_da_solicitacao(solicitacao: dict[str, Any] | None) -> str:
    """Valores atuais da solicitação de alteração no chat/painel HITL.

    Permite que o usuário peça alterações em linguagem natural e o agente atualize a solicitação existente.
    """
    if not solicitacao:
        return ""
    campos = {
        "tipo": solicitacao.get("tipo"),
        "matricula": solicitacao.get("matricula"),
        "competencia": solicitacao.get("competencia"),
        "antes": solicitacao.get("antes"),
        "depois": solicitacao.get("depois"),
        "motivo": solicitacao.get("motivo"),
    }
    return (
        "[Solicitação de alteração da base atual no chat/painel (HITL), ainda NÃO enviada aos supervisores. "
        "Parta destes valores ao chamar registrar_solicitacao_correcao novamente e altere apenas o que o usuário pedir: "
        f"{json.dumps(campos, ensure_ascii=False)}]\n\n"
    )


def _converter_item_historico(item: dict[str, Any] | BaseMessage) -> BaseMessage:
    if isinstance(item, BaseMessage):
        return item
    papel = item.get("papel")
    texto = item.get("texto", "")
    if papel == "lana":
        return AIMessage(content=texto)
    if papel == "sistema":
        return HumanMessage(content=f"[Mensagem do sistema, não do usuário] {texto}")
    return HumanMessage(content=texto)


def _converter_historico(historico: list[dict[str, Any]] | None) -> list[BaseMessage]:
    if not historico:
        return []
    return [_converter_item_historico(item) for item in historico]


def _mensagens_de_entrada(
    user_input: str,
    regra: dict[str, Any] | None,
    historico_mensagens: list[BaseMessage],
    solicitacao: dict[str, Any] | None = None,
    achados: list[TrechoEncontrado] | None = None,
) -> list[BaseMessage]:
    prefixo = contexto_do_painel(regra) + contexto_da_solicitacao(solicitacao)
    mensagem_atual = HumanMessage(content=prefixo + contexto_documental(achados or []) + user_input)
    return [*SYSTEM_RULES, *historico_mensagens, mensagem_atual]


_travas_por_chat: dict[str, threading.Lock] = {}
_trava_do_registro = threading.Lock()


def _trava_do_chat(thread_id: str) -> threading.Lock:
    # Dois turnos simultâneos no mesmo thread poderiam conflitar ao invocar o agente.
    with _trava_do_registro:
        return _travas_por_chat.setdefault(thread_id, threading.Lock())


def _obter_base_ou_nada() -> BaseConhecimento | None:
    """Obtém singleton da base vetorial capturando exceções com log JSON (A6-128)."""
    try:
        return obter_base_conhecimento()
    except Exception as exc:
        logger.warning(
            json.dumps({"evento": "rag_indisponivel", "erro": str(exc)}, ensure_ascii=False)
        )
        return None


# Função para invocar o grafo via requisição HTTP
def lana_invoke(
    thread_id: str,
    user_input: str,
    regra: dict[str, Any] | None = None,
    historico: list[dict[str, Any]] | None = None,
    solicitacao: dict[str, Any] | None = None,
    base: BaseConhecimento | None = None,
    config_rag: ConfigRag | None = None,
) -> dict[str, Any]:
    with _trava_do_chat(thread_id):
        config = config_rag or ConfigRag.do_settings()
        base_ativa = base or (_obter_base_ou_nada() if config.ativo else None)
        return _invocar_turno(
            thread_id, user_input, regra, historico, solicitacao, base=base_ativa, config=config
        )


# A6-128: mensagem amigável quando o limite de recursão do LangGraph é atingido.
MENSAGEM_LIMITE_DE_PASSOS: str = (
    "Não consegui concluir dentro do limite de passos. Tente dividir o pedido em partes menores."
)


def _executar_grafo(entrada: list[BaseMessage]) -> list[BaseMessage]:
    limite = get_settings().LANA_LIMITE_PASSOS
    try:
        result = lana.invoke({"messages": entrada}, {"recursion_limit": limite})
        novas = result["messages"][len(entrada):]
        return novas if novas else [result["messages"][-1]]
    except GraphRecursionError:
        # A6-128: observabilidade do guardrail de agente atingindo o limite de passos.
        logger.warning(json.dumps({"evento": "limite_de_passos", "limite": limite}, ensure_ascii=False))
        return [AIMessage(content=MENSAGEM_LIMITE_DE_PASSOS)]


def _conferir_resposta_do_turno(
    agent_response: BaseMessage,
    user_input: str,
    regra: dict[str, Any] | None,
    regra_do_turno: dict[str, Any] | None,
    trilha: dict[str, Any] | None,
    historico_mensagens: list[BaseMessage],
    historico: list[dict[str, Any]] | None,
) -> str:
    textos = [user_input, *(extract_text(m) for m in historico_mensagens)]
    trilhas_hist = [item.get("trilha") for item in (historico or []) if isinstance(item, dict) and item.get("trilha")]
    fichas_hist = [item.get("regra") for item in (historico or []) if isinstance(item, dict) and item.get("regra")]
    fichas = [regra, regra_do_turno, *fichas_hist]
    return conferir_fonte_dos_valores(
        extract_text(agent_response), trilha, textos, fichas, trilhas_historico=trilhas_hist
    )


def extrair_alertas(trilha: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extrai alertas de segurança ocorridos no turno (ex.: consultas bloqueadas)."""
    alertas = []
    if trilha and "eventos" in trilha:
        for evento in trilha["eventos"]:
            if evento.get("status") == "bloqueada":
                alertas.append({
                    "tipo": "consulta_bloqueada",
                    "sql": evento.get("sql"),
                    "motivo": evento.get("motivo"),
                    "horario": evento.get("horario"),
                    "status": "bloqueada",
                    "mensagem": f"Consulta SQL bloqueada por segurança: {evento.get('motivo')}",
                })
    return alertas


def _aplicar_grounding(
    user_input: str,
    historico_mensagens: list[BaseMessage],
    base: BaseConhecimento | None,
    config: ConfigRag,
) -> tuple[ResultadoGrounding, list[TrechoEncontrado]]:
    if not config.ativo:
        return _grounding_sem_busca("desligado", config.limiar), []
    if base is None:
        return _grounding_sem_busca("indisponivel", config.limiar), []
    try:
        consulta = texto_de_busca(user_input, historico_mensagens)
        achados = base.buscar(consulta, k=config.top_k)
        return avaliar_grounding(achados, limiar=config.limiar), achados
    except Exception as exc:
        logger.warning(
            json.dumps({"evento": "rag_indisponivel", "erro": str(exc)}, ensure_ascii=False)
        )
        return _grounding_sem_busca("indisponivel", config.limiar), []


def _resposta_fora_do_escopo(
    thread_id: str,
    grounding: ResultadoGrounding,
) -> dict[str, Any]:
    dados_grounding = grounding.model_dump(mode="json")
    trilha = montar_trilha_fora_do_escopo(dados_grounding)
    return {
        "chat_id": thread_id,
        "response": MENSAGEM_FORA_DO_ESCOPO,
        "events": [],
        "regra": None,
        "trilha": trilha,
        "alertas": [],
    }


def _montar_resultado_turno(
    thread_id: str,
    messages: list[BaseMessage],
    user_input: str,
    regra: dict[str, Any] | None,
    historico_mensagens: list[BaseMessage],
    historico: list[dict[str, Any]] | None,
    grounding: ResultadoGrounding | None = None,
) -> dict[str, Any]:
    regra_do_turno = extrair_regra(messages)
    solicitacao_do_turno = extrair_solicitacao(messages)
    dados_g = grounding.model_dump(mode="json") if grounding else None
    trilha = montar_trilha_chat(messages, get_settings().AI_MODEL, grounding=dados_g)
    resposta = _conferir_resposta_do_turno(
        messages[-1], user_input, regra, regra_do_turno, trilha, historico_mensagens, historico
    )
    return {
        "chat_id": thread_id, "response": resposta, "events": get_events(messages),
        "regra": regra_do_turno, "solicitacao": solicitacao_do_turno, "trilha": trilha,
        "alertas": extrair_alertas(trilha),
    }


def _invocar_turno(
    thread_id: str,
    user_input: str,
    regra: dict[str, Any] | None,
    historico: list[dict[str, Any]] | None = None,
    solicitacao: dict[str, Any] | None = None,
    base: BaseConhecimento | None = None,
    config: ConfigRag | None = None,
) -> dict[str, Any]:
    configuracao = config or ConfigRag.do_settings()
    hist_msgs = _converter_historico(historico)
    grounding, achados = _aplicar_grounding(user_input, hist_msgs, base, configuracao)
    if grounding.situacao == "fora_do_escopo":
        return _resposta_fora_do_escopo(thread_id, grounding)

    entrada = _mensagens_de_entrada(user_input, regra, hist_msgs, solicitacao, achados)
    messages = _executar_grafo(entrada)
    return _montar_resultado_turno(
        thread_id, messages, user_input, regra, hist_msgs, historico, grounding
    )
