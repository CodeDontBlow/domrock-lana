import pytest

from app.tools.correcao_tool.dtos import TipoCorrecao, normalizar_tipo
from app.tools.correcao_tool.gerador_sql import (
    converter_competencia_para_data,
    extrair_codigo_ou_valor,
    gerar_sql_correcao,
)


def test_converter_competencia_formatos_variados():
    assert converter_competencia_para_data("out/2025") == ("2025-10-01", "2025-10", "10/2025")
    assert converter_competencia_para_data("10/2025") == ("2025-10-01", "2025-10", "10/2025")
    assert converter_competencia_para_data("2025-10") == ("2025-10-01", "2025-10", "10/2025")
    assert converter_competencia_para_data("outubro de 2025") == ("2025-10-01", "2025-10", "10/2025")
    assert converter_competencia_para_data("nov/2025") == ("2025-11-01", "2025-11", "11/2025")
    assert converter_competencia_para_data("11/2025") == ("2025-11-01", "2025-11", "11/2025")


def test_extrair_codigo_ou_valor():
    assert extrair_codigo_ou_valor("loja 5") == "5"
    assert extrair_codigo_ou_valor("loja 8") == "8"
    assert extrair_codigo_ou_valor("MATRIC-38 na loja 5") == "5"
    assert extrair_codigo_ou_valor("MATRIC-302 na loja 8") == "8"
    assert extrair_codigo_ou_valor("MATRIC-302: loja 9") == "9"
    assert extrair_codigo_ou_valor("150") == "150"
    assert extrair_codigo_ou_valor("cargo 200") == "200"
    assert extrair_codigo_ou_valor("sem numero") == "sem numero"


def test_normalizar_tipo():
    assert normalizar_tipo("transferencia de loja") == TipoCorrecao.TRANSFERENCIA_LOJA.value
    assert normalizar_tipo("mudança de cargo") == TipoCorrecao.MUDANCA_CARGO.value
    assert normalizar_tipo("correcao de venda") == TipoCorrecao.CORRECAO_VENDA.value
    assert normalizar_tipo("exclusao") == TipoCorrecao.EXCLUSAO.value
    assert normalizar_tipo("atualizacao") == TipoCorrecao.ATUALIZACAO.value


def test_gerar_sql_transferencia_loja():
    sql, tabelas = gerar_sql_correcao(
        tipo="Transferência de loja",
        matricula="MATRIC-38",
        competencia="out/2025",
        antes="loja 5",
        depois="loja 8",
    )
    assert "UPDATE funcionario_loja" in sql
    assert "SET loja_id = (SELECT id FROM loja WHERE cod_loja = '8')" in sql
    assert "WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = 'MATRIC-38')" in sql
    assert "loja_id = (SELECT id FROM loja WHERE cod_loja = '5')" in sql
    assert "date_ref = '2025-10-01'" in sql
    assert "funcionario_loja" in tabelas
    assert "loja" in tabelas


def test_gerar_sql_mudanca_cargo():
    sql, tabelas = gerar_sql_correcao(
        tipo="Mudança de cargo",
        matricula="MATRIC-10",
        competencia="11/2025",
        antes="100",
        depois="150",
    )
    assert "UPDATE funcionario_cargo" in sql
    assert "SET cargo_id = (SELECT id FROM cargo WHERE cod_cargo = '150')" in sql
    assert "WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = 'MATRIC-10')" in sql
    assert "date_ref = '2025-11-01'" in sql
    assert "funcionario_cargo" in tabelas


def test_gerar_sql_correcao_venda():
    sql, tabelas = gerar_sql_correcao(
        tipo="Correção de venda",
        matricula="MATRIC-12",
        competencia="out/2025",
        antes="1000",
        depois="1500.50",
    )
    assert "UPDATE venda" in sql
    assert "SET vlr_venda = 1500.50" in sql
    assert "WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = 'MATRIC-12')" in sql
    assert "date_ref >= '2025-10-01'" in sql
    assert "date_ref < '2025-11-01'" in sql
    assert "venda" in tabelas


def test_gerar_sql_exclusao():
    sql, tabelas = gerar_sql_correcao(
        tipo="Exclusão",
        matricula="MATRIC-99",
        competencia="10/2025",
        antes="loja 1",
        depois="",
    )
    assert "DELETE FROM funcionario_loja" in sql
    assert "WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = 'MATRIC-99')" in sql
    assert "date_ref = '2025-10-01'" in sql
    assert "funcionario_loja" in tabelas


def test_gerar_sql_customizado():
    custom = "UPDATE funcionario_loja SET loja_id = 99 WHERE id = 1"
    sql, tabelas = gerar_sql_correcao(
        tipo="Transferência de loja",
        matricula="MATRIC-38",
        competencia="10/2025",
        antes="5",
        depois="8",
        sql_customizado=custom,
    )
    assert sql == custom + ";"
    assert "funcionario_loja" in tabelas
