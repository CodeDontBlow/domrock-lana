import json
import time
from typing import Any

from langchain_core.tools import tool

from app.tools.correcao_tool.consulta import consultar_dados_funcionario_no_banco
from app.tools.correcao_tool.dtos import (
    SolicitacaoCorrecao,
    SolicitacaoCorrecaoToolResult,
    codigo_backend_tipo,
    normalizar_tipo,
)
from app.tools.correcao_tool.gerador_sql import (
    converter_competencia_para_data,
    extrair_codigo_ou_valor,
    gerar_sql_correcao,
)
from app.tools.dtos import calcular_tempo_ms

NOME_TOOL_CORRECAO = "registrar_solicitacao_correcao"


@tool(NOME_TOOL_CORRECAO, response_format="content_and_artifact")
def registrar_solicitacao_correcao(
    tipo: str,
    matricula: str,
    competencia: str,
    antes: str,
    depois: str,
    motivo: str | None = None,
    sql: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Registra uma solicitação de correção pontual na base de dados para aprovação dos supervisores.

    Use SOMENTE quando o usuário solicitar expressamente uma alteração ou correção na base de dados,
    e após confirmar na base (via `consultar_banco`) que a matrícula existe e que o valor anterior
    informado coincide com os dados atuais daquela competência.
    NUNCA chame esta ferramenta para requisições de campanhas, simulações ou consultas gerais.
    O código SQL de alteração NÃO será executado pelo agente, mas sim submetido para avaliação
    e aprovação da equipe de supervisores.

    Args:
        tipo: Tipo da alteração com nome amigável (ex.: "Transferência de loja", "Mudança de cargo",
            "Data de demissão", "Data de admissão", "Correção de venda", "Exclusão", "Atualização").
        matricula: Matrícula do funcionário afetado (ex.: "MATRIC-38").
        competencia: Mês/ano da competência afetada no formato MM/yyyy (ex.: "10/2025" ou "11/2025").
        antes: Valor anterior confirmado na base (ex.: "loja 5" ou "5").
        depois: Valor novo solicitado (ex.: "loja 8" ou "8").
        motivo: Opcional. Motivo ou sugestão de justificativa gerada pelo agente ou informada pelo usuário.
        sql: Opcional. Código SQL de alteração gerado para o banco PostgreSQL. Se omitido, a ferramenta
            gerará automaticamente o SQL apropriado.
    """
    inicio = time.perf_counter()
    try:
        valor_antes = (antes or "").strip()
        if not valor_antes and matricula and competencia:
            try:
                dados_consulta = consultar_dados_funcionario_no_banco(matricula, competencia)
                registros = dados_consulta.get("dados") or []
                if registros and isinstance(registros, list) and len(registros) > 0:
                    item = registros[0]
                    if "cod_loja" in item:
                        valor_antes = f"loja {item['cod_loja']}"
                    elif "descr_loja" in item:
                        valor_antes = item["descr_loja"]
                    elif "cod_cargo" in item:
                        valor_antes = f"cargo {item['cod_cargo']}"
                    elif "descr_cargo" in item:
                        valor_antes = item["descr_cargo"]
            except Exception:
                pass

        sql_gerado, tabelas = gerar_sql_correcao(
            tipo=tipo,
            matricula=matricula,
            competencia=competencia,
            antes=valor_antes or antes,
            depois=depois,
            sql_customizado=sql,
        )
        _, comp_iso, comp_mm_yyyy = converter_competencia_para_data(competencia)
        tipo_amigavel = normalizar_tipo(tipo)
        tipo_codigo = codigo_backend_tipo(tipo)
        matricula_limpa = matricula.strip().upper()
        cod_antes = extrair_codigo_ou_valor(valor_antes or antes)
        cod_depois = extrair_codigo_ou_valor(depois)

        motivo_final = (motivo or "").strip()
        if not motivo_final:
            motivo_final = (
                f"{tipo_amigavel} de {matricula_limpa}: alteração de "
                f"{(valor_antes or antes).strip()} para {depois.strip()} em {comp_mm_yyyy}"
            )

        solicitacao = SolicitacaoCorrecao(
            tipo=tipo_amigavel,
            tipo_alteracao=tipo_codigo,
            matricula=matricula_limpa,
            competencia=comp_mm_yyyy,
            competencia_iso=comp_iso,
            antes=(valor_antes or antes).strip(),
            depois=depois.strip(),
            valor_antes=cod_antes,
            valor_depois=cod_depois,
            motivo=motivo_final,
            origem="LANA",
            status="PENDENTE_APROVACAO",
            sql=sql_gerado,
        )
        contrato = solicitacao.model_dump(mode="json")
        resultado = SolicitacaoCorrecaoToolResult(
            situacao="ok",
            tempo=calcular_tempo_ms(inicio),
            tabelas=tabelas,
            competencias=[comp_mm_yyyy],
            filtros={
                "matricula": matricula_limpa,
                "competencia": comp_mm_yyyy,
                "antes": (valor_antes or antes).strip(),
                "depois": depois.strip(),
            },
            sql=sql_gerado,
            solicitacao=contrato,
        )
        return json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False), contrato
    except Exception as e:
        resultado = SolicitacaoCorrecaoToolResult(
            situacao=f"erro ao registrar solicitação de correção: {e}",
            tempo=calcular_tempo_ms(inicio),
            competencias=[],
            filtros=None,
            tabelas=None,
            registros=None,
            sql=None,
            solicitacao={},
        )
        return json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False), {}
