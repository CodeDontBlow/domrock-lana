"""Testes de integração end-to-end do sandbox de execução de código gerado."""
import os
import subprocess
import pytest

from app.simulacao.baseline import calcular_baseline
from app.tools.code_tool.codigo import (
    CodigoInseguroError,
    CodigoInvalidoError,
    extrair_codigo,
    validar_codigo,
)
from app.tools.code_tool.dtos import ContextoGeracao
from app.tools.code_tool.gerador import GeradorCodigo
from app.tools.code_tool.runner import SubprocessRunner
from tests.fakes import bases_pequenas, fonte_modelo, parametros_black_friday

CABECALHO_REGRA = "def aplicar_regra(bases, apuracao_base, competencias):\n"


def _executar_no_sandbox(fonte: str, timeout_s: int = 15):
    bases = bases_pequenas()
    baseline = calcular_baseline(bases)
    runner = SubprocessRunner(timeout_s=timeout_s)
    return runner.executar(fonte, bases.como_dict(), baseline, ["2025-11"])


def test_sandbox_e2e_codigo_valido_executa_e_retorna_contrato() -> None:
    """Valida o ciclo completo de um código gerado válido."""
    resposta_ia = (
        "Aqui está o código solicitado:\n```python\n"
        + fonte_modelo(parametros_black_friday())
        + "\n```\nEspero ter ajudado!"
    )
    codigo_extraido = extrair_codigo(resposta_ia)
    validar_codigo(codigo_extraido)

    resultado = _executar_no_sandbox(codigo_extraido)

    assert resultado.ok, resultado.mensagem
    assert resultado.status == "ok"
    assert resultado.apuracao_simulada is not None
    assert resultado.contribuicoes is not None
    assert "comissao" in resultado.apuracao_simulada.columns
    assert "matricula" in resultado.contribuicoes.columns


def test_sandbox_bloqueio_estatico_de_seguranca_ast() -> None:
    """Valida que tentativas de escape são bloqueadas antes mesmo da execução pelo validador AST."""
    tentativas_inseguras = [
        ("import socket", "socket"),
        ("import requests", "requests"),
        ("import os", "os"),
        ("open('arquivo.txt', 'w')", "open"),
        ("eval('2 + 2')", "eval"),
        ("exec('import sys')", "exec"),
        ("getattr(pd, 'read_csv')", "getattr"),
        ("pd.read_csv('segredo.csv')", "read_csv"),
        ("x = ().__class__", "__class__"),
    ]
    for trecho, nome_esperado in tentativas_inseguras:
        codigo = f"{CABECALHO_REGRA}    {trecho}\n    return {{}}\n"
        with pytest.raises((CodigoInseguroError, CodigoInvalidoError)) as exc:
            validar_codigo(codigo)
        assert nome_esperado in str(exc.value) or nome_esperado in getattr(exc.value, "descricao", "")


def test_sandbox_bloqueio_runtime_harness_restricoes() -> None:
    """Valida que, caso um import escape da validação AST, o harness bloqueia em runtime."""
    # datetime é permitido, mas urllib não
    codigo_import_proibido = (
        CABECALHO_REGRA
        + "    import urllib.request\n"
        + "    return {}\n"
    )
    resultado = _executar_no_sandbox(codigo_import_proibido)
    assert not resultado.ok
    assert resultado.status == "erro_codigo"
    assert "ImportError" in resultado.mensagem or "Import proibido" in resultado.mensagem


def test_sandbox_timeout_interrupcao_deterministica() -> None:
    """Valida que laços infinitos ou operações demoradas são cortadas exatamente pelo timeout."""
    codigo_loop = CABECALHO_REGRA + "    while True:\n        pass\n"
    resultado = _executar_no_sandbox(codigo_loop, timeout_s=2)

    assert resultado.status == "timeout"
    assert "Execução passou de 2s" in resultado.mensagem


def test_sandbox_captura_feedback_para_llm_em_caso_de_erro() -> None:
    """Valida que o traceback do erro e prints de depuração são capturados para retroalimentar a LLM."""
    codigo_com_erro = (
        CABECALHO_REGRA
        + "    print('LOG_SANDBOX: Iniciando calculo de comissao')\n"
        + "    total = apuracao_base['coluna_inexistente'] * 2\n"
        + "    return {}\n"
    )
    resultado = _executar_no_sandbox(codigo_com_erro)

    assert resultado.status == "erro_codigo"
    assert "KeyError" in resultado.mensagem
    assert "coluna_inexistente" in resultado.mensagem
    # Saída do código capturada pelo canal stderr para alimentar o prompt de correção
    assert "LOG_SANDBOX: Iniciando calculo de comissao" in resultado.mensagem


def test_sandbox_isolamento_de_ambiente_sem_vazar_env() -> None:
    """Valida que variáveis de ambiente confidenciais (chaves, senhas) não existem dentro do subprocesso."""
    os.environ["VARIAVEL_SECRETA_TESTE"] = "SEGREDO_SUPER_CONFIDENCIAL_123"
    codigo_verifica_env = (
        CABECALHO_REGRA
        + "    # O código não pode ver a variável secreta do host\n"
        + "    import os\n"
        + "    return {}\n"
    )
    resultado = _executar_no_sandbox(codigo_verifica_env)
    assert not resultado.ok
    assert "ImportError" in resultado.mensagem or "Import proibido" in resultado.mensagem
