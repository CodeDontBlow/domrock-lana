import json
import re
import time
from typing import Any

from langchain_core.tools import tool

from app.tools.correcao_tool.conferencia import (
    BuscarValoresAtuais,
    buscar_valores_atuais,
    conferir_antes_na_base,
)
from app.tools.correcao_tool.dtos import (
    TIPOS_CORRECAO,
    SolicitacaoCorrecao,
    SolicitacaoCorrecaoToolResult,
)
from app.tools.dtos import calcular_tempo_ms

NOME_TOOL_CORRECAO = "registrar_solicitacao_correcao"

# A @tool não aceita dependência injetada (o LLM veria o parâmetro); os testes trocam esta busca por um fake.
buscar_valores_na_base: BuscarValoresAtuais = buscar_valores_atuais


def normalizar_competencia(competencia: str) -> str:
    """Normaliza competência para o formato yyyy-MM.

    Aceita MM/yyyy ou yyyy-MM.
    Ex.: normalizar_competencia("10/2025") -> "2025-10"
    """
    comp = competencia.strip()
    m_mm_yyyy = re.match(r"^(\d{1,2})/(\d{4})$", comp)
    if m_mm_yyyy:
        return f"{m_mm_yyyy.group(2)}-{int(m_mm_yyyy.group(1)):02d}"
    m_yyyy_mm = re.match(r"^(\d{4})-(\d{1,2})(?:-\d{1,2})?$", comp)
    if m_yyyy_mm:
        return f"{m_yyyy_mm.group(1)}-{int(m_yyyy_mm.group(2)):02d}"
    raise ValueError(f"Competência inválida {competencia!r}, esperado formato MM/yyyy ou yyyy-MM")


def montar_retorno_erro_correcao(mensagem: str, inicio: float) -> tuple[str, dict[str, Any]]:
    """Monta retorno padronizado de erro da ferramenta de correção cadastral.

    Ex.: montar_retorno_erro_correcao("Tipo inválido", time.perf_counter())
    """
    res = SolicitacaoCorrecaoToolResult(
        situacao=mensagem, tempo=calcular_tempo_ms(inicio), competencias=[],
        filtros=None, tabelas=None, registros=None, sql=None, solicitacao={},
    )
    return json.dumps(res.model_dump(mode="json"), ensure_ascii=False), {}


def validar_tipo_correcao(tipo_limpo: str, tipo_original: str) -> str | None:
    """Valida se o tipo de correção é suportado pelo contrato pontual.

    Ex.: validar_tipo_correcao("INVALIDO", "invalido")
    """
    if tipo_limpo not in TIPOS_CORRECAO:
        tipos_validos = ", ".join(TIPOS_CORRECAO.keys())
        return (
            f"Tipo de correção '{tipo_original}' não é uma correção pontual suportada. "
            f"Tipos suportados: {tipos_validos}. "
            "Alterações de percentuais ou regras de comissionamento devem ser registradas via registrar_parametros_regra."
        )
    return None


def validar_competencia_correcao(competencia: str) -> tuple[str | None, str | None]:
    """Valida e normaliza a competência informada.

    Retorna tupla (competencia_normalizada, mensagem_de_erro).
    Ex.: validar_competencia_correcao("10/2025") -> ("2025-10", None)
    """
    try:
        return normalizar_competencia(competencia), None
    except ValueError as e:
        return None, str(e)


def formatar_rotulo_padrao_correcao(
    tipo_limpo: str, tipo_rotulo: str, matricula: str, valor: str
) -> str:
    """Gera o rótulo amigável padrão para o estado da correção cadastral.

    Ex.: formatar_rotulo_padrao_correcao("TROCA_CARGO", "Troca de cargo", "MATRIC-1", "100")
    """
    mapa_rotulos = {
        "TRANSFERENCIA_LOJA": f"{matricula} na loja {valor}",
        "TROCA_CARGO": f"{matricula} no cargo {valor}",
        "DATA_ADMISSAO": f"Data de admissão {valor}",
        "DATA_DEMISSAO": f"Data de demissão {valor}",
    }
    return mapa_rotulos.get(tipo_limpo, f"{tipo_rotulo}: {valor}")


def resolver_rotulos_correcao(
    tipo_limpo: str, tipo_rotulo: str, matricula: str, val_antes: str | None, val_depois: str,
    antes_rotulo: str | None, depois_rotulo: str | None,
) -> tuple[str | None, str]:
    """Resolve os rótulos anterior e posterior, usando padrões caso não tenham sido passados.

    Ex.: resolver_rotulos_correcao(...)
    """
    # Rótulos amigáveis padrão caso não tenham sido passados
    rot_dep = (depois_rotulo or "").strip() or formatar_rotulo_padrao_correcao(
        tipo_limpo, tipo_rotulo, matricula, val_depois
    )
    rot_ant = (antes_rotulo or "").strip()
    if not rot_ant and val_antes is not None:
        rot_ant = formatar_rotulo_padrao_correcao(tipo_limpo, tipo_rotulo, matricula, val_antes)
    return (rot_ant or None), rot_dep


def normalizar_motivo_correcao(motivo: str | None, tipo_rotulo: str, matricula: str) -> str:
    """Retorna motivo informado ou padrão quando omitido.

    Ex.: normalizar_motivo_correcao(None, "Troca de cargo", "MATRIC-1") -> "Troca de cargo de MATRIC-1"
    """
    motivo_limpo = (motivo or "").strip()
    if not motivo_limpo:
        return f"{tipo_rotulo} de {matricula}"
    return motivo_limpo


def criar_solicitacao_correcao(
    tipo: str, rotulo: str, matricula: str, competencia: str, antes: str | None,
    depois: str, antes_rotulo: str | None, depois_rotulo: str, motivo: str,
) -> dict[str, Any]:
    """Instancia a SolicitacaoCorrecao e devolve dicionário serializável.

    Ex.: criar_solicitacao_correcao(...)
    """
    return SolicitacaoCorrecao(
        categoria="CORRECAO", tipo=tipo, tipo_rotulo=rotulo, matricula=matricula,
        competencia=competencia, antes=antes, depois=depois,
        antes_rotulo=antes_rotulo, depois_rotulo=depois_rotulo, motivo=motivo,
    ).model_dump(mode="json")


def montar_sucesso_correcao(
    contrato: dict[str, Any], filtros: dict[str, Any], competencia: str, inicio: float
) -> tuple[str, dict[str, Any]]:
    """Monta tupla de retorno de sucesso com JSON e artifact.

    Ex.: montar_sucesso_correcao(contrato, filtros, "2025-10", time.perf_counter())
    """
    resultado = SolicitacaoCorrecaoToolResult(
        situacao="ok", tempo=calcular_tempo_ms(inicio), tabelas=[], competencias=[competencia],
        filtros=filtros, sql=None, solicitacao=contrato,
    )
    return json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False), contrato


@tool(NOME_TOOL_CORRECAO, response_format="content_and_artifact")
def registrar_solicitacao_correcao(
    tipo: str,
    matricula: str,
    competencia: str,
    depois: str,
    antes: str | None = None,
    antes_rotulo: str | None = None,
    depois_rotulo: str | None = None,
    motivo: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Registra uma solicitação de correção pontual na base de dados para o painel HITL.

    Use SOMENTE quando o usuário solicitar correção cadastral pontual na base de dados
    (um dos 4 tipos: TRANSFERENCIA_LOJA, TROCA_CARGO, DATA_ADMISSAO, DATA_DEMISSAO)
    e após confirmar na base (via `consultar_banco`) que a matrícula existe e que os dados atuais
    daquela competência foram checados.
    Os códigos de `antes` e `depois` DEVEM vir do resultado do `consultar_banco` (ex.: cod_loja, cod_cargo, datas).
    Pergunte a competência e o motivo se faltarem, NUNCA assuma.
    Se o dado não bater com a base, avise o valor atual e NÃO chame a ferramenta.
    O pedido só vale depois que um Supervisor aprovar e o usuário precisa clicar em Confirmar no cartão.
    NUNCA use esta ferramenta para regras de campanhas de comissionamento (use registrar_parametros_regra).

    Args:
        tipo: Código da alteração: TRANSFERENCIA_LOJA, TROCA_CARGO, DATA_ADMISSAO ou DATA_DEMISSAO.
        matricula: Matrícula do funcionário afetado (ex.: "MATRIC-38").
        competencia: Mês/ano da competência afetada no formato MM/yyyy ou yyyy-MM (ex.: "10/2025" ou "2025-10").
        depois: Código ou data nova solicitada vinda da base (ex.: "8", "150", "2025-10-01").
        antes: Código ou data anterior confirmada na base ou None (ex.: "33", "100", None).
        antes_rotulo: Rótulo amigável para exibição do estado anterior (ex.: "MATRIC-38 na loja 33").
        depois_rotulo: Rótulo amigável para exibição do novo estado (ex.: "MATRIC-38 na loja 8").
        motivo: Justificativa da alteração. Pergunte ao usuário se faltar.
    """
    inicio = time.perf_counter()
    tipo_l = (tipo or "").strip().upper()
    mat_l = (matricula or "").strip().upper()

    erro_tipo = validar_tipo_correcao(tipo_l, tipo)
    if erro_tipo:
        return montar_retorno_erro_correcao(erro_tipo, inicio)

    comp_norm, erro_comp = validar_competencia_correcao(competencia)
    if erro_comp or not comp_norm:
        return montar_retorno_erro_correcao(erro_comp or "Competência inválida", inicio)

    rotulo = TIPOS_CORRECAO[tipo_l]
    val_ant = (antes.strip() if isinstance(antes, str) else str(antes)) if antes is not None else None
    val_dep = depois.strip() if isinstance(depois, str) else str(depois)
    erro_antes = conferir_antes_na_base(tipo_l, mat_l, comp_norm, val_ant, buscar=buscar_valores_na_base)
    if erro_antes:
        return montar_retorno_erro_correcao(erro_antes, inicio)
    rot_ant, rot_dep = resolver_rotulos_correcao(tipo_l, rotulo, mat_l, val_ant, val_dep, antes_rotulo, depois_rotulo)
    motivo_final = normalizar_motivo_correcao(motivo, rotulo, mat_l)
    solic = criar_solicitacao_correcao(tipo_l, rotulo, mat_l, comp_norm, val_ant, val_dep, rot_ant, rot_dep, motivo_final)
    filtros = {"matricula": mat_l, "tipo": tipo_l, "competencia": comp_norm, "antes": val_ant, "depois": val_dep}
    return montar_sucesso_correcao(solic, filtros, comp_norm, inicio)
