import re
from typing import Any

from app.tools.correcao_tool.dtos import TipoCorrecao, normalizar_tipo

MESES_PT = {
    "jan": 1, "janeiro": 1,
    "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3, "março": 3,
    "abr": 4, "abril": 4,
    "mai": 5, "maio": 5,
    "jun": 6, "junho": 6,
    "jul": 7, "julho": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "setembro": 9,
    "out": 10, "outubro": 10,
    "nov": 11, "novembro": 11,
    "dez": 12, "dezembro": 12,
}


MAPEAMENTO_CARGOS = {
    "vendedor balcao": "200",
    "vendedor balcão": "200",
    "gerente de loja": "150",
    "gerente": "150",
    "vendedor loja": "100",
    "vendedor": "100",
    "assistente de vendas": "300",
    "assistente": "300",
}


def extrair_codigo_ou_valor(texto: str) -> str:
    """Extrai o código numérico ou identificador de uma string como 'loja 5', 'loja 8', 'LOJA-76', '100', 'MATRIC-38 na loja 5'."""
    if not texto:
        return ""
    texto_limpo = texto.strip()
    texto_sem_matricula = re.sub(r"MATRIC-\d+", "", texto_limpo, flags=re.IGNORECASE).strip()
    match = re.search(r"\b(\d+)\b", texto_sem_matricula)
    if match:
        return match.group(1)
    match_orig = re.search(r"\b(\d+)\b", texto_limpo)
    if match_orig:
        return match_orig.group(1)

    t_lower = texto_sem_matricula.lower()
    for cargo_desc, cod in MAPEAMENTO_CARGOS.items():
        if cargo_desc in t_lower:
            return cod

    return texto_limpo


def converter_competencia_para_data(competencia: str) -> tuple[str, str, str]:
    """Converte 'out/2025', '10/2025', '2025-10', 'outubro de 2025' para (date_ref, comp_yyyy_mm, comp_mm_yyyy).

    Exemplos:
        converter_competencia_para_data('out/2025') -> ('2025-10-01', '2025-10', '10/2025')
        converter_competencia_para_data('10/2025') -> ('2025-10-01', '2025-10', '10/2025')
        converter_competencia_para_data('2025-10') -> ('2025-10-01', '2025-10', '10/2025')
    """
    comp = re.sub(r"[\s\-_/]+", " ", competencia.strip().lower())
    ano = 2025
    mes = 10
    match_ano = re.search(r"\b(202\d)\b", comp)
    if match_ano:
        ano = int(match_ano.group(1))

    mes_encontrado = None
    for nome_mes, num_mes in MESES_PT.items():
        if re.search(rf"\b{nome_mes}\b", comp):
            mes_encontrado = num_mes
            break

    if mes_encontrado is None:
        match_mes = re.search(r"\b(0?[1-9]|1[0-2])\b", comp)
        if match_mes:
            mes_encontrado = int(match_mes.group(1))

    if mes_encontrado is not None:
        mes = mes_encontrado

    date_ref = f"{ano:04d}-{mes:02d}-01"
    comp_iso = f"{ano:04d}-{mes:02d}"
    comp_mm_yyyy = f"{mes:02d}/{ano:04d}"
    return date_ref, comp_iso, comp_mm_yyyy


def proximo_mes(date_ref: str) -> str:
    partes = date_ref.split("-")
    ano = int(partes[0])
    mes = int(partes[1])
    if mes == 12:
        return f"{ano + 1:04d}-01-01"
    return f"{ano:04d}-{mes + 1:02d}-01"


def sanitizar_numero(texto: str) -> str:
    t = re.sub(r"[^\d.,]", "", texto.strip())
    if not t:
        return "0.00"
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
        return t
    if "," in t:
        t = t.replace(",", ".")
    return t


def gerar_sql_correcao(
    tipo: str,
    matricula: str,
    competencia: str,
    antes: str,
    depois: str,
    sql_customizado: str | None = None,
) -> tuple[str, list[str]]:
    if sql_customizado and sql_customizado.strip():
        sql_limpo = sql_customizado.strip().rstrip(";") + ";"
        return sql_limpo, ["funcionario_loja", "funcionario"]

    tipo_norm = normalizar_tipo(tipo)
    date_ref, _, _ = converter_competencia_para_data(competencia)
    matricula_limpa = matricula.strip().upper()
    cod_antes = extrair_codigo_ou_valor(antes)
    cod_depois = extrair_codigo_ou_valor(depois)

    if tipo_norm == TipoCorrecao.TRANSFERENCIA_LOJA.value:
        tabelas = ["funcionario_loja", "loja", "funcionario"]
        filtro_antes = (
            f"\n  AND loja_id = (SELECT id FROM loja WHERE cod_loja = '{cod_antes}')"
            if cod_antes
            else ""
        )
        sql = (
            f"UPDATE funcionario_loja\n"
            f"SET loja_id = (SELECT id FROM loja WHERE cod_loja = '{cod_depois}')\n"
            f"WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = '{matricula_limpa}')"
            f"{filtro_antes}\n"
            f"  AND date_ref = '{date_ref}';"
        )
        return sql, tabelas

    if tipo_norm == TipoCorrecao.MUDANCA_CARGO.value:
        tabelas = ["funcionario_cargo", "cargo", "funcionario"]
        filtro_antes = (
            f"\n  AND cargo_id = (SELECT id FROM cargo WHERE cod_cargo = '{cod_antes}')"
            if cod_antes
            else ""
        )
        sql = (
            f"UPDATE funcionario_cargo\n"
            f"SET cargo_id = (SELECT id FROM cargo WHERE cod_cargo = '{cod_depois}')\n"
            f"WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = '{matricula_limpa}')"
            f"{filtro_antes}\n"
            f"  AND date_ref = '{date_ref}';"
        )
        return sql, tabelas

    if tipo_norm == TipoCorrecao.CORRECAO_VENDA.value:
        tabelas = ["venda", "funcionario"]
        fim_mes = proximo_mes(date_ref)
        vlr_valido = sanitizar_numero(depois)
        sql = (
            f"UPDATE venda\n"
            f"SET vlr_venda = {vlr_valido}\n"
            f"WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = '{matricula_limpa}')\n"
            f"  AND date_ref >= '{date_ref}'\n"
            f"  AND date_ref < '{fim_mes}';"
        )
        return sql, tabelas

    if tipo_norm == TipoCorrecao.EXCLUSAO.value:
        tabelas = ["funcionario_loja", "funcionario"]
        sql = (
            f"DELETE FROM funcionario_loja\n"
            f"WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = '{matricula_limpa}')\n"
            f"  AND date_ref = '{date_ref}';"
        )
        return sql, tabelas

    tabelas = ["funcionario_loja", "loja", "funcionario"]
    sql = (
        f"UPDATE funcionario_loja\n"
        f"SET loja_id = (SELECT id FROM loja WHERE cod_loja = '{cod_depois}')\n"
        f"WHERE funcionario_id = (SELECT id FROM funcionario WHERE matricula = '{matricula_limpa}')\n"
        f"  AND date_ref = '{date_ref}';"
    )
    return sql, tabelas
