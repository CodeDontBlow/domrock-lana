"""Saída dos logs da Lana no container (A6-128)."""
import logging

NOME_LOGGER_DA_APP = "app"


def configurar_logs_da_lana() -> None:
    """Mostra no log do container os eventos JSON de nível INFO dos módulos `app.*`.

    Sem handler, o Python só imprime WARNING ou acima, e o evento `rag_indexado` do startup
    sumia (A6-128). Chamar de novo não duplica a saída.

    Ex.: configurar_logs_da_lana()  # no início do main.py
    """
    logger_da_app = logging.getLogger(NOME_LOGGER_DA_APP)
    logger_da_app.setLevel(logging.INFO)
    if logger_da_app.handlers:
        return
    saida = logging.StreamHandler()
    saida.setFormatter(logging.Formatter("%(message)s"))
    logger_da_app.addHandler(saida)
