import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.service import extrair_solicitacao, lana_invoke
from app.agent.trilha import montar_trilha_chat
from app.tools.correcao_tool.tool import NOME_TOOL_CORRECAO, registrar_solicitacao_correcao
from app.tools.regra_tool.tool import NOME_TOOL_REGRA, registrar_parametros_regra


def test_extrair_solicitacao_pega_o_ultimo_artifact_do_turno():
    msg1 = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "Transferência de loja",
                "matricula": "MATRIC-38",
                "competencia": "10/2025",
                "antes": "loja 5",
                "depois": "loja 8",
                "motivo": "Transferência",
            },
            "id": "c1",
            "type": "tool_call",
        }
    )
    turno = [
        HumanMessage(content="a MATRIC-38 foi transferida da loja 5 para a loja 8 em outubro"),
        AIMessage(content="", tool_calls=[{"name": NOME_TOOL_CORRECAO, "args": {}, "id": "c1"}]),
        msg1,
        AIMessage(content="Abri o pedido; ele vale depois que um Supervisor aprovar."),
    ]
    solic = extrair_solicitacao(turno)
    assert solic is not None
    assert solic["matricula"] == "MATRIC-38"
    assert solic["antes"] == "loja 5"
    assert solic["depois"] == "loja 8"
    assert solic["competencia"] == "10/2025"
    assert solic["origem"] == "LANA"
    assert solic["status"] == "PENDENTE_APROVACAO"
    assert "UPDATE funcionario_loja" in solic["sql"]


def test_extrair_solicitacao_retorna_none_quando_nao_chamou_tool():
    turno = [
        HumanMessage(content="aumente a % do gerente da marca 10"),
        AIMessage(content="Isso é uma campanha de comissionamento e não uma correção pontual."),
    ]
    assert extrair_solicitacao(turno) is None


def test_trilha_registra_passo_de_correcao():
    msg = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "Transferência de loja",
                "matricula": "MATRIC-38",
                "competencia": "10/2025",
                "antes": "loja 5",
                "depois": "loja 8",
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
    assert "UPDATE funcionario_loja" in passo["sql_executado"]


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
    """Dado Gabriela escreve 'a MATRIC-38 foi transferida da loja 5 para a loja 8 em outubro',

    Quando a Lana responde,
    Então devolve a solicitação com antes = loja 5, depois = loja 8, competência 10/2025,
    origem LANA, e diz 'Abri o pedido; ele vale depois que um Supervisor aprovar'.
    """
    tool_msg_corr = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "Transferência de loja",
                "matricula": "MATRIC-38",
                "competencia": "10/2025",
                "antes": "loja 5",
                "depois": "loja 8",
                "motivo": "Transferida da loja 5 para a loja 8 em outubro",
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
                "dados": [{"matricula": "MATRIC-38", "cod_loja": "5", "date_ref": "2025-10-01"}],
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
                    "tipo": "Transferência de loja",
                    "matricula": "MATRIC-38",
                    "competencia": "10/2025",
                    "antes": "loja 5",
                    "depois": "loja 8",
                    "motivo": "Transferida da loja 5 para a loja 8 em outubro",
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
            user_input="a MATRIC-38 foi transferida da loja 5 para a loja 8 em outubro",
        )
        assert "Abri o pedido; ele vale depois que um Supervisor aprovar" in resposta_turno["response"]
        solicitacao = resposta_turno["solicitacao"]
        assert solicitacao is not None
        assert solicitacao["antes"] == "loja 5"
        assert solicitacao["depois"] == "loja 8"
        assert solicitacao["competencia"] == "10/2025"
        assert solicitacao["origem"] == "LANA"
        assert solicitacao["status"] == "PENDENTE_APROVACAO"
        assert "UPDATE funcionario_loja" in solicitacao["sql"]


def test_criterio_2_matricula_nao_esta_na_loja_avisa_e_nao_abre_pedido():
    """Dado a matrícula não está na loja 5 naquele mês,

    Então a Lana avisa a loja atual e não abre o pedido.
    """
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
            content="A matrícula MATRIC-38 está atualmente registrada na loja 3 em outubro de 2025, e não na loja 5. Por isso, não abri o pedido de transferência."
        ),
    ]
    with patch("app.agent.service._executar_grafo", return_value=mensagens_grafo):
        resposta_turno = lana_invoke(
            thread_id="chat-2",
            user_input="a MATRIC-38 foi transferida da loja 5 para a loja 8 em outubro",
        )
        assert "loja 3" in resposta_turno["response"]
        assert resposta_turno["solicitacao"] is None


def test_criterio_3_pedido_nao_correcao_recusa_e_explica_campanha():
    """Dado 'aumente a % do gerente da marca 10',

    Então a Lana não abre solicitação e explica que isso é uma campanha.
    """
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
    """No fluxo HITL, o usuário pode pedir para alterar a solicitação aberta no chat,
    e a Lana chama novamente a tool atualizando apenas o campo solicitado."""
    solic_inicial = {
        "tipo": "Transferência de loja",
        "matricula": "MATRIC-38",
        "competencia": "10/2025",
        "antes": "MATRIC-38 na loja 5",
        "depois": "MATRIC-38 na loja 8",
        "motivo": "Transferência inicial",
    }
    tool_msg_refinada = registrar_solicitacao_correcao.invoke(
        {
            "name": NOME_TOOL_CORRECAO,
            "args": {
                "tipo": "Transferência de loja",
                "matricula": "MATRIC-38",
                "competencia": "10/2025",
                "antes": "MATRIC-38 na loja 5",
                "depois": "MATRIC-38 na loja 9",
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
                    "tipo": "Transferência de loja",
                    "matricula": "MATRIC-38",
                    "competencia": "10/2025",
                    "antes": "MATRIC-38 na loja 5",
                    "depois": "MATRIC-38 na loja 9",
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
        assert resposta["solicitacao"]["depois"] == "MATRIC-38 na loja 9"
        assert resposta["solicitacao"]["valor_depois"] == "9"
