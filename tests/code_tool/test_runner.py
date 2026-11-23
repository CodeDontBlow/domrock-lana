"""Executa o harness de verdade em subprocesso (~1 s por caso, por causa do import do pandas)."""
import logging
import sys

import pytest

from app.simulacao.baseline import calcular_baseline
from app.tools.code_tool.runner import SubprocessRunner, limites_de_recursos_disponiveis
from tests.fakes import bases_pequenas, fonte_modelo, parametros_black_friday

CABECALHO = "def aplicar_regra(bases, apuracao_base, competencias):\n"


def _executar(fonte: str, timeout_s: int = 20):
    bases = bases_pequenas()
    return SubprocessRunner(timeout_s=timeout_s).executar(
        fonte, bases.como_dict(), calcular_baseline(bases), ["2025-11"]
    )


def test_runner_executa_o_modelo_e_devolve_as_tabelas() -> None:
    execucao = _executar(fonte_modelo(parametros_black_friday()))

    assert execucao.ok, execucao.mensagem
    assert execucao.apuracao_simulada is not None
    assert sorted(execucao.contribuicoes["matricula"]) == ["M1", "M2"]  # G1 é gerente: fora


def test_runner_reporta_excecao_do_codigo_gerado() -> None:
    execucao = _executar(CABECALHO + "    raise KeyError('coluna_x')\n")

    assert execucao.status == "erro_codigo"
    assert "KeyError" in execucao.mensagem


def test_runner_reporta_retorno_fora_do_contrato() -> None:
    execucao = _executar(CABECALHO + "    return {'apuracao_simulada': 1}\n")

    assert execucao.status == "erro_codigo"
    assert "Esperado DataFrame" in execucao.mensagem


def test_runner_interrompe_loop_infinito_por_timeout() -> None:
    execucao = _executar(CABECALHO + "    while True:\n        pass\n", timeout_s=2)

    assert execucao.status == "timeout"


def test_runner_bloqueia_escrita_em_disco_mesmo_se_passar_pela_validacao() -> None:
    fonte = CABECALHO + "    import pathlib\n    pathlib.Path('x.txt').write_text('a' * 10)\n    return {}\n"

    execucao = _executar(fonte)

    assert not execucao.ok


def test_runner_ignora_print_do_codigo_gerado_no_resultado() -> None:
    fonte = fonte_modelo(parametros_black_friday()).replace(
        "    simulada = apuracao_base.copy()", "    print('depurando')\n    simulada = apuracao_base.copy()"
    )

    execucao = _executar(fonte)

    assert execucao.ok, execucao.mensagem


def test_runner_mostra_o_print_do_codigo_quando_ele_falha() -> None:
    execucao = _executar(CABECALHO + "    print('coluna_x ausente')\n    raise KeyError('x')\n")

    assert execucao.status == "erro_codigo"
    assert "coluna_x ausente" in execucao.mensagem


def test_runner_bloqueia_import_e_open_em_tempo_de_execucao() -> None:
    for corpo in ("    import os\n", "    open('/proc/1/environ')\n"):
        execucao = _executar(CABECALHO + corpo + "    return {}\n")

        assert execucao.status == "erro_codigo"
        assert "ImportError" in execucao.mensagem or "NameError" in execucao.mensagem


def sem_modulo_resource() -> bool:
    """Simula o Windows, onde o harness não consegue aplicar os limites."""
    return False


def com_modulo_resource() -> bool:
    return True


def test_limites_de_recursos_so_faltam_no_windows() -> None:
    assert limites_de_recursos_disponiveis() is (sys.platform != "win32")


def test_runner_avisa_no_log_quando_o_sandbox_roda_sem_limites(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="app.tools.code_tool.runner"):
        SubprocessRunner(timeout_s=7, tem_limites=sem_modulo_resource)
    assert "módulo 'resource' indisponível" in caplog.text
    assert "timeout de 7s" in caplog.text


def test_runner_nao_avisa_quando_os_limites_valem(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="app.tools.code_tool.runner"):
        SubprocessRunner(tem_limites=com_modulo_resource)
    assert caplog.text == ""
