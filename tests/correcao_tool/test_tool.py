import json
from unittest.mock import MagicMock

from langchain_core.messages import ToolMessage

from app.tools.correcao_tool.tool import NOME_TOOL_CORRECAO, registrar_solicitacao_correcao
from app.tools.query_tool.dtos import QueryResponseBody


def _chamar_correcao(args: dict) -> ToolMessage:
    return registrar_solicitacao_correcao.invoke(
        {"name": NOME_TOOL_CORRECAO, "args": args, "id": "call-corr-1", "type": "tool_call"}
    )


def test_tool_devolve_resultado_para_llm_e_solicitacao_como_artifact():
    mensagem = _chamar_correcao({
        "tipo": "Transferência de loja",
        "matricula": "MATRIC-38",
        "competencia": "out/2025",
        "antes": "loja 5",
        "depois": "loja 8",
        "motivo": "Transferida de loja em outubro",
    })
    assert isinstance(mensagem, ToolMessage)
    assert mensagem.name == NOME_TOOL_CORRECAO

    artifact = mensagem.artifact
    assert artifact["tipo"] == "Transferência de loja"
    assert artifact["tipo_alteracao"] == "TRANSFERENCIA_LOJA"
    assert artifact["matricula"] == "MATRIC-38"
    assert artifact["competencia"] == "10/2025"
    assert artifact["competencia_iso"] == "2025-10"
    assert artifact["antes"] == "loja 5"
    assert artifact["depois"] == "loja 8"
    assert artifact["valor_antes"] == "5"
    assert artifact["valor_depois"] == "8"
    assert artifact["motivo"] == "Transferida de loja em outubro"
    assert artifact["origem"] == "LANA"
    assert artifact["status"] == "PENDENTE_APROVACAO"
    assert "UPDATE funcionario_loja" in artifact["sql"]

    content = json.loads(mensagem.content)
    assert content["situacao"] == "ok"
    assert "funcionario_loja" in content["tabelas"]
    assert "10/2025" in content["competencias"]
    assert content["solicitacao"] == artifact


def test_tool_gera_motivo_sugerido_quando_omitido():
    mensagem = _chamar_correcao({
        "tipo": "Transferência de loja",
        "matricula": "MATRIC-38",
        "competencia": "10/2025",
        "antes": "loja 5",
        "depois": "loja 8",
    })
    artifact = mensagem.artifact
    assert "alteração" in artifact["motivo"]


def test_tool_aceita_outros_tipos_amigaveis():
    mensagem = _chamar_correcao({
        "tipo": "Mudança de cargo",
        "matricula": "MATRIC-10",
        "competencia": "11/2025",
        "antes": "100",
        "depois": "150",
        "motivo": "Promovido a gerente",
    })
    artifact = mensagem.artifact
    assert artifact["tipo"] == "Mudança de cargo"
    assert artifact["tipo_alteracao"] == "TROCA_CARGO"
    assert "UPDATE funcionario_cargo" in artifact["sql"]


def test_tool_reutiliza_query_tool_quando_antes_vazio(monkeypatch):
    mock_retorno = QueryResponseBody(
        status="sucesso",
        dados=[{"cod_loja": "31", "descr_loja": "LOJA-31"}],
        tempo=10,
        situacao="ok",
        mensagem="ok",
        tabelas=["loja"],
        competencias=["2025-10"],
        filtros=None,
        registros=1,
        sql=None,
    )
    monkeypatch.setattr(
        "app.tools.correcao_tool.consulta.executar_consulta_banco",
        MagicMock(return_value=mock_retorno),
    )

    mensagem = _chamar_correcao({
        "tipo": "Transferência de loja",
        "matricula": "MATRIC-91",
        "competencia": "10/2025",
        "antes": "",
        "depois": "loja 8",
    })
    artifact = mensagem.artifact
    assert artifact["antes"] == "loja 31"
    assert artifact["valor_antes"] == "31"
    assert artifact["depois"] == "loja 8"
    assert "loja_id = (SELECT id FROM loja WHERE cod_loja = '31')" in artifact["sql"]


def test_tool_corrige_id_surrogate_para_cod_loja_negocio(monkeypatch):
    mock_retorno = QueryResponseBody(
        status="sucesso",
        dados=[{"loja_id": 9, "cod_loja": "76", "descr_loja": "LOJA-76"}],
        tempo=10,
        situacao="ok",
        mensagem="ok",
        tabelas=["loja", "funcionario_loja"],
        competencias=["2025-07"],
        filtros=None,
        registros=1,
        sql=None,
    )
    monkeypatch.setattr(
        "app.tools.correcao_tool.consulta.executar_consulta_banco",
        MagicMock(return_value=mock_retorno),
    )

    mensagem = _chamar_correcao({
        "tipo": "Transferência de loja",
        "matricula": "MATRIC-33",
        "competencia": "10/2025",
        "antes": "MATRIC-33 na loja 9",
        "depois": "MATRIC-33 na loja 8",
    })
    artifact = mensagem.artifact
    assert artifact["valor_antes"] == "76"
    assert "76" in artifact["antes"]
    assert artifact["valor_depois"] == "8"
    assert "loja_id = (SELECT id FROM loja WHERE cod_loja = '76')" in artifact["sql"]
