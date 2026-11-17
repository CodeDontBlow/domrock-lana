"""Testes da análise estática de segurança do código Python (A6-95 / US-20)."""
import pytest

from app.tools.code_tool.analise_seguranca import AchadoSeguranca, analisar_codigo, analisar_seguranca

CODIGO_LIMPO = """
def aplicar_regra(bases, apuracao_base, competencias):
    import pandas as pd
    import numpy as np
    import math
    from datetime import datetime

    simulada = apuracao_base.copy()
    simulada["comissao_simulada"] = simulada["comissao_base"] * 1.05
    return simulada
"""


def test_codigo_limpo_sem_achados() -> None:
    achados = analisar_seguranca(CODIGO_LIMPO)
    assert achados == []
    assert len(achados) == 0


def test_import_os_aponta_linha_certa() -> None:
    codigo = (
        "def aplicar_regra(bases, apuracao_base, competencias):\n"
        "    import pandas as pd\n"
        "    import os\n"  # Linha 3
        "    return apuracao_base\n"
    )
    achados = analisar_seguranca(codigo)

    assert len(achados) == 1
    assert achados[0].linha == 3
    assert "os" in achados[0].descricao
    assert achados[0]["linha"] == 3


def test_eval_aponta_linha_certa() -> None:
    codigo = (
        "def aplicar_regra(bases, apuracao_base, competencias):\n"
        "    resultado = eval('1 + 1')\n"  # Linha 2
        "    return apuracao_base\n"
    )
    achados = analisar_seguranca(codigo)

    assert len(achados) == 1
    assert achados[0].linha == 2
    assert "eval" in achados[0].descricao


@pytest.mark.parametrize("modulo", ["os", "subprocess", "socket", "sys", "requests"])
def test_imports_suspeitos_sao_bloqueados(modulo: str) -> None:
    codigo = f"import {modulo}\n"
    achados = analisar_seguranca(codigo)
    assert len(achados) == 1
    assert achados[0].linha == 1
    assert modulo in achados[0].descricao


@pytest.mark.parametrize("modulo", ["os", "subprocess", "socket", "sys", "requests"])
def test_from_imports_suspeitos_sao_bloqueados(modulo: str) -> None:
    codigo = f"from {modulo} import algo\n"
    achados = analisar_seguranca(codigo)
    assert len(achados) == 1
    assert achados[0].linha == 1
    assert modulo in achados[0].descricao


@pytest.mark.parametrize("funcao", ["open", "eval", "exec", "__import__"])
def test_chamadas_suspeitas_sao_bloqueadas(funcao: str) -> None:
    codigo = f"resultado = {funcao}('arg')\n"
    achados = analisar_seguranca(codigo)
    assert len(achados) == 1
    assert achados[0].linha == 1
    assert funcao in achados[0].descricao


def test_multiplos_achados_ordenados_por_linha() -> None:
    codigo = (
        "import os\n"       # Linha 1
        "import sys\n"      # Linha 2
        "open('/etc/passwd')\n"  # Linha 3
        "exec('pass')\n"    # Linha 4
    )
    achados = analisar_seguranca(codigo)
    assert len(achados) == 4
    assert [a.linha for a in achados] == [1, 2, 3, 4]


def test_codigo_com_erro_de_sintaxe_devolve_achado() -> None:
    codigo = "def aplicar_regra(:\n"
    achados = analisar_seguranca(codigo)
    assert len(achados) == 1
    assert achados[0].linha == 1
    assert "sintaxe" in achados[0].descricao.lower()


def test_alias_analisar_codigo() -> None:
    assert analisar_codigo == analisar_seguranca
