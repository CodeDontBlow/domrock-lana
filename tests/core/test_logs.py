"""Testes da configuração de logs da Lana (A6-128)."""
import logging

import pytest

from app.core.logs import NOME_LOGGER_DA_APP, configurar_logs_da_lana


@pytest.fixture
def logger_da_app_limpo():
    logger_da_app = logging.getLogger(NOME_LOGGER_DA_APP)
    handlers_antes, nivel_antes = list(logger_da_app.handlers), logger_da_app.level
    logger_da_app.handlers.clear()
    yield logger_da_app
    logger_da_app.handlers[:] = handlers_antes
    logger_da_app.setLevel(nivel_antes)


def test_eventos_info_dos_modulos_da_app_aparecem(logger_da_app_limpo, capsys):
    configurar_logs_da_lana()
    logging.getLogger("app.rag.base_vetorial").info('{"evento": "rag_indexado"}')
    assert '{"evento": "rag_indexado"}' in capsys.readouterr().err


def test_configurar_duas_vezes_nao_duplica_a_saida(logger_da_app_limpo):
    configurar_logs_da_lana()
    configurar_logs_da_lana()
    assert len(logger_da_app_limpo.handlers) == 1
