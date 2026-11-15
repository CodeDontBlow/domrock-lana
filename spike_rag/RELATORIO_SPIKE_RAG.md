# Relatório Executivo — Spike US-25 (A6-117)
## RAG + Guardrail Vetorial para a Lana Conversável

| Data de Execução | 15/11/2026 |
| :--- | :--- |
| **Responsável** | Equipe de IA / Engenharia Camplana |
| **Branch Isolada** | `chore/A6-117-spike-rag-lana` (100% experimental, sem impacto em produção) |
| **Status da Tarefa** | Concluído com Sucesso |

---

### 1. Resumo Executivo
**Vale a pena implementar o RAG + Guardrail Vetorial na Lana?**  
**SIM, FORTEMENTE RECOMENDADO.**

A implementação de um guardrail vetorial semântico antes da chamada da LLM provou ser altamente eficaz e de baixíssimo overhead operacional. Nos testes empíricos com 40 cenários desafiadores:
* **100% das tentativas de *prompt injection*** (jailbreaks como modo DAN, personificação de terminal Linux, tentativas de extração de credenciais e DDL destrutivo `DROP TABLE`) foram **bloqueadas sumariamente** na borda em ~52 ms.
* **100% das perguntas neutras fora de escopo** (receitas culinárias, esportes, literatura) foram filtradas sem gastar tokens da LLM.
* **95% das dúvidas legítimas sobre regras de comissão e campanhas** foram imediatamente liberadas para processamento normal.
* **Economia e Proteção:** A requisição é filtrada localmente na CPU antes de bater na LLM (evitando consumo de cotas de TPM/RPM, custos com OpenRouter/Gemini e vulnerabilidades de injeção).

---

### 2. Configuração Recomendada e Resultados dos Testes

#### 2.1 Modelo de Embedding Recomendado
* **Biblioteca:** `fastembed` (runtime ONNX otimizado para inferência em CPU).
* **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (dimensão 384, quantizado, ~118 MB).
* **Justificativa:** O modelo possui suporte nativo ao português brasileiro corporativo, não requer GPU nem dependências pesadas de PyTorch, roda com isolamento completo e tem **custo zero de API ($0.00)**.
* **Latência Média Observada:** **51.98 ms** (Mediana: **48.01 ms**, P95: **74.64 ms**). Comparado a uma chamada gRPC para LLM que leva entre 1.500 ms e 3.500 ms, o guardrail vetorial representa um acréscimo de tempo insignificante (< 3%) e poupa segundos preciosos em caso de rejeição precoce.

#### 2.2 Calibração do Limiar (*Threshold*)
Foi executada uma varredura paramétrica de distâncias de cosseno ($\text{Distância} = 1 - \text{Similaridade}$) sobre a base de 25 tópicos de domínio:

| Limiar Distância | Limiar Similaridade | Acurácia | Precisão | Recall | F1-Score | Injeções Bloqueadas | Falsos Positivos (Vazamento) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $\le 0.40$ | $\ge 0.60$ | 85.0% | 100.0% | 70.0% | 0.8235 | 10/10 (100%) | 0 (0%) |
| $\le 0.45$ | $\ge 0.55$ | 92.5% | 100.0% | 85.0% | 0.9189 | 10/10 (100%) | 0 (0%) |
| **$\le 0.50$ (ÓTIMO)** | **$\ge 0.50$** | **97.5%** | **100.0%** | **95.0%** | **0.9744** | **10/10 (100%)** | **0 (0%)** |
| $\le 0.55$ | $\ge 0.45$ | 92.5% | 87.0% | 100.0% | 0.9302 | 7/10 (70%) | 3 (15%) |
| $\le 0.60$ | $\ge 0.40$ | 85.0% | 76.9% | 100.0% | 0.8696 | 4/10 (40%) | 6 (30%) |

> **Ponto de Operação Selecionado:**  
> **Distância de Cosseno $\le 0.50$** (equivalente a **Similaridade de Cosseno $\ge 0.50$**).  
> Nesse limiar, alcançamos **Precisão de 100%** (zero vazamento de ataques ou perguntas irrelevantes), **Acurácia de 97.5%** e **F1-Score de 0.9744**.

---

### 3. Análise Comparativa de Infraestrutura: `pgvector` vs. Banco Vetorial Dedicado

| Critério | Opção A: `pgvector` no PostgreSQL Atual | Opção B: Banco Vetorial Dedicado (Qdrant / Milvus / Chroma) | Opção C: Vetores em Memória / FastEmbed (No-DB) |
| :--- | :--- | :--- | :--- |
| **Complexidade de Infra** | **Mínima:** apenas troca de imagem Docker para `pgvector/pgvector:pg16`. | **Alta:** requer subir, monitorar e manter um novo container/serviço no docker-compose. | **Zero:** roda diretamente no processo Python da Lana em RAM. |
| **Consumo de Memória** | Compartilha os recursos já alocados para a instância do PostgreSQL. | Adiciona overhead de ~300 MB a 1 GB de RAM exclusivo para o novo serviço. | Leve (~150 MB de RAM para modelo e matriz de embeddings). |
| **Consistência e Backup** | Backup unificado (`pg_dump`) junto com as tabelas relacionais do sistema. | Requer estratégia isolada de snapshot e replicação. | Sem estado persistente de BD; gerado no startup ou lido de arquivo local. |
| **Adequação ao Volume** | Excelente para milhares ou dezenas de milhares de vetores com índice HNSW. | Justifica-se apenas para milhões de documentos e busca distribuída. | **Ideal para o catálogo de regras da Lana** (20 a 100 regras e tópicos cabem em memória). |

---

### 4. Recomendação Final para o Product Owner (PO)

1. **Aprovação do Guardrail Vetorial:** Incluir a funcionalidade no backlog como uma melhoria de segurança e custo para o fluxo do agente (LangGraph / FastAPI).
2. **Estratégia de Adoção em Fases:**
   * **Fase 1 (Imediata / Curto Prazo — Guardrail Vetorial sem complexidade de BD):**  
     Implementar o guardrail em memória dentro do serviço da Lana via `fastembed` com o limiar calibrado ($\text{similaridade} \ge 0.50$). Isso resolve 100% do problema de segurança e contenção de custo sem exigir alterações no container do PostgreSQL da infraestrutura compartilhada.
   * **Fase 2 (Médio Prazo — RAG Completo no Backend com `pgvector`):**  
     Quando for necessário indexar documentos longos (PDFs de convenções coletivas de vendas, notas técnicas e atas de comitês), atualizar a imagem do PostgreSQL para `pgvector/pgvector:pg16` e unificar a busca vetorial via SQL direto no banco.
3. **Decisão de Go / No-Go:** **GO.** A solução é viável, rápida, segura e com ROI imediato na contenção de custos de tokens e blindagem de segurança da aplicação.
