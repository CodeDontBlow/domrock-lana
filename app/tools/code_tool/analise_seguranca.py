"""Análise estática de segurança do código Python gerado pela Lana.

Sprint 3 (A6-95 / US-20): antes de executar o código no runner/harness, verifica
via AST se o código contém imports ou chamadas proibidas/suspeitas.
Lê o código sem executá-lo.
"""
import ast
from dataclasses import dataclass
from typing import Any

IMPORTS_SUSPEITOS = frozenset({"os", "subprocess", "socket", "sys", "requests"})
CHAMADAS_SUSPEITAS = frozenset({"open", "eval", "exec", "__import__"})


@dataclass(frozen=True)
class AchadoSeguranca:
    """Representa um achado de segurança no código analisado."""

    linha: int
    descricao: str

    def __getitem__(self, item: str) -> Any:
        if item == "linha":
            return self.linha
        if item == "descricao":
            return self.descricao
        raise KeyError(item)

    def para_dict(self) -> dict[str, Any]:
        return {"linha": self.linha, "descricao": self.descricao}


def analisar_seguranca(codigo: str) -> list[AchadoSeguranca]:
    """Analisa o código Python e devolve uma lista de achados suspeitos (linha e descrição).

    São suspeitos:
    - import de os, subprocess, socket, sys ou requests;
    - chamadas a open, eval, exec ou __import__.
    """
    if not codigo or not codigo.strip():
        return []

    try:
        arvore = ast.parse(codigo)
    except SyntaxError as e:
        return [AchadoSeguranca(linha=e.lineno or 1, descricao=f"Erro de sintaxe no código: {e.msg}")]

    achados: list[AchadoSeguranca] = []

    for no in ast.walk(arvore):
        # 1. Imports tradicionais: `import os`, `import os.path`, `import sys as s`, etc.
        if isinstance(no, ast.Import):
            for alias in no.names:
                modulo_raiz = alias.name.split(".")[0]
                if modulo_raiz in IMPORTS_SUSPEITOS or alias.name in IMPORTS_SUSPEITOS:
                    achados.append(
                        AchadoSeguranca(
                            linha=no.lineno,
                            descricao=f"Import suspeito do módulo '{alias.name}'",
                        )
                    )

        # 2. Imports from: `from os import path`, `from subprocess import Popen`, etc.
        elif isinstance(no, ast.ImportFrom):
            modulo = no.module or ""
            modulo_raiz = modulo.split(".")[0]
            if modulo_raiz in IMPORTS_SUSPEITOS or modulo in IMPORTS_SUSPEITOS:
                achados.append(
                    AchadoSeguranca(
                        linha=no.lineno,
                        descricao=f"Import suspeito do módulo '{modulo}'",
                    )
                )

        # 3. Chamadas a funções: open(...), eval(...), exec(...), __import__(...)
        elif isinstance(no, ast.Call):
            nome_funcao = None
            if isinstance(no.func, ast.Name):
                nome_funcao = no.func.id
            elif isinstance(no.func, ast.Attribute):
                nome_funcao = no.func.attr

            if nome_funcao in CHAMADAS_SUSPEITAS:
                achados.append(
                    AchadoSeguranca(
                        linha=no.lineno,
                        descricao=f"Chamada suspeita à função '{nome_funcao}'",
                    )
                )

    achados.sort(key=lambda a: a.linha)
    return achados


# Alias para flexibilidade de importação
analisar_codigo = analisar_seguranca
