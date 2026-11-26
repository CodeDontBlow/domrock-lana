"""Cálculo de métricas e calibração de limiar do guardrail (A6-128)."""

from typing import Literal
from pydantic import BaseModel, Field

TipoPergunta = Literal[
    "regra",
    "campanha",
    "follow_up",
    "sistema",
    "neutra",
    "injecao",
    "legislacao",
    "estrategia",
]
Esperado = Literal["dentro", "fora"]


class PerguntaRotulada(BaseModel):
    """Pergunta com histórico opcional e rótulos de escopo (A6-128)."""

    pergunta: str
    historico: list[str] = Field(default_factory=list)
    esperado: Esperado
    tipo: TipoPergunta


class Metricas(BaseModel):
    """Matriz de confusão e métricas de classificação binária (A6-128)."""

    vp: int
    fp: int
    vn: int
    fn: int
    acuracia: float
    precisao: float
    recall: float
    f1: float


class LinhaLimiar(BaseModel):
    """Resultado da avaliação para um limiar de distância específico (A6-128)."""

    limiar: float
    metricas: Metricas
    injecoes_bloqueadas: int


def calcular_metricas(
    esperados: list[bool],
    previstos: list[bool],
) -> Metricas:
    """Calcula matriz de confusão e indicadores para corte binário (A6-128).

    Exemplo:
        >>> m = calcular_metricas([True, False], [True, False])
        >>> m.acuracia == 1.0
    """
    if len(esperados) != len(previstos):
        msg = f"Tamanhos incompatíveis: {len(esperados)} != {len(previstos)}"
        raise ValueError(msg)

    vp = sum(1 for e, p in zip(esperados, previstos) if e and p)
    fp = sum(1 for e, p in zip(esperados, previstos) if not e and p)
    vn = sum(1 for e, p in zip(esperados, previstos) if not e and not p)
    fn = sum(1 for e, p in zip(esperados, previstos) if e and not p)

    total = len(esperados)
    acuracia = (vp + vn) / total if total > 0 else 0.0
    precisao = vp / (vp + fp) if (vp + fp) > 0 else 0.0
    recall = vp / (vp + fn) if (vp + fn) > 0 else 0.0
    f1 = (2 * precisao * recall) / (precisao + recall) if (precisao + recall) > 0 else 0.0

    return Metricas(
        vp=vp,
        fp=fp,
        vn=vn,
        fn=fn,
        acuracia=round(acuracia, 4),
        precisao=round(precisao, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
    )


def varrer_limiares(
    perguntas: list[PerguntaRotulada],
    distancias: list[float],
    limiares: list[float],
) -> list[LinhaLimiar]:
    """Varre múltiplos limiares gerando uma linha de métricas para cada (A6-128).

    Exemplo:
        >>> linhas = varrer_limiares(perguntas, distancias, [0.4, 0.5])
        >>> len(linhas) == 2
    """
    if len(perguntas) != len(distancias):
        msg = f"Tamanhos incompatíveis: {len(perguntas)} != {len(distancias)}"
        raise ValueError(msg)

    linhas: list[LinhaLimiar] = []
    esperados = [p.esperado == "dentro" for p in perguntas]

    for limiar in limiares:
        previstos = [d <= limiar for d in distancias]
        metricas = calcular_metricas(esperados, previstos)
        bloqueadas = sum(
            1
            for p, d in zip(perguntas, distancias)
            if p.tipo == "injecao" and d > limiar
        )
        linhas.append(
            LinhaLimiar(
                limiar=limiar,
                metricas=metricas,
                injecoes_bloqueadas=bloqueadas,
            )
        )
    return linhas


def escolher_limiar(linhas: list[LinhaLimiar]) -> float:
    """Escolhe o limiar ótimo por F1, injeções barradas e menor valor (A6-128).

    Critério de desempate:
    1. Maior F1-score (arredondado a 4 casas decimais)
    2. Maior quantidade de injeções bloqueadas
    3. Menor valor numérico de limiar

    Exemplo:
        >>> limiar = escolher_limiar(linhas)
        >>> limiar > 0
    """
    if not linhas:
        msg = f"Lista de linhas vazia: {linhas}. Esperado: lista com ao menos 1 linha."
        raise ValueError(msg)

    # A6-128: -linha.limiar garante preferência pelo menor limiar em caso de empate
    melhor = max(
        linhas,
        key=lambda l: (
            round(l.metricas.f1, 4),
            l.injecoes_bloqueadas,
            -l.limiar,
        ),
    )
    return melhor.limiar
