"""Testes de fatiamento estrutural e carregamento do corpus (A6-128)."""
import pytest
from pathlib import Path

from app.rag.trechos import (
    FONTES_VALIDAS,
    PASTA_CORPUS,
    TrechoBase,
    carregar_corpus,
    fatiar_por_secao,
    hash_do_corpus,
)


def test_fatiar_por_secao_gera_um_trecho_por_item():
    md = "## 5b — Gerente\nVenda total da loja.\n\n## 5c — Admissão\nCalculado proporcionalmente aos dias."
    trechos = fatiar_por_secao(md, "especificacao")
    assert [t.id for t in trechos] == ["especificacao:5b", "especificacao:5c"]
    assert trechos[1].titulo == "Admissão" and "proporcionalmente" in trechos[1].texto


def test_corpus_real_tem_as_regras_5a_a_5g():
    ids = {t.id for t in carregar_corpus()}
    assert {f"especificacao:5{letra}" for letra in "abcdefg"} <= ids


def test_hash_do_corpus_muda_quando_um_texto_muda():
    t1 = TrechoBase(id="especificacao:5a", fonte="especificacao", item="5a", titulo="Geral", texto="Texto original")
    t2 = TrechoBase(id="especificacao:5a", fonte="especificacao", item="5a", titulo="Geral", texto="Texto alterado")
    assert hash_do_corpus([t1]) != hash_do_corpus([t2])
    assert hash_do_corpus([t1]) == hash_do_corpus([t1])


def test_fatiar_texto_sem_secao_levanta_erro_com_o_inicio_do_texto():
    texto_sem_secao = "Este é um texto comum sem qualquer cabeçalho de seção."
    with pytest.raises(ValueError) as exc:
        fatiar_por_secao(texto_sem_secao, "especificacao")
    mensagem = str(exc.value)
    assert texto_sem_secao[:40] in mensagem
    assert "## <item> — <título>" in mensagem


def test_fonte_invalida_levanta_value_error_com_lista_aceita(tmp_path: Path):
    arquivo_invalido = tmp_path / "desconhecido.md"
    arquivo_invalido.write_text("## item-1 — Titulo\nTexto.", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        carregar_corpus(pasta=tmp_path)
    mensagem = str(exc.value)
    assert "desconhecido" in mensagem
    assert all(f in mensagem for f in FONTES_VALIDAS)


def test_fatiar_com_fonte_invalida_levanta_value_error():
    with pytest.raises(ValueError) as exc:
        fatiar_por_secao("## item-1 — Titulo\nTexto.", "fonte_inexistente")
    mensagem = str(exc.value)
    assert "fonte_inexistente" in mensagem


def test_fonte_estrategias_e_valida():
    assert "estrategias" in FONTES_VALIDAS


def test_carregar_corpus_carrega_todas_as_fontes_com_ids_minimos():
    trechos = carregar_corpus()
    ids = {t.id for t in trechos}
    assert "especificacao:5c" in ids
    assert "capacidades:pedidos-campanha" in ids
    assert "esclarecimentos:atualizacao-mensal-bases" in ids
    assert "glossario:cargo-100" in ids
    assert "estrategias:estrategia-objetivo" in ids


def test_capacidades_tem_item_pedidos_campanha():
    trechos = carregar_corpus()
    pedidos = [t for t in trechos if t.id == "capacidades:pedidos-campanha"]
    assert len(pedidos) == 1
    texto = pedidos[0].texto
    assert "Black Friday" in texto
    assert "registra" in texto and "simula" in texto

