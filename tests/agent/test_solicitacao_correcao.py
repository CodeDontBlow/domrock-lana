import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.service import extrair_solicitacao, lana_invoke
from app.agent.trilha import montar_trilha_chat
from app.tools.correcao_tool.tool import NOME_TOOL_CORRECAO, registrar_solicitacao_correcao
from app.tools.intercorrencia_tool.tool import (
    NOME_TOOL_INTERCORRENCIA,
    registrar_intercorrencia,
)
from app.tools.regra_tool.tool import NOME_TOOL_REGRA, registrar_parametros_regra


def test_extrair_solicitacao_pega_o_ultimo_artifact_do_turno_correcao():
    msg1 = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "TRANSFERENCIA_LOJA",
                "matricula": "MATRIC-38",
                "competencia": "2025-10",
                "antes": "33",
                "depois": "8",
                "antes_rotulo": "MATRIC-38 na loja 33",
                "depois_rotulo": "MATRIC-38 na loja 8",
                "motivo": "Transferência para a loja 8 em outubro",
            },
            "id": "c1",
            "type": "tool_call",
        }
    )
    turno = [
        HumanMessage(content="a MATRIC-38 foi transferida da loja 33 para a 8 em outubro"),
        AIMessage(content="", tool_calls=[{"name": NOME_TOOL_CORRECAO, "args": {}, "id": "c1"}]),
        msg1,
        AIMessage(content="Abri o pedido; ele vale depois que um Supervisor aprovar."),
    ]
    solic = extrair_solicitacao(turno)
    assert solic is not None
    assert solic["categoria"] == "CORRECAO"
    assert solic["tipo"] == "TRANSFERENCIA_LOJA"
    assert solic["tipo_rotulo"] == "Transferência de loja"
    assert solic["matricula"] == "MATRIC-38"
    assert solic["antes"] == "33"
    assert solic["depois"] == "8"
    assert solic["competencia"] == "2025-10"
    assert solic["motivo"] == "Transferência para a loja 8 em outubro"


def test_extrair_solicitacao_pega_o_ultimo_artifact_do_turno_intercorrencia():
    msg_interc = registrar_intercorrencia.invoke(
        {
            "name": NOME_TOOL_INTERCORRENCIA,
            "args": {
                "tipo": "FERIAS",
                "matricula": "MATRIC-12",
                "data_inicio": "2025-12-01",
                "data_fim": "2025-12-15",
                "motivo": "Férias programadas",
            },
            "id": "c_int_1",
            "type": "tool_call",
        }
    )
    turno = [
        HumanMessage(content="a MATRIC-12 sai de férias de 01/12 a 15/12"),
        AIMessage(content="", tool_calls=[{"name": NOME_TOOL_INTERCORRENCIA, "args": {}, "id": "c_int_1"}]),
        msg_interc,
        AIMessage(content="Abri a solicitação de férias; precisa de aprovação."),
    ]
    solic = extrair_solicitacao(turno)
    assert solic is not None
    assert solic["categoria"] == "INTERCORRENCIA"
    assert solic["tipo"] == "FERIAS"
    assert solic["tipo_rotulo"] == "Férias"
    assert solic["matricula"] == "MATRIC-12"
    assert solic["competencia"] == "2025-12"
    assert solic["antes"] is None
    assert solic["depois"] == {"data_inicio": "2025-12-01", "data_fim": "2025-12-15"}


def test_extrair_solicitacao_retorna_none_quando_nao_chamou_tool():
    turno = [
        HumanMessage(content="aumente a % do gerente da marca 10"),
        AIMessage(content="Isso é uma campanha de comissionamento e não uma correção pontual."),
    ]
    assert extrair_solicitacao(turno) is None


def test_trilha_registra_passo_de_correcao_sem_sql():
    msg = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "TRANSFERENCIA_LOJA",
                "matricula": "MATRIC-38",
                "competencia": "2025-10",
                "antes": "33",
                "depois": "8",
                "motivo": "Transferência",
            },
            "id": "c2",
            "type": "tool_call",
        }
    )
    mensagens = [
        AIMessage(content="", tool_calls=[{"name": NOME_TOOL_CORRECAO, "args": {}, "id": "c2"}]),
        msg,
    ]
    trilha = montar_trilha_chat(mensagens, "modelo-teste")
    assert trilha is not None
    assert len(trilha["passos"]) == 1
    passo = trilha["passos"][0]
    assert passo["ferramenta"] == NOME_TOOL_CORRECAO
    assert "solicitação de transferência de loja registrada para matric-38" in passo["descricao"].lower()
    assert passo["sql_executado"] is None


def test_trilha_registra_passo_de_intercorrencia_sem_sql():
    msg = registrar_intercorrencia.invoke(
        {
            "name": NOME_TOOL_INTERCORRENCIA,
            "args": {
                "tipo": "FERIAS",
                "matricula": "MATRIC-12",
                "data_inicio": "2025-12-01",
                "data_fim": "2025-12-15",
                "motivo": "Férias",
            },
            "id": "c_int_2",
            "type": "tool_call",
        }
    )
    mensagens = [
        AIMessage(content="", tool_calls=[{"name": NOME_TOOL_INTERCORRENCIA, "args": {}, "id": "c_int_2"}]),
        msg,
    ]
    trilha = montar_trilha_chat(mensagens, "modelo-teste")
    assert trilha is not None
    assert len(trilha["passos"]) == 1
    passo = trilha["passos"][0]
    assert passo["ferramenta"] == NOME_TOOL_INTERCORRENCIA
    assert "solicitação de férias registrada para matric-12" in passo["descricao"].lower()
    assert passo["sql_executado"] is None


def test_requisicao_de_campanha_funciona_normalmente_sem_bloqueio():
    tool_msg_regra = registrar_parametros_regra.invoke(
        {
            "name": NOME_TOOL_REGRA,
            "args": {
                "comando_original": "Campanha Black Friday +1%",
                "explicacao": "Registrando a campanha",
                "pct_acrescimo": 1.0,
                "data_inicio": "2025-11-24",
                "data_fim": "2025-11-30",
            },
            "id": "call-regra",
            "type": "tool_call",
        }
    )
    mensagens = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": NOME_TOOL_REGRA,
                "args": {
                    "comando_original": "Campanha Black Friday +1%",
                    "explicacao": "Registrando",
                    "pct_acrescimo": 1.0,
                },
                "id": "call-regra",
            }],
        ),
        tool_msg_regra,
        AIMessage(content="Campanha registrada no painel com sucesso!"),
    ]
    with patch("app.agent.service._executar_grafo", return_value=mensagens):
        resposta = lana_invoke("chat-regra", "Campanha Black Friday +1%")
        assert resposta["regra"] is not None
        assert resposta["solicitacao"] is None
        assert "Campanha registrada" in resposta["response"]


def test_criterio_1_solicitacao_aprovada_apos_confirmar_na_base():
    tool_msg_corr = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "TRANSFERENCIA_LOJA",
                "matricula": "MATRIC-38",
                "competencia": "2025-10",
                "antes": "33",
                "depois": "8",
                "antes_rotulo": "MATRIC-38 na loja 33",
                "depois_rotulo": "MATRIC-38 na loja 8",
                "motivo": "Transferida da loja 33 para a loja 8 em outubro",
            },
            "id": "call-corr",
            "type": "tool_call",
        }
    )
    mensagens_grafo = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": "consultar_banco",
                "args": {
                    "pergunta": "loja da MATRIC-38 em outubro de 2025",
                    "explicacao": "Consultando vínculo atual da MATRIC-38",
                },
                "id": "call-query",
            }],
        ),
        ToolMessage(
            content=json.dumps({
                "status": "sucesso",
                "dados": [{"matricula": "MATRIC-38", "cod_loja": "33", "date_ref": "2025-10-01"}],
                "tabelas": ["funcionario_loja", "loja"],
                "competencias": ["2025-10"],
                "tempo": 20,
            }),
            name="consultar_banco",
            tool_call_id="call-query",
        ),
        AIMessage(
            content="",
            tool_calls=[{
                "name": NOME_TOOL_CORRECAO,
                "args": {
                    "tipo": "TRANSFERENCIA_LOJA",
                    "matricula": "MATRIC-38",
                    "competencia": "2025-10",
                    "antes": "33",
                    "depois": "8",
                    "motivo": "Transferida da loja 33 para a loja 8 em outubro",
                },
                "id": "call-corr",
            }],
        ),
        tool_msg_corr,
        AIMessage(content="Abri o pedido; ele vale depois que um Supervisor aprovar."),
    ]
    with patch("app.agent.service._executar_grafo", return_value=mensagens_grafo):
        resposta_turno = lana_invoke(
            thread_id="chat-1",
            user_input="a MATRIC-38 foi transferida da loja 33 para a 8 em outubro",
        )
        assert "Abri o pedido; ele vale depois que um Supervisor aprovar" in resposta_turno["response"]
        solicitacao = resposta_turno["solicitacao"]
        assert solicitacao is not None
        assert solicitacao["categoria"] == "CORRECAO"
        assert solicitacao["tipo"] == "TRANSFERENCIA_LOJA"
        assert solicitacao["antes"] == "33"
        assert solicitacao["depois"] == "8"
        assert solicitacao["competencia"] == "2025-10"


def test_criterio_2_matricula_nao_esta_na_loja_avisa_e_nao_abre_pedido():
    mensagens_grafo = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": "consultar_banco",
                "args": {
                    "pergunta": "loja da MATRIC-38 em out/2025",
                    "explicacao": "Consultando vínculo atual da MATRIC-38",
                },
                "id": "call-query-diff",
            }],
        ),
        ToolMessage(
            content=json.dumps({
                "status": "sucesso",
                "dados": [{"matricula": "MATRIC-38", "cod_loja": "3", "date_ref": "2025-10-01"}],
                "tabelas": ["funcionario_loja", "loja"],
                "competencias": ["2025-10"],
                "tempo": 15,
            }),
            name="consultar_banco",
            tool_call_id="call-query-diff",
        ),
        AIMessage(
            content="A matrícula MATRIC-38 está atualmente registrada na loja 3 em outubro de 2025, e não na loja 33. Por isso, não abri o pedido de transferência."
        ),
    ]
    with patch("app.agent.service._executar_grafo", return_value=mensagens_grafo):
        resposta_turno = lana_invoke(
            thread_id="chat-2",
            user_input="a MATRIC-38 foi transferida da loja 33 para a 8 em outubro",
        )
        assert "loja 3" in resposta_turno["response"]
        assert resposta_turno["solicitacao"] is None


def test_criterio_3_pedido_nao_correcao_recusa_e_explica_campanha():
    mensagens_grafo = [
        AIMessage(
            content="Alterar o percentual do gerente da marca 10 não é uma correção cadastral pontual, mas sim uma campanha de comissionamento ou mudança de tabela. Para isso, podemos criar uma nova regra de campanha informando vigência, acréscimo e metas."
        )
    ]
    with patch("app.agent.service._executar_grafo", return_value=mensagens_grafo):
        resposta_turno = lana_invoke(
            thread_id="chat-3",
            user_input="aumente a % do gerente da marca 10",
        )
        assert "campanha" in resposta_turno["response"].lower()
        assert resposta_turno["solicitacao"] is None


def test_hitl_refinamento_atualiza_solicitacao_existente():
    solic_inicial = {
        "categoria": "CORRECAO",
        "tipo": "TRANSFERENCIA_LOJA",
        "tipo_rotulo": "Transferência de loja",
        "matricula": "MATRIC-38",
        "competencia": "2025-10",
        "antes": "33",
        "depois": "8",
        "antes_rotulo": "MATRIC-38 na loja 33",
        "depois_rotulo": "MATRIC-38 na loja 8",
        "motivo": "Transferência inicial",
    }
    tool_msg_refinada = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "TRANSFERENCIA_LOJA",
                "matricula": "MATRIC-38",
                "competencia": "2025-10",
                "antes": "33",
                "depois": "9",
                "antes_rotulo": "MATRIC-38 na loja 33",
                "depois_rotulo": "MATRIC-38 na loja 9",
                "motivo": "Transferência corrigida para loja 9",
            },
            "id": "call-refinada",
            "type": "tool_call",
        }
    )
    mensagens = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": NOME_TOOL_CORRECAO,
                "args": {
                    "tipo": "TRANSFERENCIA_LOJA",
                    "matricula": "MATRIC-38",
                    "competencia": "2025-10",
                    "antes": "33",
                    "depois": "9",
                    "motivo": "Transferência corrigida para loja 9",
                },
                "id": "call-refinada",
            }],
        ),
        tool_msg_refinada,
        AIMessage(content="Atualizei a solicitação no painel para a loja 9; ela vale após aprovação de um Supervisor."),
    ]
    with patch("app.agent.service._executar_grafo", return_value=mensagens):
        resposta = lana_invoke(
            thread_id="chat-hitl",
            user_input="mude para a loja 9",
            solicitacao=solic_inicial,
        )
        assert resposta["solicitacao"] is not None
        assert resposta["solicitacao"]["categoria"] == "CORRECAO"
        assert resposta["solicitacao"]["depois"] == "9"
        assert resposta["solicitacao"]["depois_rotulo"] == "MATRIC-38 na loja 9"
