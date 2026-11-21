"""Consolidação dos resultados, métricas, cenários alternativos e explicação em linguagem natural."""
from dataclasses import replace
import pandas as pd

from app.simulacao.assercoes import AssercaoViolada
from app.simulacao.bases import BasesSimulacao
from app.simulacao.cenarios import SimularCusto, propor_cenarios
from app.simulacao.dtos import AtingimentoMeta, ReferenciaSimulacao, ResultadoSimulacao, SimulacaoNaMeta
from app.simulacao.explicacao import Explicador
from app.simulacao.na_meta import escalar_vendas, fator_na_meta, montar_simulacao_na_meta
from app.simulacao.orquestracao.pipeline import ExecucaoFalhouError, TentativaAprovada, executar_codigo
from app.simulacao.por_pessoa import montar_apuracao_por_pessoa
from app.simulacao.regras.aplicador import calcular_ajustes
from app.simulacao.regras_aplicadas import contar_pessoas_no_piso, contar_regras_aplicadas
from app.simulacao.resumo import (
    avaliar_meta,
    avaliar_orcamento,
    avaliar_retorno,
    aviso_intercorrencias_pendentes,
    calcular_totais,
    maiores_lojas,
    medir_impacto,
    montar_ressalvas,
    quebrar_por,
)
from app.simulacao.vigencia import CampanhaContexto, calcular_baseline_vigente
from app.tools.code_tool.dtos import ContextoGeracao
from app.tools.code_tool.gerador import GeradorCodigo
from app.tools.code_tool.runner import CodeRunner
from app.tools.regra_tool.dtos import ParametrosSimulacao

# Sem "retorno": a explicação só volta a falar dele na Sprint 3 (decisão do PO, 26/10).
CAMPOS_EXPLICACAO: set[str] = {
    "totais", "por_marca", "por_cargo", "orcamento", "meta", "impacto", "maiores_lojas", "cenarios", "na_meta",
    "referencia",
}


def criar_simulador_custo(
    recalculo: GeradorCodigo,
    runner: CodeRunner,
    contexto: ContextoGeracao,
    bases: BasesSimulacao,
    baseline: pd.DataFrame,
) -> SimularCusto:
    """Devolve função que recalcula o custo determinístico de um cenário com parâmetros alternativos."""
    def simular_custo(parametros: ParametrosSimulacao) -> float | None:
        variante = replace(contexto, parametros=parametros)
        try:
            comparacao = executar_codigo(runner, recalculo.gerar(variante, None), variante, bases, baseline)
        except (ExecucaoFalhouError, AssercaoViolada):
            return None
        return calcular_totais(comparacao).diferenca

    return simular_custo


def simular_na_meta(
    contexto: ContextoGeracao,
    bases: BasesSimulacao,
    fontes: list[CampanhaContexto],
    meta: AtingimentoMeta,
    runner: CodeRunner,
    recalculo: GeradorCodigo,
) -> SimulacaoNaMeta | None:
    """Simula a campanha com vendas escaladas até a meta informada (A6-93)."""
    fator = fator_na_meta(meta)
    if fator is None:
        return None
    bases_escaladas = escalar_vendas(bases, contexto.parametros, fator)
    try:
        baseline_escalado = calcular_baseline_vigente(bases_escaladas, fontes)
        codigo = recalculo.gerar(contexto, None)
        comparacao = executar_codigo(runner, codigo, contexto, bases_escaladas, baseline_escalado)
    except (ExecucaoFalhouError, AssercaoViolada):
        # A simulação na meta é acessória: se falhar, a simulação segue sem ela (A6-93).
        return None
    vendas_na_meta = avaliar_meta(bases_escaladas.vendas, contexto.parametros).vendas_periodo
    return montar_simulacao_na_meta(
        fator, vendas_na_meta, calcular_totais(comparacao), contexto.parametros.orcamento_limite,
    )


def consolidar_resultado(
    rule_id: str,
    contexto: ContextoGeracao,
    bases: BasesSimulacao,
    baseline: pd.DataFrame,
    aprovada: TentativaAprovada,
    fontes: list[CampanhaContexto],
    referencia: ReferenciaSimulacao | None,
    explicador: Explicador,
    simular_custo: SimularCusto,
    runner: CodeRunner,
    recalculo: GeradorCodigo,
) -> ResultadoSimulacao:
    """Calcula todas as agregações, cenários, detalhamento por pessoa e redação final."""
    comparacao, parametros = aprovada.comparacao, contexto.parametros
    totais = calcular_totais(comparacao)
    orcamento = avaliar_orcamento(totais, parametros.orcamento_limite)
    por_marca = quebrar_por(comparacao, "cod_marca")
    meta = avaliar_meta(bases.vendas, parametros)
    na_meta = simular_na_meta(contexto, bases, fontes, meta, runner, recalculo)
    ajustes = calcular_ajustes(bases.rh, bases.intercorrencias)
    aviso_pendentes = aviso_intercorrencias_pendentes(bases.intercorrencias_pendentes)

    resultado = ResultadoSimulacao(
        rule_id=rule_id,
        competencias=contexto.competencias,
        totais=totais,
        por_marca=por_marca,
        por_cargo=quebrar_por(comparacao, "cod_cargo"),
        orcamento=orcamento,
        meta=meta,
        retorno=avaliar_retorno(totais, meta),
        impacto=medir_impacto(comparacao),
        maiores_lojas=maiores_lojas(comparacao),
        cenarios=propor_cenarios(parametros, totais.diferenca, orcamento, por_marca, simular_custo),
        ressalvas=montar_ressalvas(bases.intercorrencias_pendentes),
        codigo=aprovada.codigo.fonte,
        origem_codigo=aprovada.codigo.origem,
        tentativas=aprovada.numero,
        explicacao="",
        observacao=aprovada.observacao,
        apuracao_por_pessoa=montar_apuracao_por_pessoa(comparacao, ajustes),
        regras_base_aplicadas=contar_regras_aplicadas(ajustes),
        pessoas_no_piso=contar_pessoas_no_piso(comparacao, ajustes),
        na_meta=na_meta,
        referencia=referencia,
    )
    resumo = resultado.model_dump(include=CAMPOS_EXPLICACAO)
    if aviso_pendentes:
        resumo["aviso_pendentes"] = aviso_pendentes
    explicacao = explicador.explicar(resumo)
    if aviso_pendentes and aviso_pendentes not in explicacao:
        explicacao = f"{explicacao} {aviso_pendentes}." if explicacao else f"{aviso_pendentes}."
    return resultado.model_copy(update={"explicacao": explicacao})
