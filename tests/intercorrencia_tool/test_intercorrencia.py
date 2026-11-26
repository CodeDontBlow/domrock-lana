import json
import pytest
from langchain_core.messages import ToolMessage

from app.tools.intercorrencia_tool.tool import (
    NOME_TOOL_INTERCORRENCIA,
    criar_solicitacao_intercorrencia,
    formatar_data_br,
    montar_dados_depois_intercorrencia,
    montar_retorno_erro_intercorrencia,
    montar_sucesso_intercorrencia,
    registrar_intercorrencia,
    validar_data_inicio_intercorrencia,
    validar_datas_intercorrencia,
    validar_loja_intercorrencia,
    validar_motivo_intercorrencia,
    validar_regras_intercorrencia,
    validar_tipo_intercorrencia,
)


def _chamar_intercorrencia(args: dict) -> ToolMessage:
    return registrar_intercorrencia.invoke(
        {"name": NOME_TOOL_INTERCORRENCIA, "args": args, "id": "call-interc-1", "type": "tool_call"}
    )


def test_intercorrencia_cada_tipo():
    # 1. FERIAS
    msg_ferias = _chamar_intercorrencia({
        "tipo": "FERIAS",
        "matricula": "MATRIC-12",
        "data_inicio": "2025-12-01",
        "data_fim": "2025-12-15",
        "motivo": "Férias programadas",
    })
    art_ferias = msg_ferias.artifact
    assert art_ferias == {
        "categoria": "INTERCORRENCIA",
        "tipo": "FERIAS",
        "tipo_rotulo": "Férias",
        "matricula": "MATRIC-12",
        "competencia": "2025-12",
        "antes": None,
        "depois": {"data_inicio": "2025-12-01", "data_fim": "2025-12-15"},
        "antes_rotulo": None,
        "depois_rotulo": "Férias de 01/12/2025 a 15/12/2025",
        "motivo": "Férias programadas",
    }

    # 2. AFASTAMENTO
    msg_afast = _chamar_intercorrencia({
        "tipo": "AFASTAMENTO",
        "matricula": "MATRIC-14",
        "data_inicio": "2025-10-05",
        "data_fim": "2025-10-20",
        "motivo": "Atestado médico",
    })
    assert msg_afast.artifact["tipo"] == "AFASTAMENTO"
    assert msg_afast.artifact["tipo_rotulo"] == "Afastamento"
    assert msg_afast.artifact["depois_rotulo"] == "Afastamento de 05/10/2025 a 20/10/2025"

    # 3. LICENCA_MATERNIDADE
    msg_mat = _chamar_intercorrencia({
        "tipo": "LICENCA_MATERNIDADE",
        "matricula": "MATRIC-20",
        "data_inicio": "2025-10-01",
        "data_fim": "2026-02-01",
        "motivo": "Licença maternidade",
    })
    assert msg_mat.artifact["tipo"] == "LICENCA_MATERNIDADE"
    assert msg_mat.artifact["tipo_rotulo"] == "Licença-maternidade"

    # 4. COBERTURA_LOJA
    msg_cob = _chamar_intercorrencia({
        "tipo": "COBERTURA_LOJA",
        "matricula": "MATRIC-30",
        "data_inicio": "2025-11-01",
        "data_fim": "2025-11-10",
        "cod_loja": "8",
        "motivo": "Cobertura temporária",
    })
    assert msg_cob.artifact["tipo"] == "COBERTURA_LOJA"
    assert msg_cob.artifact["tipo_rotulo"] == "Cobertura de loja"
    assert msg_cob.artifact["depois"] == {
        "data_inicio": "2025-11-01",
        "data_fim": "2025-11-10",
        "cod_loja": "8",
    }
    assert "8" in msg_cob.artifact["depois_rotulo"]

    # 5. DEMISSAO
    msg_dem = _chamar_intercorrencia({
        "tipo": "DEMISSAO",
        "matricula": "MATRIC-99",
        "data_inicio": "2025-11-15",
        "motivo": "Desligamento",
    })
    assert msg_dem.artifact["tipo"] == "DEMISSAO"
    assert msg_dem.artifact["tipo_rotulo"] == "Demissão"
    assert msg_dem.artifact["depois"] == {"data_inicio": "2025-11-15"}
    assert msg_dem.artifact["depois_rotulo"] == "Demissão em 15/11/2025"


def test_intercorrencia_data_final_antes_da_inicial():
    msg = _chamar_intercorrencia({
        "tipo": "FERIAS",
        "matricula": "MATRIC-12",
        "data_inicio": "2025-12-15",
        "data_fim": "2025-12-01",
        "motivo": "Férias",
    })
    assert msg.artifact == {}
    content = json.loads(msg.content)
    assert content["situacao"] == "A data final precisa ser igual ou posterior à inicial"


def test_intercorrencia_cobertura_sem_loja():
    msg = _chamar_intercorrencia({
        "tipo": "COBERTURA_LOJA",
        "matricula": "MATRIC-30",
        "data_inicio": "2025-11-01",
        "data_fim": "2025-11-10",
        "cod_loja": None,
        "motivo": "Cobertura",
    })
    assert msg.artifact == {}
    content = json.loads(msg.content)
    assert "cod_loja" in content["situacao"].lower() or "loja" in content["situacao"].lower()


def test_intercorrencia_loja_em_outro_tipo():
    msg = _chamar_intercorrencia({
        "tipo": "FERIAS",
        "matricula": "MATRIC-12",
        "data_inicio": "2025-12-01",
        "data_fim": "2025-12-15",
        "cod_loja": "8",
        "motivo": "Férias",
    })
    assert msg.artifact == {}
    content = json.loads(msg.content)
    assert "loja" in content["situacao"].lower()


def test_intercorrencia_demissao_sem_data_fim():
    msg = _chamar_intercorrencia({
        "tipo": "DEMISSAO",
        "matricula": "MATRIC-99",
        "data_inicio": "2025-11-15",
        "data_fim": None,
        "motivo": "Desligamento",
    })
    assert msg.artifact != {}
    assert "data_fim" not in msg.artifact["depois"]

    # Se data_fim diferente de data_inicio, recusa
    msg_err = _chamar_intercorrencia({
        "tipo": "DEMISSAO",
        "matricula": "MATRIC-99",
        "data_inicio": "2025-11-15",
        "data_fim": "2025-11-20",
        "motivo": "Desligamento",
    })
    assert msg_err.artifact == {}


def test_intercorrencia_motivo_vazio():
    msg1 = _chamar_intercorrencia({
        "tipo": "FERIAS",
        "matricula": "MATRIC-12",
        "data_inicio": "2025-12-01",
        "data_fim": "2025-12-15",
        "motivo": "",
    })
    assert msg1.artifact == {}
    content = json.loads(msg1.content)
    assert "motivo" in content["situacao"].lower()

    msg2 = _chamar_intercorrencia({
        "tipo": "FERIAS",
        "matricula": "MATRIC-12",
        "data_inicio": "2025-12-01",
        "data_fim": "2025-12-15",
        "motivo": None,
    })
    assert msg2.artifact == {}


def test_formatar_data_br():
    assert formatar_data_br("2025-12-01") == "01/12/2025"
    assert formatar_data_br("invalida") == "invalida"


def test_montar_retorno_erro_intercorrencia():
    conteudo_json, artifact = montar_retorno_erro_intercorrencia("Falha de teste", 0.0)
    assert artifact == {}
    dados = json.loads(conteudo_json)
    assert dados["situacao"] == "Falha de teste"
    assert dados["solicitacao"] == {}


@pytest.mark.parametrize("motivo,esperado", [
    ("", "Motivo é obrigatório para registrar intercorrência"),
    ("   ", "Motivo é obrigatório para registrar intercorrência"),
    ("Férias anuais", None),
])
def test_validar_motivo_intercorrencia(motivo: str, esperado: str | None):
    assert validar_motivo_intercorrencia(motivo.strip()) == esperado


@pytest.mark.parametrize("tipo_limpo,tipo_orig,valido", [
    ("FERIAS", "ferias", True),
    ("DEMISSAO", "DEMISSAO", True),
    ("OUTRO", "outro", False),
])
def test_validar_tipo_intercorrencia(tipo_limpo: str, tipo_orig: str, valido: bool):
    resultado = validar_tipo_intercorrencia(tipo_limpo, tipo_orig)
    if valido:
        assert resultado is None
    else:
        assert resultado is not None
        assert "não suportado" in resultado


@pytest.mark.parametrize("d_ini,esperado_valido", [
    ("2025-12-01", True),
    ("2025-12", True),
    ("20251201", False),
    ("2025", False),
])
def test_validar_data_inicio_intercorrencia(d_ini: str, esperado_valido: bool):
    res = validar_data_inicio_intercorrencia(d_ini, d_ini)
    assert (res is None) == esperado_valido


@pytest.mark.parametrize("tipo,rotulo,d_ini,d_fim,esperado_erro", [
    ("DEMISSAO", "Demissão", "2025-10-01", None, None),
    ("DEMISSAO", "Demissão", "2025-10-01", "2025-10-01", None),
    ("DEMISSAO", "Demissão", "2025-10-01", "2025-10-02", "Demissão não leva data final diferente da data de demissão"),
    ("FERIAS", "Férias", "2025-10-01", None, "Data final é obrigatória para férias"),
    ("FERIAS", "Férias", "2025-10-10", "2025-10-01", "A data final precisa ser igual ou posterior à inicial"),
    ("FERIAS", "Férias", "2025-10-01", "2025-10-10", None),
])
def test_validar_datas_intercorrencia(tipo: str, rotulo: str, d_ini: str, d_fim: str | None, esperado_erro: str | None):
    assert validar_datas_intercorrencia(tipo, rotulo, d_ini, d_fim) == esperado_erro


@pytest.mark.parametrize("tipo,rotulo,loja,esperado_erro", [
    ("COBERTURA_LOJA", "Cobertura de loja", None, "Código da loja (cod_loja) é obrigatório para cobertura de loja"),
    ("COBERTURA_LOJA", "Cobertura de loja", "8", None),
    ("DEMISSAO", "Demissão", "8", "Código da loja não deve ser informado para demissão"),
    ("FERIAS", "Férias", "8", "Código da loja não deve ser informado para férias"),
    ("FERIAS", "Férias", None, None),
])
def test_validar_loja_intercorrencia(tipo: str, rotulo: str, loja: str | None, esperado_erro: str | None):
    assert validar_loja_intercorrencia(tipo, rotulo, loja) == esperado_erro


def test_validar_regras_intercorrencia():
    assert "Motivo" in (validar_regras_intercorrencia("FERIAS", "FERIAS", "", "2025-12-01", "2025-12-01", "2025-12-10", None) or "")
    assert validar_regras_intercorrencia("FERIAS", "FERIAS", "Férias", "2025-12-01", "2025-12-01", "2025-12-10", None) is None


def test_montar_dados_depois_intercorrencia():
    dep_dem, rot_dem = montar_dados_depois_intercorrencia("DEMISSAO", "Demissão", "2025-11-15", None, None)
    assert dep_dem == {"data_inicio": "2025-11-15"}
    assert "Demissão em 15/11/2025" in rot_dem

    dep_cob, rot_cob = montar_dados_depois_intercorrencia("COBERTURA_LOJA", "Cobertura de loja", "2025-11-01", "2025-11-10", "8")
    assert dep_cob == {"data_inicio": "2025-11-01", "data_fim": "2025-11-10", "cod_loja": "8"}
    assert "Cobertura na loja 8" in rot_cob

    dep_fer, rot_fer = montar_dados_depois_intercorrencia("FERIAS", "Férias", "2025-12-01", "2025-12-15", None)
    assert dep_fer == {"data_inicio": "2025-12-01", "data_fim": "2025-12-15"}
    assert rot_fer == "Férias de 01/12/2025 a 15/12/2025"


def test_criar_e_montar_sucesso_intercorrencia():
    solic = criar_solicitacao_intercorrencia(
        "FERIAS", "Férias", "MATRIC-1", "2025-12",
        {"data_inicio": "2025-12-01", "data_fim": "2025-12-15"},
        "Férias de 01/12/2025 a 15/12/2025", "Motivo férias",
    )
    assert solic["categoria"] == "INTERCORRENCIA"
    assert solic["matricula"] == "MATRIC-1"

    filtros = {"matricula": "MATRIC-1", "tipo": "FERIAS", "data_inicio": "2025-12-01", "data_fim": "2025-12-15"}
    conteudo_json, artifact = montar_sucesso_intercorrencia(solic, filtros, "2025-12", 0.0)
    assert artifact == solic
    dados = json.loads(conteudo_json)
    assert dados["situacao"] == "ok"
    assert dados["competencias"] == ["2025-12"]
