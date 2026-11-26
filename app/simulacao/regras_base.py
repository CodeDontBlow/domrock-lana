"""Regras base 5c a 5g da apuração de comissões (A6-77).

Módulo fachada (Facade) mantido para retrocompatibilidade total de contratos e testes.
A implementação modular reside no subpacote `app.simulacao.regras`.
"""
from app.simulacao.regras.afastamento import (
    ajuste_afastamento as _ajuste_afastamento,
    coletar_afastamentos as _coletar_afastamentos,
    descrever_afastamento as _descrever_afastamento,
)
from app.simulacao.regras.aplicador import (
    ajustar_comissao,
    ajustar_linha_rh as _ajustar_linha_rh,
    aplicar_ajustes,
    calcular_ajustes,
)
from app.simulacao.regras.ferias import ajuste_ferias as _ajuste_ferias
from app.simulacao.regras.piso import descrever_piso, detalhar_base
from app.simulacao.regras.tipos import (
    COLUNAS_INTERCORRENCIAS,
    PISO_AFASTAMENTO,
    AjusteMatricula,
    RegraAplicada,
    _Evento,
    formatar_moeda as _formatar_moeda,
    formatar_pct as _formatar_pct,
)
from app.simulacao.regras.validacao import (
    datas_validadas as _datas_validadas,
    dias_intersecao as _dias_intersecao,
    intercorrencias_vazias,
    para_data as _para_data,
    validar_e_extrair_eventos as _validar_e_extrair_eventos,
)
from app.simulacao.regras.vinculo import ajuste_vinculo as _ajuste_vinculo

__all__ = [
    "PISO_AFASTAMENTO",
    "COLUNAS_INTERCORRENCIAS",
    "RegraAplicada",
    "AjusteMatricula",
    "_Evento",
    "intercorrencias_vazias",
    "calcular_ajustes",
    "ajustar_comissao",
    "aplicar_ajustes",
    "detalhar_base",
    "descrever_piso",
    # Aliases de compatibilidade
    "_ajustar_linha_rh",
    "_ajuste_vinculo",
    "_ajuste_ferias",
    "_ajuste_afastamento",
    "_coletar_afastamentos",
    "_descrever_afastamento",
    "_dias_intersecao",
    "_validar_e_extrair_eventos",
    "_datas_validadas",
    "_para_data",
    "_formatar_pct",
    "_formatar_moeda",
]
