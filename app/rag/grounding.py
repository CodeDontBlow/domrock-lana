"""Grounding documental e guardrail de escopo por similaridade vetorial (A6-128)."""
import re
from typing import Literal

from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel

from app.core.config import extract_text, get_settings
from app.rag.base_vetorial import TrechoEncontrado

MENSAGEM_FORA_DO_ESCOPO = (
    "Posso ajudar com campanhas e comissionamento. Esse assunto está fora do que eu cubro."
)

CARACTERES_MAXIMOS_HISTORICO = 300

ROTULOS_FONTES: dict[str, str] = {
    "especificacao": "especificação",
    "capacidades": "capacidades da Lana",
    "esclarecimentos": "esclarecimentos do cliente",
    "glossario": "glossário",
    "legislacao": "legislação",
    "estrategias": "guia de estratégias de campanha",
    "exemplos": "exemplos de mensagens",
}

# A6-128: frases curtas típicas (roteamento semântico por exemplos). Servem só para o corte do
# guardrail, porque uma pergunta curta e vaga fica longe dos trechos longos; não são conhecimento.
FONTES_SO_PARA_O_CORTE: set[str] = {"exemplos"}

# A6-128: sem um fecho claro, um comando de campanha escrito como regra ("Todas as vendas no
# período... terão um acréscimo...") era lido como mais um trecho, e a Lana respondia com um
# cumprimento em vez de registrar a campanha.
FECHO_DOS_TRECHOS = (
    "[Fim dos trechos de referência. A mensagem do usuário está abaixo; responda a ela.]\n\n"
)

INSTRUCAO_GROUNDING = (
    "[Trechos documentais recuperados para esta mensagem. Em perguntas sobre regras, "
    "responda APENAS com base neles e cite o item (ex.: 'item 5c'). Se a resposta não estiver "
    "nos trechos, diga 'não encontrei isso na especificação'. A especificação da Dom Rock "
    "prevalece sobre as outras fontes. Legislação é só contexto e não vira parecer jurídico. "
    "Em pedidos de ideia ou estratégia, use os trechos do guia de estratégias junto com os dados, "
    "trazendo opções com prós e riscos. Pedidos de campanha seguem o fluxo normal.]\n\n"
)

SituacaoGrounding = Literal["no_escopo", "fora_do_escopo", "indisponivel", "desligado"]


class ConfigRag(BaseModel, frozen=True):
    """Parâmetros de configuração do RAG da Lana."""

    ativo: bool
    limiar: float
    top_k: int

    @classmethod
    def do_settings(cls) -> "ConfigRag":
        """Instancia a configuração a partir das variáveis de ambiente atuais."""
        cfg = get_settings()
        return cls(
            ativo=bool(cfg.RAG_ATIVO),
            limiar=float(cfg.RAG_LIMIAR_DISTANCIA),
            top_k=int(cfg.RAG_TOP_K),
        )


class ResultadoGrounding(BaseModel, frozen=True):
    """Resultado da checagem de grounding e do guardrail de escopo."""

    situacao: SituacaoGrounding
    assunto_mais_proximo: str | None = None
    item: str | None = None
    distancia: float | None = None
    limiar: float
    trechos: list[str] = []


def _grounding_sem_busca(situacao: SituacaoGrounding, limiar: float) -> ResultadoGrounding:
    """Gera resultado padronizado de grounding quando não há busca vetorial."""
    return ResultadoGrounding(
        situacao=situacao,
        assunto_mais_proximo=None,
        item=None,
        distancia=None,
        limiar=limiar,
        trechos=[],
    )


def avaliar_grounding(
    encontrados: list[TrechoEncontrado], limiar: float
) -> ResultadoGrounding:
    """Avalia se a consulta mais próxima está dentro do limiar de distância (A6-128)."""
    if not encontrados:
        return _grounding_sem_busca("fora_do_escopo", limiar)
    mais_prox = encontrados[0]
    sit: SituacaoGrounding = "no_escopo" if mais_prox.distancia <= limiar else "fora_do_escopo"
    t = mais_prox.trecho
    return ResultadoGrounding(
        situacao=sit,
        assunto_mais_proximo=t.titulo,
        item=t.item,
        distancia=mais_prox.distancia,
        limiar=limiar,
        trechos=[item.trecho.id for item in encontrados],
    )



def _filtrar_mensagens_historico(mensagens: list[BaseMessage]) -> list[str]:
    validas: list[str] = []
    for m in mensagens:
        if isinstance(m, SystemMessage) or getattr(m, "type", "") == "system":
            continue
        texto = extract_text(m).strip()
        if texto.startswith("[Mensagem do sistema"):
            continue
        if texto:
            # A6-128: corta cada mensagem do histórico para limitar o tamanho
            validas.append(texto[:CARACTERES_MAXIMOS_HISTORICO])
    return validas[-2:]


def texto_de_busca(
    user_input: str,
    historico_mensagens: list[BaseMessage],
) -> str:
    """Compõe o texto para busca vetorial com mensagem atual primeiro (A6-128).

    Ex.: texto_de_busca("sim", [HumanMessage("crie a campanha")])
    """
    texto_atual = user_input.strip()
    # A6-128: com histórico, a busca sempre leva a última troca. Uma regra de "só mensagens curtas"
    # cortava respostas longas no meio do fluxo (ex.: "Pode usar novembro de 2025 como referência,
    # com 0% de crescimento..."). Uma pergunta fora do assunto no meio da conversa passa a ser
    # recusada pelas regras de escopo do prompt, não pelo vetor.
    # A mensagem atual vem primeiro porque o embedding corta o fim de textos longos.
    partes = [texto_atual] if texto_atual else []
    partes.extend(_filtrar_mensagens_historico(historico_mensagens))
    return "\n".join(partes).strip()


def _formatar_bloco_trecho(achado: TrechoEncontrado) -> str:
    trecho = achado.trecho
    rotulo = ROTULOS_FONTES.get(trecho.fonte, trecho.fonte)
    return f"[{rotulo}] item {trecho.item} — {trecho.titulo}: {trecho.texto}"


def contexto_documental(encontrados: list[TrechoEncontrado]) -> str:
    """Monta o bloco de grounding documental a ser inserido no prompt do agente.

    Ex.: contexto_documental(achados)
    """
    conhecimento = [a for a in encontrados if a.trecho.fonte not in FONTES_SO_PARA_O_CORTE]
    if not conhecimento:
        return ""
    blocos = [_formatar_bloco_trecho(a) for a in conhecimento]
    return f"{INSTRUCAO_GROUNDING}{'\n\n'.join(blocos)}\n\n{FECHO_DOS_TRECHOS}"

