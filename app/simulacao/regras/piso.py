"""Regras de negócio de piso salarial garantido e detalhamento das regras base 5a e 5b."""
import pandas as pd

from app.simulacao.regras.tipos import PISO_AFASTAMENTO, RegraAplicada, formatar_moeda, formatar_pct


def descrever_piso(comissao_sem_piso: float) -> RegraAplicada:
    """Descreve a aplicação do piso de afastamento frente à comissão. Ex.: descrever_piso(600.0)"""
    fixo, comiss = formatar_moeda(PISO_AFASTAMENTO), formatar_moeda(comissao_sem_piso)
    if comissao_sem_piso < PISO_AFASTAMENTO:
        return RegraAplicada("piso", f"piso — recebe o fixo de {fixo} (a comissão daria {comiss})")
    return RegraAplicada("piso", f"piso — recebe a comissão de {comiss} (acima do fixo de {fixo})")


def detalhar_base(linha_apuracao: pd.Series) -> list[RegraAplicada]:
    """5a sempre; 5b quando cod_cargo == '150'. Ex.: detalhar_base(linha)"""
    pct = formatar_pct(float(linha_apuracao["pct_comiss"]))
    regras = [RegraAplicada("5a", f"5a — % da base: {pct}")]
    if str(linha_apuracao["cod_cargo"]) == "150":
        regras.append(RegraAplicada("5b", f"5b — base: venda total da loja {linha_apuracao['cod_loja']}"))
    return regras
