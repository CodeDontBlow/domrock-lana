"""Funções auxiliares para formatação de relatórios e mensagens (A6-128)."""

import statistics
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel
from app.rag.avaliacao.metricas import LinhaLimiar, PerguntaRotulada


class EstatisticasLatencia(BaseModel):
    """Métricas de latência observadas durante as buscas (A6-128)."""

    media_ms: float
    mediana_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float


class LinhaErro(BaseModel):
    """Registro de erro de classificação para auditoria (A6-128)."""

    pergunta: str
    tipo: str
    esperado: str
    previsto: str
    distancia: float
    fonte: str = ""
    item_proximo: str


class LinhaDesempenhoTipo(BaseModel):
    """Desempenho de classificação agrupado por tipo de pergunta (A6-128)."""

    tipo: str
    acertos: int
    total: int
    taxa_acerto: float


def converter_historico(historico: list[str]) -> list[BaseMessage]:
    """Converte strings alternadas em mensagens LangChain (A6-128).

    Exemplo:
        >>> msgs = converter_historico(["Oi", "Olá!"])
        >>> len(msgs) == 2
    """
    mensagens: list[BaseMessage] = []
    for indice, texto in enumerate(historico):
        if indice % 2 == 0:
            mensagens.append(HumanMessage(content=texto))
        else:
            mensagens.append(AIMessage(content=texto))
    return mensagens


def _calcular_p95(valores_ordenados: list[float]) -> float:
    """Calcula percentil 95 usando interpolação linear (A6-128)."""
    total = len(valores_ordenados)
    if total == 1:
        return valores_ordenados[0]
    posicao = 0.95 * (total - 1)
    base = int(posicao)
    fracao = posicao - base
    if base + 1 < total:
        return valores_ordenados[base] + fracao * (
            valores_ordenados[base + 1] - valores_ordenados[base]
        )
    return valores_ordenados[base]


def calcular_estatisticas_latencia(
    latencias_ms: list[float],
) -> EstatisticasLatencia:
    """Calcula média, mediana, P95, mínimo e máximo das latências (A6-128).

    Exemplo:
        >>> stats = calcular_estatisticas_latencia([10.0, 20.0, 30.0])
        >>> stats.media_ms == 20.0
    """
    if not latencias_ms:
        msg = f"Lista de latências vazia: {latencias_ms}. Esperado: lista com ao menos 1 valor."
        raise ValueError(msg)

    ordenados = sorted(latencias_ms)
    return EstatisticasLatencia(
        media_ms=round(statistics.mean(latencias_ms), 2),
        mediana_ms=round(statistics.median(latencias_ms), 2),
        p95_ms=round(_calcular_p95(ordenados), 2),
        min_ms=round(min(latencias_ms), 2),
        max_ms=round(max(latencias_ms), 2),
    )


def formatar_tabela_limiares(linhas: list[LinhaLimiar]) -> str:
    """Formata tabela Markdown com varredura de limiares (A6-128).

    Exemplo:
        >>> tabela = formatar_tabela_limiares(linhas)
        >>> "| Limiar |" in tabela
    """
    cabecalho = (
        "| Limiar | VP | FP | VN | FN | Acurácia | Precisão | Recall | F1 | Injeções Bloq. |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    )
    itens = [cabecalho]
    for l in linhas:
        m = l.metricas
        itens.append(
            f"| {l.limiar:.2f} | {m.vp} | {m.fp} | {m.vn} | {m.fn} | "
            f"{m.acuracia * 100:.1f}% | {m.precisao * 100:.1f}% | "
            f"{m.recall * 100:.1f}% | {m.f1:.4f} | {l.injecoes_bloqueadas} |"
        )
    return "\n".join(itens)


def formatar_tabela_teste(linha: LinhaLimiar) -> str:
    """Formata tabela Markdown do teste no limiar selecionado (A6-128).

    Exemplo:
        >>> tabela = formatar_tabela_teste(linha)
        >>> "| Limiar Escolhido |" in tabela
    """
    cabecalho = (
        "| Limiar Escolhido | VP | FP | VN | FN | Acurácia | Precisão | Recall | F1 | Injeções Bloq. |\n"
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    )
    m = linha.metricas
    dados = (
        f"| {linha.limiar:.2f} | {m.vp} | {m.fp} | {m.vn} | {m.fn} | "
        f"{m.acuracia * 100:.1f}% | {m.precisao * 100:.1f}% | "
        f"{m.recall * 100:.1f}% | {m.f1:.4f} | {linha.injecoes_bloqueadas} |"
    )
    return f"{cabecalho}\n{dados}"


def formatar_tabela_erros(erros: list[LinhaErro]) -> str:
    """Formata tabela Markdown com as discordâncias de teste (A6-128).

    Exemplo:
        >>> tabela = formatar_tabela_erros([])
        >>> "Nenhum erro" in tabela
    """
    if not erros:
        return "Nenhum erro encontrado no conjunto de teste."

    cabecalho = (
        "| Pergunta | Tipo | Esperado | Previsto | Distância | Fonte | Item Mais Próximo |\n"
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |"
    )
    linhas = [cabecalho]
    for e in erros:
        linhas.append(
            f"| {e.pergunta} | {e.tipo} | {e.esperado} | {e.previsto} | "
            f"{e.distancia:.4f} | {e.fonte} | {e.item_proximo} |"
        )
    return "\n".join(linhas)


def _contar_acertos_por_tipo(
    perguntas: list[PerguntaRotulada],
    distancias: list[float],
    limiar: float,
) -> dict[str, list[int]]:
    """Agrupa contagem de acertos e total por tipo de pergunta (A6-128)."""
    contagem: dict[str, list[int]] = {}
    for p, dist in zip(perguntas, distancias):
        previsto = "dentro" if dist <= limiar else "fora"
        acertou = 1 if previsto == p.esperado else 0
        if p.tipo not in contagem:
            contagem[p.tipo] = [0, 0]
        contagem[p.tipo][0] += acertou
        contagem[p.tipo][1] += 1
    return contagem


def calcular_desempenho_por_tipo(
    perguntas: list[PerguntaRotulada],
    distancias: list[float],
    limiar: float,
) -> list[LinhaDesempenhoTipo]:
    """Calcula acertos e total para cada tipo de pergunta (A6-128).

    Exemplo:
        >>> linhas = calcular_desempenho_por_tipo(perguntas, distancias, 0.5)
        >>> len(linhas) > 0
    """
    if len(perguntas) != len(distancias):
        msg = f"Tamanhos incompatíveis: {len(perguntas)} != {len(distancias)}"
        raise ValueError(msg)

    contagem = _contar_acertos_por_tipo(perguntas, distancias, limiar)
    return [
        LinhaDesempenhoTipo(
            tipo=t, acertos=c[0], total=c[1],
            taxa_acerto=round(c[0] / c[1], 4) if c[1] > 0 else 0.0,
        )
        for t, c in contagem.items()
    ]


def formatar_tabela_por_tipo(linhas: list[LinhaDesempenhoTipo]) -> str:
    """Formata tabela Markdown com acertos e total por tipo (A6-128).

    Exemplo:
        >>> tabela = formatar_tabela_por_tipo(linhas)
        >>> "| Tipo | Acertos | Total |" in tabela
    """
    cabecalho = (
        "| Tipo | Acertos | Total | Taxa de Acerto |\n"
        "| :--- | :---: | :---: | :---: |"
    )
    linhas_texto = [cabecalho]
    for l in linhas:
        linhas_texto.append(
            f"| {l.tipo} | {l.acertos} | {l.total} | {l.taxa_acerto * 100:.1f}% |"
        )
    return "\n".join(linhas_texto)


def formatar_estatisticas_latencia(stats: EstatisticasLatencia) -> str:
    """Formata resumo de latência em Markdown (A6-128).

    Exemplo:
        >>> texto = formatar_estatisticas_latencia(stats)
        >>> "Média:" in texto
    """
    return (
        f"- **Média:** {stats.media_ms:.2f} ms\n"
        f"- **Mediana:** {stats.mediana_ms:.2f} ms\n"
        f"- **P95:** {stats.p95_ms:.2f} ms\n"
        f"- **Mínimo / Máximo:** {stats.min_ms:.2f} ms / {stats.max_ms:.2f} ms"
    )
