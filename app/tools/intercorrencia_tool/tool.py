import json
import time
from typing import Any

from langchain_core.tools import tool

from app.tools.intercorrencia_tool.conferencia import BuscarMatricula, conferir_matricula, matricula_existe
from app.tools.dtos import calcular_tempo_ms
from app.tools.intercorrencia_tool.dtos import (
    TIPOS_INTERCORRENCIA,
    SolicitacaoIntercorrencia,
    SolicitacaoIntercorrenciaToolResult,
)

NOME_TOOL_INTERCORRENCIA = "registrar_intercorrencia"

# A @tool não aceita dependência injetada (o LLM veria o parâmetro); os testes trocam esta busca por um fake.
buscar_matricula_na_base: BuscarMatricula = matricula_existe


def formatar_data_br(data_iso: str) -> str:
    """Converte data YYYY-MM-DD em DD/MM/YYYY.

    Ex.: formatar_data_br("2025-12-01") -> "01/12/2025"
    """
    partes = data_iso.strip().split("-")
    if len(partes) == 3:
        return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return data_iso.strip()


def montar_retorno_erro_intercorrencia(
    mensagem: str, inicio: float
) -> tuple[str, dict[str, Any]]:
    """Monta retorno padronizado de erro da ferramenta de intercorrência.

    Ex.: montar_retorno_erro_intercorrencia("Motivo obrigatório", time.perf_counter())
    """
    res = SolicitacaoIntercorrenciaToolResult(
        situacao=mensagem, tempo=calcular_tempo_ms(inicio), competencias=[],
        filtros=None, tabelas=None, registros=None, sql=None, solicitacao={},
    )
    return json.dumps(res.model_dump(mode="json"), ensure_ascii=False), {}


def validar_motivo_intercorrencia(motivo: str) -> str | None:
    """Valida se o motivo foi informado para intercorrência.

    Ex.: validar_motivo_intercorrencia("") -> "Motivo é obrigatório para registrar intercorrência"
    """
    # Validação do motivo obrigatório
    if not motivo:
        return "Motivo é obrigatório para registrar intercorrência"
    return None


def validar_tipo_intercorrencia(tipo_limpo: str, tipo_original: str) -> str | None:
    """Valida se o tipo da intercorrência pertence aos tipos suportados.

    Ex.: validar_tipo_intercorrencia("INVALIDO", "invalido")
    """
    # Validação de tipo suportado
    if tipo_limpo not in TIPOS_INTERCORRENCIA:
        tipos_validos = ", ".join(TIPOS_INTERCORRENCIA.keys())
        return f"Tipo de intercorrência '{tipo_original}' não suportado. Tipos válidos: {tipos_validos}."
    return None


def validar_data_inicio_intercorrencia(d_inicio: str, data_inicio_original: str) -> str | None:
    """Valida o formato básico da data de início no formato YYYY-MM-DD.

    Ex.: validar_data_inicio_intercorrencia("2025", "2025")
    """
    # Validação de data_inicio
    if len(d_inicio) < 7 or "-" not in d_inicio:
        return f"Data de início inválida {data_inicio_original!r}, esperado formato YYYY-MM-DD"
    return None


def validar_datas_intercorrencia(
    tipo_limpo: str, tipo_rotulo: str, d_inicio: str, d_fim: str | None
) -> str | None:
    """Valida coerência de datas de acordo com o tipo da intercorrência.

    Ex.: validar_datas_intercorrencia("FERIAS", "Férias", "2025-12-10", "2025-12-01")
    """
    # Validações específicas por tipo
    if tipo_limpo == "DEMISSAO":
        if d_fim and d_fim != d_inicio:
            return "Demissão não leva data final diferente da data de demissão"
        return None
    if not d_fim:
        return f"Data final é obrigatória para {tipo_rotulo.lower()}"
    if d_fim < d_inicio:
        return "A data final precisa ser igual ou posterior à inicial"
    return None


def validar_loja_intercorrencia(
    tipo_limpo: str, tipo_rotulo: str, loja_str: str | None
) -> str | None:
    """Valida se o código da loja é informado apenas quando exigido (COBERTURA_LOJA).

    Ex.: validar_loja_intercorrencia("COBERTURA_LOJA", "Cobertura de loja", None)
    """
    if tipo_limpo == "COBERTURA_LOJA":
        if not loja_str:
            return "Código da loja (cod_loja) é obrigatório para cobertura de loja"
        return None
    if loja_str:
        if tipo_limpo == "DEMISSAO":
            return "Código da loja não deve ser informado para demissão"
        return f"Código da loja não deve ser informado para {tipo_rotulo.lower()}"
    return None


def validar_regras_intercorrencia(
    tipo_l: str, tipo_orig: str, motivo_l: str, d_ini: str, d_ini_orig: str, d_fim: str | None, loja: str | None
) -> str | None:
    """Executa sequencialmente as validações de regra de negócio para intercorrência.

    Ex.: validar_regras_intercorrencia("FERIAS", "FERIAS", "", "2025-12-01", "2025-12-01", None, None)
    """
    erro = (
        validar_motivo_intercorrencia(motivo_l)
        or validar_tipo_intercorrencia(tipo_l, tipo_orig)
        or validar_data_inicio_intercorrencia(d_ini, d_ini_orig)
    )
    if erro:
        return erro
    rotulo = TIPOS_INTERCORRENCIA[tipo_l]
    return validar_datas_intercorrencia(tipo_l, rotulo, d_ini, d_fim) or validar_loja_intercorrencia(tipo_l, rotulo, loja)


def montar_dados_depois_intercorrencia(
    tipo_limpo: str, tipo_rotulo: str, d_inicio: str, d_fim: str | None, loja_str: str | None
) -> tuple[dict[str, Any], str]:
    """Monta o payload de alterações e rótulo descritivo da intercorrência.

    Ex.: montar_dados_depois_intercorrencia("DEMISSAO", "Demissão", "2025-11-15", None, None)
    """
    if tipo_limpo == "DEMISSAO":
        return {"data_inicio": d_inicio}, f"Demissão em {formatar_data_br(d_inicio)}"
    if tipo_limpo == "COBERTURA_LOJA":
        payload = {"data_inicio": d_inicio, "data_fim": d_fim, "cod_loja": loja_str}
        return payload, f"Cobertura na loja {loja_str} de {formatar_data_br(d_inicio)} a {formatar_data_br(d_fim)}"
    payload = {"data_inicio": d_inicio, "data_fim": d_fim}
    return payload, f"{tipo_rotulo} de {formatar_data_br(d_inicio)} a {formatar_data_br(d_fim)}"


def criar_solicitacao_intercorrencia(
    tipo: str, rotulo: str, matricula: str, competencia: str, depois: dict[str, Any], rotulo_depois: str, motivo: str
) -> dict[str, Any]:
    """Cria dicionário da SolicitacaoIntercorrencia validado pelo Pydantic.

    Ex.: criar_solicitacao_intercorrencia(...)
    """
    return SolicitacaoIntercorrencia(
        categoria="INTERCORRENCIA", tipo=tipo, tipo_rotulo=rotulo, matricula=matricula,
        competencia=competencia, antes=None, depois=depois, antes_rotulo=None,
        depois_rotulo=rotulo_depois, motivo=motivo,
    ).model_dump(mode="json")


def montar_sucesso_intercorrencia(
    contrato: dict[str, Any], filtros: dict[str, Any], competencia: str, inicio: float
) -> tuple[str, dict[str, Any]]:
    """Monta a tupla de retorno de sucesso com JSON e artifact.

    Ex.: montar_sucesso_intercorrencia(contrato, filtros, "2025-12", time.perf_counter())
    """
    resultado = SolicitacaoIntercorrenciaToolResult(
        situacao="ok", tempo=calcular_tempo_ms(inicio), tabelas=[], competencias=[competencia],
        filtros=filtros, sql=None, solicitacao=contrato,
    )
    return json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False), contrato


@tool(NOME_TOOL_INTERCORRENCIA, response_format="content_and_artifact")
def registrar_intercorrencia(
    tipo: str,
    matricula: str,
    data_inicio: str,
    data_fim: str | None = None,
    cod_loja: str | int | None = None,
    motivo: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Registra uma solicitação de intercorrência de RH para o painel HITL.

    Chame direto, sem `consultar_banco` antes: a ferramenta confere se a matrícula existe na base.
    Se ela devolver que a matrícula não existe, avise o usuário e NÃO abra a solicitação.
    O pedido só vale depois que outra pessoa aprovar na fila de aprovações.

    Args:
        tipo: Tipo da intercorrência (um de: FERIAS, AFASTAMENTO, LICENCA_MATERNIDADE, COBERTURA_LOJA, DEMISSAO).
        matricula: Matrícula do funcionário afetado (ex.: "MATRIC-12").
        data_inicio: Data de início no formato YYYY-MM-DD (ex.: "2025-12-01").
        data_fim: Data de término no formato YYYY-MM-DD (obrigatória para FERIAS, AFASTAMENTO, LICENCA_MATERNIDADE, COBERTURA_LOJA; omitida em DEMISSAO).
        cod_loja: Código da loja atendida (obrigatório e exclusivo para COBERTURA_LOJA).
        motivo: Justificativa obrigatória da intercorrência.
    """
    inicio = time.perf_counter()
    tipo_l = (tipo or "").strip().upper()
    mat_l = (matricula or "").strip().upper()
    motivo_l = (motivo or "").strip()
    d_ini = (data_inicio or "").strip()
    d_fim = (data_fim or "").strip() if data_fim else None
    loja = str(cod_loja).strip() if cod_loja is not None and str(cod_loja).strip() else None

    erro = validar_regras_intercorrencia(tipo_l, tipo, motivo_l, d_ini, data_inicio, d_fim, loja)
    erro = erro or conferir_matricula(mat_l, buscar=buscar_matricula_na_base)
    if erro:
        return montar_retorno_erro_intercorrencia(erro, inicio)

    rotulo = TIPOS_INTERCORRENCIA[tipo_l]
    depois, rotulo_depois = montar_dados_depois_intercorrencia(tipo_l, rotulo, d_ini, d_fim, loja)
    competencia = d_ini[:7]
    solic = criar_solicitacao_intercorrencia(tipo_l, rotulo, mat_l, competencia, depois, rotulo_depois, motivo_l)
    filtros = {"matricula": mat_l, "tipo": tipo_l, "data_inicio": d_ini, "data_fim": d_fim}
    return montar_sucesso_intercorrencia(solic, filtros, competencia, inicio)
