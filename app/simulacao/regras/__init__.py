"""Subpacote modular de regras de negócio de comissões e RH (5a–5g, afastamentos, férias e pisos)."""
from app.simulacao.regras.afastamento import (
    ajuste_afastamento,
    coletar_afastamentos,
    descrever_afastamento,
)
from app.simulacao.regras.aplicador import (
    ajustar_comissao,
    ajustar_linha_rh,
    aplicar_ajustes,
    calcular_ajustes,
)
from app.simulacao.regras.ferias import ajuste_ferias
from app.simulacao.regras.piso import descrever_piso, detalhar_base
from app.simulacao.regras.tipos import (
    COLUNAS_INTERCORRENCIAS,
    PISO_AFASTAMENTO,
    AjusteMatricula,
    EventoIntercorrencia,
    RegraAplicada,
    _Evento,
    formatar_moeda,
    formatar_pct,
)
from app.simulacao.regras.validacao import (
    datas_validadas,
    dias_intersecao,
    intercorrencias_vazias,
    para_data,
    validar_e_extrair_eventos,
)
from app.simulacao.regras.vinculo import ajuste_vinculo

__all__ = [
    "PISO_AFASTAMENTO",
    "COLUNAS_INTERCORRENCIAS",
    "RegraAplicada",
    "AjusteMatricula",
    "EventoIntercorrencia",
    "_Evento",
    "formatar_pct",
    "formatar_moeda",
    "intercorrencias_vazias",
    "para_data",
    "datas_validadas",
    "validar_e_extrair_eventos",
    "dias_intersecao",
    "ajuste_vinculo",
    "ajuste_ferias",
    "coletar_afastamentos",
    "descrever_afastamento",
    "ajuste_afastamento",
    "descrever_piso",
    "detalhar_base",
    "ajustar_linha_rh",
    "calcular_ajustes",
    "ajustar_comissao",
    "aplicar_ajustes",
]
