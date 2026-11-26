"""Orquestra a simulação: valida a regra, apura o baseline, gera e executa o código da regra,
confere o resultado e resume. A LLM só entra na geração do código e na redação final.
"""
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from typing import Any
import pandas as pd

from app.simulacao.bases import BasesSimulacao, FonteBases, competencias_do_periodo, deslocar_bases
from app.simulacao.dtos import ReferenciaSimulacao, ResultadoSimulacao
from app.simulacao.especificacao import CatalogoEspecificacao
from app.simulacao.explicacao import Explicador
from app.simulacao.orquestracao.amostragem import (
    LINHAS_AMOSTRA,
    amostra_vendas as _amostra_vendas,
    amostras as _amostras,
    modelo_da_ia,
)
from app.simulacao.orquestracao.consolidador import (
    CAMPOS_EXPLICACAO,
    consolidar_resultado,
    criar_simulador_custo,
)
from app.simulacao.orquestracao.pipeline import (
    CONFERIDO,
    USOU_REFERENCIA,
    ExecucaoFalhouError,
    SimulacaoFalhouError,
    TentativaAprovada,
    aplicar_regras_base as _aplicar_regras_base,
    executar_codigo,
    executar_referencia,
    gerar_e_executar,
)
from app.simulacao.trilha import Cronometro, ExecucaoSimulada, montar_trilha_simulacao
from app.simulacao.vigencia import (
    CampanhaContexto,
    calcular_baseline_vigente,
    calcular_periodos,
    detectar_conflitos,
    fontes_da_vigente,
)
from app.tools.code_tool.dtos import CodigoGerado, ContextoGeracao
from app.tools.code_tool.gerador import GeradorCodigo, GeradorCodigoModelo
from app.tools.code_tool.runner import CodeRunner
from app.tools.regra_tool.dtos import RegraCampanha
from app.tools.regra_tool.parametros import RegraInvalidaError, ler_parametros
from app.tools.regra_tool.referencia import ReferenciaCalculo, ler_referencia


def _resumo_referencia(referencia: ReferenciaCalculo | None, lidas: list[str]) -> ReferenciaSimulacao | None:
    if referencia is None:
        return None
    return ReferenciaSimulacao(
        competencia_referencia=referencia.competencia,
        pct_crescimento=referencia.pct_crescimento,
        competencias_lidas=lidas,
        descricao=referencia.descrever(),
    )


def _modelo_da_ia(aprovada: TentativaAprovada) -> str:
    """O modelo que escreveu o código, ou a origem do código fixo (ex.: 'modelo')."""
    return modelo_da_ia(aprovada.codigo.origem, aprovada.observacao, USOU_REFERENCIA)


class SimuladorCampanha:
    """Ex.: SimuladorCampanha(fonte, gerador, SubprocessRunner(), explicador, referencia).simular(regra)

    `referencia` gera o código determinístico do mesmo contrato; quando existe, todo resultado
    da IA é conferido contra ele. O contrato da Sprint 1 tem forma fixa, então sempre há referência.
    `recalculo` gera o código determinístico que simula de novo os cenários alternativos.
    `especificacao` traz as campanhas da especificação, que somam às do sistema na % vigente.
    `hoje` decide se o período é futuro e, então, calculado sobre a competência de referência (ADR-006).
    """

    def __init__(
        self,
        fonte_bases: FonteBases,
        gerador: GeradorCodigo,
        runner: CodeRunner,
        explicador: Explicador,
        referencia: GeradorCodigo | None = None,
        max_tentativas: int = 2,
        recalculo: GeradorCodigo | None = None,
        especificacao: CatalogoEspecificacao | None = None,
        hoje: Callable[[], date] = date.today,
    ) -> None:
        self._fonte_bases = fonte_bases
        self._gerador = gerador
        self._runner = runner
        self._explicador = explicador
        self._referencia = referencia
        self._max_tentativas = max_tentativas
        self._recalculo = recalculo or GeradorCodigoModelo()
        self._especificacao = especificacao
        self._hoje = hoje

    def simular(self, regra: RegraCampanha, campanhas: list[CampanhaContexto] | None = None) -> ResultadoSimulacao:
        alertas: list[dict[str, Any]] = []
        parametros = ler_parametros(regra)
        referencia = self._ler_referencia(regra, parametros.data_inicio, parametros.data_fim)
        competencias = competencias_do_periodo(parametros.data_inicio, parametros.data_fim)
        cronometro = Cronometro()

        with cronometro.medir("carregar_bases"):
            bases, lidas = self._carregar(competencias, referencia)

        resumo_referencia = _resumo_referencia(referencia, lidas)
        fontes = self._campanhas_da_especificacao() + list(campanhas or [])
        periodos = calcular_periodos(parametros, bases.comissoes, fontes)
        conflitos = detectar_conflitos(parametros, fontes)

        with cronometro.medir("comissao_atual"):
            baseline = calcular_baseline_vigente(bases, fontes)

        contexto = ContextoGeracao(parametros, competencias, _amostras(bases, baseline))

        with cronometro.medir("conferir"):
            conferencia = self._executar_referencia(contexto, bases, baseline)

        aprovada = self._gerar_e_executar(contexto, bases, baseline, conferencia, cronometro, alertas)

        with cronometro.medir("resumir"):
            resultado = self._resumir(
                regra.rule_id, contexto, bases, baseline, aprovada, fontes, resumo_referencia,
            )

        trilha = montar_trilha_simulacao(
            ExecucaoSimulada(
                parametros=parametros,
                competencias=competencias,
                bases=bases,
                baseline=baseline,
                modelo=_modelo_da_ia(aprovada),
                tentativas=aprovada.numero,
                conferido=CONFERIDO in aprovada.observacao,
                usou_referencia=USOU_REFERENCIA in aprovada.observacao,
                linhas_executadas=len(aprovada.comparacao),
                totais=resultado.totais,
                campanhas=fontes_da_vigente(fontes, periodos),
                tempos=cronometro.tempos,
                referencia=resumo_referencia,
            )
        )
        return resultado.model_copy(update={
            "comissao_periodo": periodos,
            "conflitos": conflitos,
            "trilha": trilha,
            "alertas": list(alertas),
        })

    def _campanhas_da_especificacao(self) -> list[CampanhaContexto]:
        return self._especificacao.campanhas() if self._especificacao else []

    def _ler_referencia(self, regra: RegraCampanha, inicio: date, fim: date) -> ReferenciaCalculo | None:
        valores = {p.key: p.value for p in regra.parametros}
        referencia, erros = ler_referencia(valores, inicio, fim, self._hoje())
        if erros:
            raise RegraInvalidaError(erros)
        return referencia

    def _carregar(
        self, competencias: list[str], referencia: ReferenciaCalculo | None,
    ) -> tuple[BasesSimulacao, list[str]]:
        """As bases do período e as competências lidas: as da referência, quando o período é futuro."""
        lidas = referencia.competencias_lidas(competencias) if referencia else competencias
        bases = self._fonte_bases.carregar(lidas)
        sem_dados = sorted(set(lidas) - set(bases.rh["competencia"]))
        if sem_dados and referencia:
            raise SimulacaoFalhouError(
                "dados",
                f"Sem base de RH para {sem_dados} (referência); "
                "importe essas competências ou escolha outro mês de referência",
            )
        if sem_dados:
            raise SimulacaoFalhouError("dados", f"Sem base de RH para {sem_dados}; importe essas competências")
        if referencia:
            bases = deslocar_bases(bases, referencia.meses, referencia.fator)
        return bases, lidas

    def _executar_referencia(
        self, contexto: ContextoGeracao, bases: BasesSimulacao, baseline: pd.DataFrame,
    ) -> TentativaAprovada | None:
        return executar_referencia(self._referencia, self._runner, contexto, bases, baseline)

    def _gerar_e_executar(
        self,
        contexto: ContextoGeracao,
        bases: BasesSimulacao,
        baseline: pd.DataFrame,
        conferencia: TentativaAprovada | None,
        cronometro: Cronometro,
        alertas: list[dict[str, Any]],
    ) -> TentativaAprovada:
        return gerar_e_executar(
            self._gerador,
            self._runner,
            self._max_tentativas,
            contexto,
            bases,
            baseline,
            conferencia,
            cronometro,
            alertas,
        )

    def _executar(
        self, codigo: CodigoGerado, contexto: ContextoGeracao, bases: BasesSimulacao, baseline: pd.DataFrame,
    ) -> pd.DataFrame:
        return executar_codigo(self._runner, codigo, contexto, bases, baseline)

    def _resumir(
        self,
        rule_id: str,
        contexto: ContextoGeracao,
        bases: BasesSimulacao,
        baseline: pd.DataFrame,
        aprovada: TentativaAprovada,
        fontes: list[CampanhaContexto],
        referencia: ReferenciaSimulacao | None = None,
    ) -> ResultadoSimulacao:
        simulador_custo = criar_simulador_custo(self._recalculo, self._runner, contexto, bases, baseline)
        return consolidar_resultado(
            rule_id=rule_id,
            contexto=contexto,
            bases=bases,
            baseline=baseline,
            aprovada=aprovada,
            fontes=fontes,
            referencia=referencia,
            explicador=self._explicador,
            simular_custo=simulador_custo,
            runner=self._runner,
            recalculo=self._recalculo,
        )
