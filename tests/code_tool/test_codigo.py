import pytest

from app.tools.code_tool.codigo import CodigoInseguroError, CodigoInvalidoError, extrair_codigo, validar_codigo

VALIDO = "import pandas as pd\n\ndef aplicar_regra(bases, apuracao_base, competencias):\n    return {}\n"


def test_extrair_codigo_devolve_o_unico_bloco_python() -> None:
    assert extrair_codigo(f"Segue:\n```python\n{VALIDO}```\nfim") == VALIDO


def test_extrair_codigo_rejeita_resposta_sem_bloco() -> None:
    with pytest.raises(CodigoInvalidoError, match="encontrados 0"):
        extrair_codigo(VALIDO)


@pytest.mark.parametrize(
    ("fonte", "trecho"),
    [
        ("import os\n" + VALIDO, "'os'"),
        ("from subprocess import run\n" + VALIDO, "'subprocess'"),
        (VALIDO + "open('/etc/passwd')\n", "'open'"),
        (VALIDO + "x = ().__class__\n", "__class__"),
        (VALIDO + "eval('1')\n", "'eval'"),
        # Regressões do code review: escapes que passavam pela validação.
        (VALIDO + "pd.io.common.os.system('id')\n", "'system'"),
        (VALIDO + "__builtins__['__import__']('os')\n", "'__builtins__'"),
        (VALIDO + "pd.read_csv('/proc/1/environ')\n", "'read_csv'"),
        ("import pandas.io.common\n" + VALIDO, "pandas.io.common"),
        ("from pandas import io\n" + VALIDO, "pandas.io"),
        (VALIDO + "pd.DataFrame().query('a')\n", "'query'"),
        (VALIDO + "x = pd._libs\n", "'_libs'"),
        ("def aplicar_regra(bases):\n    return {}\n", "aplicar_regra(bases, apuracao_base"),
        ("def aplicar_regra(:\n", "não é Python válido"),
    ],
)
def test_validar_codigo_recusa_codigo_inseguro_ou_fora_do_contrato(fonte: str, trecho: str) -> None:
    with pytest.raises(CodigoInvalidoError, match=None) as erro:
        validar_codigo(fonte)

    assert trecho in str(erro.value)


def test_validar_codigo_distingue_codigo_inseguro_com_linha_de_sintaxe_invalida() -> None:
    # 1. import os levanta CodigoInseguroError com linha
    with pytest.raises(CodigoInseguroError) as exc_import:
        validar_codigo("import os\n" + VALIDO)
    assert exc_import.value.linha == 1
    assert "os" in exc_import.value.descricao

    # 2. eval(...) levanta CodigoInseguroError com linha
    with pytest.raises(CodigoInseguroError) as exc_eval:
        validar_codigo(VALIDO + "eval('1')\n")
    assert exc_eval.value.linha == 5
    assert "eval" in exc_eval.value.descricao

    # 3. atributo proibido levanta CodigoInseguroError com linha
    with pytest.raises(CodigoInseguroError) as exc_attr:
        validar_codigo(VALIDO + "x = pd._libs\n")
    assert exc_attr.value.linha == 5
    assert "_libs" in exc_attr.value.descricao

    # 4. sintaxe inválida levanta CodigoInvalidoError que NÃO é CodigoInseguroError
    with pytest.raises(CodigoInvalidoError) as exc_sintaxe:
        validar_codigo("def aplicar_regra(:\n")
    assert not isinstance(exc_sintaxe.value, CodigoInseguroError)
