"""Pipeline de execução, geração e conferência de código da simulação."""
from dataclasses import dataclass, replace
from typing import Any
import pandas as pd

from app.simulacao.assercoes import conferir_contra_referencia, conferir_resultado
from app.simulacao.bases import BasesSimulacao
from app.simulacao.regras.aplicador import aplicar_ajustes, calcular_ajustes
from app.simulacao.trilha import Cronometro
from app.tools.code_tool.codigo import CodigoInseguroError
from app.tools.code_tool.dtos import CodigoGerado, ContextoGeracao
from app.tools.code_tool.gerador import GeradorCodigo
from app.tools.code_tool.runner import CodeRunner

CONFERIDO: str = "Resultado da IA conferido com o cálculo determinístico."
USOU_REFERENCIA: str = (
    "O código da IA divergiu do cálculo determinístico em todas as tentativas; "
    "o resultado mostrado é o do cálculo determinístico."
)


class ExecucaoFalhouError(RuntimeError):
    """O código gerado falhou ao rodar (erro, timeout ou saída inválida)."""


class SimulacaoFalhouError(RuntimeError):
    """Nenhuma tentativa produziu resultado válido. Nunca se devolve resultado parcial."""

    def __init__(
        self, etapa: str, mensagem: str, codigo: str | None = None, alertas: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(f"{etapa}: {mensagem}")
        self.etapa, self.mensagem, self.codigo = etapa, mensagem, codigo
        self.alertas = alertas or []


@dataclass(frozen=True)
class TentativaAprovada:
    codigo: CodigoGerado
    comparacao: pd.DataFrame
    numero: int
    observacao: str = ""


def aplicar_regras_base(comparacao: pd.DataFrame, bases: BasesSimulacao) -> pd.DataFrame:
    """Aplica regras de RH (5c a 5g e piso) e calcula a diferença de comissão."""
    ajustes = calcular_ajustes(bases.rh, bases.intercorrencias)
    ajustada = aplicar_ajustes(comparacao, ajustes, ["comissao", "comissao_simulada"])
    # As brutas (só 5a/5b) servem para dizer se o piso venceu: por_pessoa e regras_aplicadas.
    ajustada["comissao_bruta"] = comparacao["comissao"]
    ajustada["comissao_simulada_bruta"] = comparacao["comissao_simulada"]
    ajustada["diferenca"] = (ajustada["comissao_simulada"] - ajustada["comissao"]).round(2)
    return ajustada


def executar_codigo(
    runner: CodeRunner,
    codigo: CodigoGerado,
    contexto: ContextoGeracao,
    bases: BasesSimulacao,
    baseline: pd.DataFrame,
) -> pd.DataFrame:
    """Roda o código gerado no sandbox e confere o resultado contra o contrato."""
    execucao = runner.executar(codigo.fonte, bases.como_dict(), baseline, contexto.competencias)
    if not execucao.ok or execucao.apuracao_simulada is None or execucao.contribuicoes is None:
        raise ExecucaoFalhouError(f"{execucao.status}: {execucao.mensagem}")
    comparacao = conferir_resultado(baseline, execucao.apuracao_simulada, execucao.contribuicoes, contexto.parametros)
    return aplicar_regras_base(comparacao, bases)


def executar_referencia(
    referencia: GeradorCodigo | None,
    runner: CodeRunner,
    contexto: ContextoGeracao,
    bases: BasesSimulacao,
    baseline: pd.DataFrame,
) -> TentativaAprovada | None:
    """Gera e executa a implementação determinística de referência, se configurada."""
    if referencia is None:
        return None
    codigo = referencia.gerar(contexto, None)
    return TentativaAprovada(codigo, executar_codigo(runner, codigo, contexto, bases, baseline), 0)


def gerar_e_executar(
    gerador: GeradorCodigo,
    runner: CodeRunner,
    max_tentativas: int,
    contexto: ContextoGeracao,
    bases: BasesSimulacao,
    baseline: pd.DataFrame,
    conferencia: TentativaAprovada | None,
    cronometro: Cronometro,
    alertas: list[dict[str, Any]],
) -> TentativaAprovada:
    """Tenta gerar e rodar código da IA com fallback/conferência determinística."""
    erro: str | None = None
    codigo: CodigoGerado | None = None
    for numero in range(1, max_tentativas + 1):
        try:
            with cronometro.medir("gerar_codigo"):
                codigo = gerador.gerar(contexto, erro)
            with cronometro.medir("executar_sandbox"):
                comparacao = executar_codigo(runner, codigo, contexto, bases, baseline)
            if conferencia is None:
                return TentativaAprovada(codigo, comparacao, numero)
            with cronometro.medir("conferir"):
                conferir_contra_referencia(comparacao, conferencia.comparacao)
            return TentativaAprovada(codigo, comparacao, numero, CONFERIDO)
        except CodigoInseguroError as falha:
            alertas.append({
                "tipo": "codigo_inseguro",
                "linha": falha.linha,
                "descricao": falha.descricao,
                "mensagem": f"Código Python suspeito na linha {falha.linha}: {falha.descricao}",
            })
            erro = f"{type(falha).__name__}: {falha}"
        except Exception as falha:
            erro = f"{type(falha).__name__}: {falha}"
    if conferencia is not None:
        return replace(conferencia, numero=max_tentativas, observacao=f"{USOU_REFERENCIA} Último erro: {erro}")
    raise SimulacaoFalhouError(
        "seguranca_codigo" if alertas else "geracao_codigo",
        erro or "sem detalhe",
        codigo.fonte if codigo else None,
        alertas=alertas,
    )
