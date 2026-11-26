"""Script de avaliação do guardrail vetorial e calibração de limiar (A6-128)."""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from app.rag.avaliacao.metricas import (
    LinhaLimiar,
    PerguntaRotulada,
    escolher_limiar,
    varrer_limiares,
)
from app.rag.avaliacao.relatorio import (
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
from app.rag.base_vetorial import BaseChroma
from app.rag.embeddings import EmbeddingFastembed
from app.rag.grounding import texto_de_busca
from app.rag.trechos import TrechoBase, carregar_corpus

MODELO_PADRAO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LIMIARES_PADRAO = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]


def carregar_conjunto_perguntas(caminho: Path) -> list[PerguntaRotulada]:
    """Carrega perguntas rotuladas de um arquivo JSON (A6-128).

    Exemplo:
        >>> perguntas = carregar_conjunto_perguntas(Path("perguntas.json"))
        >>> isinstance(perguntas, list)
    """
    if not caminho.exists():
        msg = f"Arquivo não encontrado: {caminho}. Esperado arquivo JSON existente."
        raise FileNotFoundError(msg)

    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    return [PerguntaRotulada(**item) for item in dados]


def filtrar_trechos_por_fonte(
    trechos: list[TrechoBase],
    fontes_csv: str | None,
) -> list[TrechoBase]:
    """Filtra trechos do corpus pelas fontes indicadas em CSV (A6-128).

    Exemplo:
        >>> filtrados = filtrar_trechos_por_fonte(trechos, "especificacao,capacidades")
        >>> all(t.fonte in ["especificacao", "capacidades"] for t in filtrados)
    """
    if not fontes_csv:
        return trechos

    fontes_permitidas = {
        item.strip() for item in fontes_csv.split(",") if item.strip()
    }
    return [t for t in trechos if t.fonte in fontes_permitidas]


def inicializar_base_temporaria(
    pasta_temp: Path,
    trechos: list[TrechoBase],
    modelo: str,
    pasta_cache: Path,
) -> BaseChroma:
    """Inicializa ChromaDB temporário e indexa trechos selecionados (A6-128).

    Exemplo:
        >>> base = inicializar_base_temporaria(Path("/tmp"), trechos, "m", Path("/c"))
    """
    funcao_embedding = EmbeddingFastembed(
        modelo=modelo,
        pasta_cache=pasta_cache,
    )
    base = BaseChroma(pasta=pasta_temp, funcao_embedding=funcao_embedding)
    base.indexar_se_mudou(trechos)
    return base


def buscar_pergunta(
    pergunta: PerguntaRotulada,
    base: BaseChroma,
) -> tuple[float, str, str, float]:
    """Realiza busca vetorial para uma pergunta medindo tempo e distância (A6-128).

    Exemplo:
        >>> dist, item, fonte, lat = buscar_pergunta(p, base)
    """
    historico_msgs = converter_historico(pergunta.historico)
    query = texto_de_busca(pergunta.pergunta, historico_msgs)

    t0 = time.perf_counter()
    encontrados = base.buscar(query, k=1)
    latencia_ms = (time.perf_counter() - t0) * 1000

    if not encontrados:
        return 1.0, "nenhum", "nenhuma", latencia_ms

    primeiro = encontrados[0]
    return primeiro.distancia, primeiro.trecho.item, primeiro.trecho.fonte, latencia_ms


def avaliar_conjunto(
    perguntas: list[PerguntaRotulada],
    base: BaseChroma,
) -> tuple[list[float], list[str], list[str], list[float]]:
    """Avalia uma lista de perguntas contra a base de conhecimento (A6-128).

    Exemplo:
        >>> dists, itens, fontes, lats = avaliar_conjunto(perguntas, base)
    """
    distancias: list[float] = []
    itens: list[str] = []
    fontes: list[str] = []
    latencias: list[float] = []

    for p in perguntas:
        dist, item, fonte, lat = buscar_pergunta(p, base)
        distancias.append(dist)
        itens.append(item)
        fontes.append(fonte)
        latencias.append(lat)

    return distancias, itens, fontes, latencias


def _criar_linha_erro(
    p: PerguntaRotulada, dist: float, item: str, fonte: str, previsto: str,
) -> LinhaErro:
    """Cria objeto LinhaErro para auditoria de falha (A6-128)."""
    return LinhaErro(
        pergunta=p.pergunta, tipo=p.tipo, esperado=p.esperado,
        previsto=previsto, distancia=dist, fonte=fonte, item_proximo=item,
    )


def coletar_erros_teste(
    perguntas: list[PerguntaRotulada],
    distancias: list[float],
    itens: list[str],
    fontes: list[str],
    limiar: float,
) -> list[LinhaErro]:
    """Identifica perguntas cuja classificação divergiu do esperado (A6-128).

    Exemplo:
        >>> erros = coletar_erros_teste(perguntas, distancias, itens, fontes, 0.50)
    """
    erros: list[LinhaErro] = []
    for p, dist, item, fonte in zip(perguntas, distancias, itens, fontes):
        previsto = "dentro" if dist <= limiar else "fora"
        if previsto != p.esperado:
            erros.append(_criar_linha_erro(p, dist, item, fonte, previsto))
    return erros


def montar_relatorio_markdown(
    linhas_calib: list[LinhaLimiar],
    limiar: float,
    linha_teste: LinhaLimiar,
    linhas_tipo: list[LinhaDesempenhoTipo],
    erros: list[LinhaErro],
    latencias: list[float],
) -> str:
    """Monta o documento completo de avaliação em Markdown (A6-128)."""
    stats = calcular_estatisticas_latencia(latencias)
    return (
        f"# Avaliação do Guardrail Vetorial da Lana\n\n"
        f"## 1. Varredura de Limiares (Calibração)\n\n"
        f"{formatar_tabela_limiares(linhas_calib)}\n\n"
        f"**Limiar Escolhido:** `{limiar:.2f}`\n\n"
        f"## 2. Desempenho no Conjunto de Teste\n\n"
        f"{formatar_tabela_teste(linha_teste)}\n\n"
        f"## 3. Desempenho por Tipo de Pergunta (Teste)\n\n"
        f"{formatar_tabela_por_tipo(linhas_tipo)}\n\n"
        f"## 4. Discordâncias no Conjunto de Teste\n\n"
        f"{formatar_tabela_erros(erros)}\n\n"
        f"## 5. Latência de Inferência e Busca\n\n"
        f"{formatar_estatisticas_latencia(stats)}"
    )


def imprimir_relatorio_completo(
    linhas_calibracao: list[LinhaLimiar],
    limiar_escolhido: float,
    linha_teste: LinhaLimiar,
    linhas_tipo: list[LinhaDesempenhoTipo],
    erros: list[LinhaErro],
    latencias_totais: list[float],
) -> None:
    """Imprime relatório de avaliação formatado em Markdown (A6-128).

    Exemplo:
        >>> imprimir_relatorio_completo(linhas, 0.5, linha_t, l_tipo, erros, lats)
    """
    relatorio = montar_relatorio_markdown(
        linhas_calibracao, limiar_escolhido, linha_teste,
        linhas_tipo, erros, latencias_totais,
    )
    print(relatorio)


def criar_argumentos() -> argparse.ArgumentParser:
    """Configura e retorna os argumentos de linha de comando (A6-128)."""
    parser = argparse.ArgumentParser(
        description="Avalia limiares do guardrail vetorial da Lana (A6-128)."
    )
    parser.add_argument(
        "--fontes",
        type=str,
        default=None,
        help="Fontes do corpus separadas por vírgula (ex.: especificacao,capacidades)",
    )
    parser.add_argument(
        "--calibracao",
        type=Path,
        default=Path("app/rag/avaliacao/perguntas_calibracao.json"),
        help="Caminho do JSON com perguntas de calibração",
    )
    parser.add_argument(
        "--teste",
        type=Path,
        default=Path("app/rag/avaliacao/perguntas_teste.json"),
        help="Caminho do JSON com perguntas de teste",
    )
    parser.add_argument(
        "--modelo",
        type=str,
        default=MODELO_PADRAO,
        help="Nome do modelo fastembed",
    )
    parser.add_argument(
        "--pasta-modelo",
        type=Path,
        default=None,
        help="Diretório de cache de modelos (padrão: RAG_PASTA_MODELO ou data/modelos)",
    )
    return parser


def _executar_avaliacao(
    calibracao: list[PerguntaRotulada],
    teste: list[PerguntaRotulada],
    base: BaseChroma,
) -> None:
    """Executa a calibração, teste e impressão do relatório (A6-128)."""
    dists_calib, _, _, lats_calib = avaliar_conjunto(calibracao, base)
    linhas_calib = varrer_limiares(calibracao, dists_calib, LIMIARES_PADRAO)
    limiar_escolhido = escolher_limiar(linhas_calib)

    dists_teste, itens_teste, fontes_teste, lats_teste = avaliar_conjunto(teste, base)
    linha_teste = varrer_limiares(teste, dists_teste, [limiar_escolhido])[0]
    linhas_tipo = calcular_desempenho_por_tipo(teste, dists_teste, limiar_escolhido)
    erros = coletar_erros_teste(
        teste, dists_teste, itens_teste, fontes_teste, limiar_escolhido
    )

    imprimir_relatorio_completo(
        linhas_calibracao=linhas_calib,
        limiar_escolhido=limiar_escolhido,
        linha_teste=linha_teste,
        linhas_tipo=linhas_tipo,
        erros=erros,
        latencias_totais=lats_calib + lats_teste,
    )


def main() -> None:
    """Ponto de entrada do script de avaliação do guardrail (A6-128)."""
    parser = criar_argumentos()
    args = parser.parse_args()

    calibracao = carregar_conjunto_perguntas(args.calibracao)
    teste = carregar_conjunto_perguntas(args.teste)
    trechos = filtrar_trechos_por_fonte(carregar_corpus(), args.fontes)

    pasta_cache = args.pasta_modelo or Path(
        os.environ.get("RAG_PASTA_MODELO", "data/modelos")
    )
    with tempfile.TemporaryDirectory(prefix="chroma_avaliacao_") as tmp_dir:
        base = inicializar_base_temporaria(
            pasta_temp=Path(tmp_dir),
            trechos=trechos,
            modelo=args.modelo,
            pasta_cache=pasta_cache,
        )
        _executar_avaliacao(calibracao, teste, base)


if __name__ == "__main__":
    main()
