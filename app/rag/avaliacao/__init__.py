"""Módulo de avaliação e calibração de guardrails vetoriais (A6-128)."""

from app.rag.avaliacao.metricas import (
    LinhaLimiar,
    Metricas,
    PerguntaRotulada,
    calcular_metricas,
    escolher_limiar,
    varrer_limiares,
)
from app.rag.avaliacao.relatorio import (
    EstatisticasLatencia,
    LinhaDesempenhoTipo,
    LinhaErro,
    calcular_desempenho_por_tipo,
    calcular_estatisticas_latencia,
    converter_historico,
    formatar_estatisticas_latencia,
    formatar_tabela_erros,
    formatar_tabela_limiares,
    formatar_tabela_por_tipo,
    formatar_tabela_teste,
)

__all__ = [
    "EstatisticasLatencia",
    "LinhaDesempenhoTipo",
    "LinhaErro",
    "LinhaLimiar",
    "Metricas",
    "PerguntaRotulada",
    "calcular_desempenho_por_tipo",
    "calcular_estatisticas_latencia",
    "calcular_metricas",
    "converter_historico",
    "escolher_limiar",
    "formatar_estatisticas_latencia",
    "formatar_tabela_erros",
    "formatar_tabela_limiares",
    "formatar_tabela_por_tipo",
    "formatar_tabela_teste",
    "varrer_limiares",
]
