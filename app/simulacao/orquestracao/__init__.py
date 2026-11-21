"""Subpacote de orquestração interna da simulação (pipeline, amostragem e consolidação)."""
from app.simulacao.orquestracao.amostragem import LINHAS_AMOSTRA, amostra_vendas, amostras, modelo_da_ia
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
    aplicar_regras_base,
    executar_codigo,
    executar_referencia,
    gerar_e_executar,
)

__all__ = [
    "LINHAS_AMOSTRA",
    "CAMPOS_EXPLICACAO",
    "CONFERIDO",
    "USOU_REFERENCIA",
    "ExecucaoFalhouError",
    "SimulacaoFalhouError",
    "TentativaAprovada",
    "amostra_vendas",
    "amostras",
    "modelo_da_ia",
    "aplicar_regras_base",
    "executar_codigo",
    "executar_referencia",
    "gerar_e_executar",
    "criar_simulador_custo",
    "consolidar_resultado",
]
