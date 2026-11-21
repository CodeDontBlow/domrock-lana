"""Funções de amostragem de dados para o contexto de IA e identificação do modelo."""
import pandas as pd

from app.core.config import get_settings
from app.simulacao.bases import BasesSimulacao

LINHAS_AMOSTRA: int = 10


def amostra_vendas(vendas: pd.DataFrame) -> pd.DataFrame:
    """Metade do início e metade do fim por data, para mostrar datas reais além do dia 1º."""
    ordenadas = vendas.sort_values("data_venda")
    metade = LINHAS_AMOSTRA // 2
    return pd.concat([ordenadas.head(metade), ordenadas.tail(metade)])


def amostras(bases: BasesSimulacao, baseline: pd.DataFrame) -> dict[str, str]:
    """Gera CSV de amostra de cada tabela relevante para alimentar o prompt do gerador de código."""
    tabelas = {**bases.como_dict(), "vendas": amostra_vendas(bases.vendas), "apuracao_base": baseline}
    return {nome: tabela.head(LINHAS_AMOSTRA).to_csv(index=False) for nome, tabela in tabelas.items()}


def modelo_da_ia(origem: str, observacao: str, usou_referencia_str: str) -> str:
    """Retorna o modelo que escreveu o código, ou a origem do código fixo (ex.: 'modelo')."""
    # Com USOU_REFERENCIA o código aprovado é o fixo, mas quem divergiu nas tentativas foi a IA.
    if origem in ("llm", "fake") or usou_referencia_str in observacao:
        return get_settings().AI_MODEL
    return origem
