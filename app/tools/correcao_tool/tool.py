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
    """Registra uma solicitação de correção/alteração na base de dados para o painel HITL (Human-In-The-Loop).

    Use SOMENTE quando o usuário solicitar alteração cadastral ou correção na base de dados,
    e após confirmar na base (via `consultar_banco`) que a matrícula existe e que os dados atuais
    daquela competência foram checados. Se os dados que você checar não coincidirem com o banco, avise o usuário e
    NÃO abra solicitação.
    NUNCA use esta ferramenta para regras de campanhas de comissionamento (use registrar_parametros_regra).

    FLUXO HITL (Human-In-The-Loop) E REFINAMENTO:
    - Esta ferramenta NÃO executa o SQL no banco. Ela gera uma proposta de solicitação que é exibida
      no componente HITL no final da sua mensagem. A solicitação NÃO é enviada imediatamente aos supervisores: ela permanece
      aguardando o usuário revisar e clicar no botão para enviar.
    - Se o usuário pedir para alterar qualquer parâmetro da solicitação pelo chat (ex: 'mude a loja para 8',
      'troque o motivo', 'mude para outubro'), chame esta ferramenta NOVAMENTE com TODOS os parâmetros conhecidos,
      atualizando apenas o que o usuário pediu para mudar. O componente HITL no chat será atualizado com os novos valores.

    PADRÃO DE FORMATAÇÃO DE 'antes' E 'depois':
    - AMBOS os campos DEVEM INCLUIR A MATRÍCULA do funcionário e possuir comprimento textual similar/simétrico
      para que a comparação visual fique balanceada e legível no painel.
    - Exemplos recomendados:
        * Transferência de loja: antes="MATRIC-38 na loja 5", depois="MATRIC-38 na loja 8"
        * Mudança de cargo: antes="MATRIC-10 como Vendedor", depois="MATRIC-10 como Gerente"
        * Correção de vendas: antes="MATRIC-12 com R$ 1.000,00", depois="MATRIC-12 com R$ 1.500,00"
        * Datas/vigência: antes="MATRIC-302 em 09/2025", depois="MATRIC-302 em 10/2025"

    Args:
        tipo: Tipo da alteração com nome amigável (ex.: "Transferência de loja", "Mudança de cargo",
            "Data de demissão", "Data de admissão", "Correção de venda", "Exclusão", "Atualização").
        matricula: Matrícula do funcionário afetado (ex.: "MATRIC-38").
        competencia: Mês/ano da competência afetada no formato MM/yyyy (ex.: "10/2025" ou "11/2025").
        antes: Estado anterior incluindo a matrícula do funcionário (ex.: "MATRIC-38 na loja 5").
        depois: Estado novo solicitado incluindo a matrícula com comprimento similar ao 'antes' (ex.: "MATRIC-38 na loja 8").
        motivo: Motivo ou justificativa da alteração. Faça o motivo conter o máximo de informaçõe possíveis
        com o mínimo de linhas.
        sql: Código SQL de alteração gerado para avaliação dos supervisores.
    """
    inicio = time.perf_counter()
    try:
        valor_antes = (antes or "").strip()
        cod_antes = extrair_codigo_ou_valor(valor_antes or antes)
        cod_depois = extrair_codigo_ou_valor(depois)

        if matricula:
            try:
                dados_consulta = consultar_dados_funcionario_no_banco(matricula, competencia)
                registros = dados_consulta.get("dados") or []
                if registros and isinstance(registros, list) and len(registros) > 0:
                    item = registros[0]
                    if not valor_antes:
                        if "cod_loja" in item:
                            valor_antes = f"loja {item['cod_loja']}"
                            cod_antes = str(item["cod_loja"])
                        elif "descr_loja" in item:
                            valor_antes = str(item["descr_loja"])
                            cod_antes = extrair_codigo_ou_valor(valor_antes)
                        elif "cod_cargo" in item:
                            valor_antes = f"cargo {item['cod_cargo']}"
                            cod_antes = str(item["cod_cargo"])
                        elif "descr_cargo" in item:
                            valor_antes = str(item["descr_cargo"])
                            cod_antes = extrair_codigo_ou_valor(valor_antes)
                    else:
                        # Proteção contra confusão de ID surrogate do banco vs cod_loja de negócio
                        loja_id_banco = str(item.get("loja_id") or item.get("id") or "")
                        cod_loja_banco = str(item.get("cod_loja") or "")
                        if cod_loja_banco and cod_antes == loja_id_banco and cod_antes != cod_loja_banco:
                            cod_antes = cod_loja_banco
                            if f"loja {loja_id_banco}" in valor_antes:
                                valor_antes = valor_antes.replace(f"loja {loja_id_banco}", f"loja {cod_loja_banco}")
                            elif loja_id_banco in valor_antes:
                                valor_antes = valor_antes.replace(loja_id_banco, cod_loja_banco)

                        cargo_id_banco = str(item.get("cargo_id") or "")
                        cod_cargo_banco = str(item.get("cod_cargo") or "")
                        if cod_cargo_banco and cod_antes == cargo_id_banco and cod_antes != cod_cargo_banco:
                            cod_antes = cod_cargo_banco
                            if f"cargo {cargo_id_banco}" in valor_antes:
                                valor_antes = valor_antes.replace(f"cargo {cargo_id_banco}", f"cargo {cod_cargo_banco}")
                            elif cargo_id_banco in valor_antes:
                                valor_antes = valor_antes.replace(cargo_id_banco, cod_cargo_banco)
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
