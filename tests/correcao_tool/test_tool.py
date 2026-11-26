import json
import pytest
from langchain_core.messages import ToolMessage

from app.tools.correcao_tool.tool import (
    NOME_TOOL_CORRECAO,
    criar_solicitacao_correcao,
    formatar_rotulo_padrao_correcao,
    montar_retorno_erro_correcao,
    montar_sucesso_correcao,
    normalizar_competencia,
    normalizar_motivo_correcao,
    registrar_solicitacao_correcao,
    resolver_rotulos_correcao,
    validar_competencia_correcao,
    validar_tipo_correcao,
)


def _chamar_correcao(args: dict) -> ToolMessage:
    return registrar_solicitacao_correcao.invoke(
        {"name": NOME_TOOL_CORRECAO, "args": args, "id": "call-corr-1", "type": "tool_call"}
    )


def test_correcao_dados_completos_artifact_igual_ao_contrato():
    mensagem = _chamar_correcao({
        "tipo": "TRANSFERENCIA_LOJA",
        "matricula": "MATRIC-38",
        "competencia": "2025-10",
        "antes": "33",
        "depois": "8",
        "antes_rotulo": "MATRIC-38 na loja 33",
        "depois_rotulo": "MATRIC-38 na loja 8",
        "motivo": "Transferida para a loja 8 em outubro",
    })
    assert isinstance(mensagem, ToolMessage)
    artifact = mensagem.artifact
    assert artifact == {
        "categoria": "CORRECAO",
        "tipo": "TRANSFERENCIA_LOJA",
        "tipo_rotulo": "Transferência de loja",
        "matricula": "MATRIC-38",
        "competencia": "2025-10",
        "antes": "33",
        "depois": "8",
        "antes_rotulo": "MATRIC-38 na loja 33",
        "depois_rotulo": "MATRIC-38 na loja 8",
        "motivo": "Transferida para a loja 8 em outubro",
    }
    content = json.loads(mensagem.content)
    assert content["situacao"] == "ok"
    assert content["sql"] is None
    assert content["competencias"] == ["2025-10"]


def test_correcao_competencia_mm_yyyy_normalizada():
    mensagem = _chamar_correcao({
        "tipo": "TROCA_CARGO",
        "matricula": "MATRIC-10",
        "competencia": "10/2025",
        "antes": "100",
        "depois": "150",
        "motivo": "Promovido a gerente",
    })
    artifact = mensagem.artifact
    assert artifact["competencia"] == "2025-10"
    assert artifact["tipo"] == "TROCA_CARGO"
    assert artifact["tipo_rotulo"] == "Troca de cargo"
    assert artifact["depois"] == "150"
    assert artifact["depois_rotulo"] == "MATRIC-10 no cargo 150"


def test_correcao_tipo_nao_suportado_retorna_erro_e_artifact_vazio():
    mensagem = _chamar_correcao({
        "tipo": "CORRECAO_VENDA",
        "matricula": "MATRIC-12",
        "competencia": "2025-10",
        "depois": "1500",
        "motivo": "Ajuste de valor",
    })
    assert mensagem.artifact == {}
    content = json.loads(mensagem.content)
    assert "não é uma correção pontual suportada" in content["situacao"]
    assert content["solicitacao"] == {}


def test_correcao_data_admissao_e_data_demissao():
    msg_demissao = _chamar_correcao({
        "tipo": "DATA_DEMISSAO",
        "matricula": "MATRIC-01",
        "competencia": "11/2025",
        "depois": "2025-11-15",
        "antes": None,
        "motivo": "Demissão comunicada",
    })
    art = msg_demissao.artifact
    assert art["categoria"] == "CORRECAO"
    assert art["tipo"] == "DATA_DEMISSAO"
    assert art["tipo_rotulo"] == "Data de demissão"
    assert art["antes"] is None
    assert art["depois"] == "2025-11-15"
    assert art["competencia"] == "2025-11"


def test_normalizar_competencia_formatos():
    assert normalizar_competencia("10/2025") == "2025-10"
    assert normalizar_competencia("2025-10") == "2025-10"
    assert normalizar_competencia("2025-10-01") == "2025-10"
    with pytest.raises(ValueError, match="Competência inválida"):
        normalizar_competencia("invalida")


def test_montar_retorno_erro_correcao():
    conteudo_json, artifact = montar_retorno_erro_correcao("Erro teste", 0.0)
    assert artifact == {}
    dados = json.loads(conteudo_json)
    assert dados["situacao"] == "Erro teste"
    assert dados["solicitacao"] == {}


@pytest.mark.parametrize("tipo_limpo,tipo_orig,valido", [
    ("TRANSFERENCIA_LOJA", "TRANSFERENCIA_LOJA", True),
    ("TROCA_CARGO", "troca_cargo", True),
    ("DATA_ADMISSAO", "DATA_ADMISSAO", True),
    ("DATA_DEMISSAO", "DATA_DEMISSAO", True),
    ("INVALIDO", "invalido", False),
])
def test_validar_tipo_correcao(tipo_limpo: str, tipo_orig: str, valido: bool):
    res = validar_tipo_correcao(tipo_limpo, tipo_orig)
    if valido:
        assert res is None
    else:
        assert res is not None
        assert "não é uma correção pontual suportada" in res


def test_validar_competencia_correcao():
    comp, erro = validar_competencia_correcao("10/2025")
    assert comp == "2025-10"
    assert erro is None

    comp_err, erro_msg = validar_competencia_correcao("invalida")
    assert comp_err is None
    assert erro_msg is not None


@pytest.mark.parametrize("tipo,rotulo,mat,val,esperado", [
    ("TRANSFERENCIA_LOJA", "Transferência de loja", "M-1", "8", "M-1 na loja 8"),
    ("TROCA_CARGO", "Troca de cargo", "M-1", "10", "M-1 no cargo 10"),
    ("DATA_ADMISSAO", "Data de admissão", "M-1", "2025-01-01", "Data de admissão 2025-01-01"),
    ("DATA_DEMISSAO", "Data de demissão", "M-1", "2025-10-10", "Data de demissão 2025-10-10"),
    ("OUTRO", "Outro", "M-1", "X", "Outro: X"),
])
def test_formatar_rotulo_padrao_correcao(tipo: str, rotulo: str, mat: str, val: str, esperado: str):
    assert formatar_rotulo_padrao_correcao(tipo, rotulo, mat, val) == esperado


def test_resolver_rotulos_correcao():
    ant, dep = resolver_rotulos_correcao("TRANSFERENCIA_LOJA", "Transferência", "M-1", "3", "8", "Rotulo Ant", "Rotulo Dep")
    assert ant == "Rotulo Ant"
    assert dep == "Rotulo Dep"

    ant_padrao, dep_padrao = resolver_rotulos_correcao("TRANSFERENCIA_LOJA", "Transferência", "M-1", "3", "8", None, None)
    assert ant_padrao == "M-1 na loja 3"
    assert dep_padrao == "M-1 na loja 8"

    ant_none, _ = resolver_rotulos_correcao("TRANSFERENCIA_LOJA", "Transferência", "M-1", None, "8", None, None)
    assert ant_none is None


def test_normalizar_motivo_correcao():
    assert normalizar_motivo_correcao("Mudança solicitada", "Troca de cargo", "M-1") == "Mudança solicitada"
    assert normalizar_motivo_correcao("", "Troca de cargo", "M-1") == "Troca de cargo de M-1"
    assert normalizar_motivo_correcao(None, "Troca de cargo", "M-1") == "Troca de cargo de M-1"


def test_criar_e_montar_sucesso_correcao():
    solic = criar_solicitacao_correcao(
        "TROCA_CARGO", "Troca de cargo", "M-1", "2025-10", "10", "20",
        "M-1 no cargo 10", "M-1 no cargo 20", "Promoção",
    )
    assert solic["categoria"] == "CORRECAO"
    assert solic["antes"] == "10"
    assert solic["depois"] == "20"

    filtros = {"matricula": "M-1", "tipo": "TROCA_CARGO", "competencia": "2025-10", "antes": "10", "depois": "20"}
    conteudo_json, artifact = montar_sucesso_correcao(solic, filtros, "2025-10", 0.0)
    assert artifact == solic
    dados = json.loads(conteudo_json)
    assert dados["situacao"] == "ok"
    assert dados["competencias"] == ["2025-10"]
