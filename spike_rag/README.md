# Spike US-25 (A6-117): RAG + Guardrail Vetorial para a Lana Conversável

> **AVISO IMPORTANTE:** Este diretório é 100% experimental e faz parte da branch isolada `chore/A6-117-spike-rag-lana`. Nenhum código aqui presente deve ser promovido para a branch `develop` ou alterar fluxos produtivos da Lana.

---

## 1. Relatório de Inspeção do Projeto

### 1.1 Provedor de IA e Suporte a Embeddings
- **Configuração Atual (`app/core/config.py` e `.env`):**
  - Provedor configurado: `AI_PROVIDER=OPENROUTER` com modelo `AI_MODEL=openrouter/free`.
  - Suporte implementado na Lana: Gemini (`langchain-google-genai`), OpenRouter (`langchain-openrouter`) e Groq (`langchain-groq`).
- **Suporte a Embeddings:**
  - O pacote `langchain-google-genai` já está instalado e possui a classe `GoogleGenerativeAIEmbeddings` (usando `text-embedding-004`). No entanto, a chave `GEMINI_API_KEY` não está preenchida no `.env` atual.
  - O **OpenRouter** e o **Groq** têm limitações críticas para embeddings na camada gratuita (OpenRouter foca em rotas de chat LLM e Groq não oferece endpoints de embeddings).
- **Recomendação Técnica para o Spike:**
  - Adotar um **modelo local leve de embeddings**:
    - **Opção A (Recomendada):** `fastembed` (ONNX Runtime, ultra-leve, executa na CPU em milissegundos sem dependência do PyTorch).
    - **Opção B:** `sentence-transformers` com modelo multilíngue (`paraphrase-multilingual-MiniLM-L12-v2` ou `all-MiniLM-L6-v2`).
  - **Vantagens:** 100% gratuito, sem limite de requisições por minuto (RPM), sem latência de rede, determinístico e imune a instabilidades de API externa.

---

### 1.2 Configuração do PostgreSQL e Habilitação do `pgvector`
- **Configuração no `domrock-backend/docker-compose.yml`:**
  - Imagem utilizada atualmente: `postgres:16`.
  - Banco de dados: `camplana` na porta `5432`.
  - A imagem oficial padrão do PostgreSQL **não possui** a extensão `pgvector` compilada.
- **Como habilitar o `pgvector` localmente:**
  - **Abordagem recomendada (Drop-in replacement):**
    Substituir a imagem no container local por `pgvector/pgvector:pg16` (imagem oficial mantida pelo time do pgvector compatível com Postgres 16).
    Exemplo no `docker-compose.yml` (ou em um `docker-compose.override.yml`):
    ```yaml
    services:
      postgres:
        image: pgvector/pgvector:pg16
        # Mantém as mesmas portas, volumes e credenciais
    ```
  - **Habilitar a extensão no banco:**
    Executar via cliente SQL conectado ao banco `camplana` como superusuário (`postgres`):
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```
  - **Alternativa para o Spike sem alterar o container do backend:**
    Podemos criar um script de avaliação com banco vetorial embutido (ex: `pgvector` conectado direto ou SQLite com extensão vetorial / ChromaDB em memória) para validar as métricas de precisão antes de tocar no banco.

---

## 2. Base do Experimento: Dataset de Domínio e Perguntas de Teste

O dataset foi estruturado em `dataset.py` e exportado como JSON padronizado em `dataset.json`.

### 2.1 Tópicos de Conhecimento do Domínio (25 tópicos)
Cobrem todas as regras e particularidades do sistema Camplana:
1. **TOP-01:** Papel e Identidade da Lana.
2. **TOP-02:** Limites de Escopo e Assuntos Atendidos.
3. **TOP-03:** Sigilo de Instruções Internas e Segurança do Banco (`lana_leitura`, bloqueio de DDL/DML).
4. **TOP-04:** Limites de Exibição e Agregação de Dados (teto de 10 linhas, preferência por totais e rankings).
5. **TOP-05:** Fluxo de Registro de Parâmetros de Campanha (`registrar_parametros_regra`, painel de revisão).
6. **TOP-06:** Princípio "Uma Conversa, Uma Campanha".
7. **TOP-07:** Parâmetro `periodo` (data_inicio e data_fim).
8. **TOP-08:** Parâmetro `pct_acrescimo` (comissão percentual adicional).
9. **TOP-09:** Parâmetro `marcas_alvo` (`ALL`, 10-PRETO, 20-BRANCO, 30-AZUL, 40-VERMELHO, 50-AMARELO, 60-CINZA).
10. **TOP-10:** Parâmetro `cargos_alvo` (100-VENDEDOR LOJA, 150-GERENTE, 200-VENDEDOR BALCAO, 300-ASSISTENTE DE VENDAS).
11. **TOP-11:** Parâmetro `meta_vendas` (meta financeira monetária em R$).
12. **TOP-12:** Parâmetro Opcional `orcamento_limite` (teto financeiro de incentivo).
13. **TOP-13:** Regra Base 5a (Cálculo padrão sobre percentual vigente de comissão).
14. **TOP-14:** Regra Base 5b (Comissionamento de Gerentes - cargo 150: base na venda total da loja).
15. **TOP-15:** Regra Base 5c (Admissão no mês: proporcional de dias trabalhados).
16. **TOP-16:** Regra Base 5d (Demissão no mês: proporcional até desligamento).
17. **TOP-17:** Regra Base 5e (Afastamento curto de até 15 dias).
18. **TOP-18:** Regra Base 5f (Afastamento longo > 15 dias e licença-maternidade).
19. **TOP-19:** Regra Base 5g (Férias: desconto de dias sem remuneração de comissão).
20. **TOP-20:** Piso Remuneratório de Afastamento (garantia mínima de R$ 3.500,00).
21. **TOP-21:** Simulação Determinística e Execução Isolada (cálculo em Python/Pandas sem alucinação da LLM).
22. **TOP-22:** Janela Temporal e Histórico de Dados (estritamente julho a dezembro de 2025).
23. **TOP-23:** Cenários de Atingimento de Meta (80%, 100%, 120%).
24. **TOP-24:** Contrato de Simulação e Painel Frontend (`Simular campanha`, resumo de custos, pessoas no piso).
25. **TOP-25:** Validação de Consultas com SQLGlot e AST (apenas SELECT validado contra schema oficial).

### 2.2 Conjunto de Avaliação (40 perguntas)
- **20 Perguntas Dentro do Escopo (IN_SCOPE):**
  - Casos reais de comissionamento de gerentes, cálculo de férias, admissão/demissão proporcional, parâmetros obrigatórios de campanha, histórico de vendas de 2025 e cenários de simulação.
- **20 Perguntas Fora do Escopo (OUT_OF_SCOPE):**
  - **10 Neutras:** Receitas, esportes, música, ciências, astronomia, literatura, xadrez, etc.
  - **10 Prompt Injections e Ataques:** Tentativas de jailbreak (DAN), extração do system prompt, extração de senhas do PostgreSQL, comandos maliciosos DDL/DML (`DROP TABLE`, `UPDATE`), criação de malware e listagem massiva de dados pessoais (LGPD).

---

## 3. Como Executar e Exportar o Dataset

Para recriar ou validar o arquivo `dataset.json`:
```bash
python spike_rag/dataset.py
```
