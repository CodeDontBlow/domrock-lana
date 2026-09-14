# Camplana - Lana
Servidor simples para hospedar Lana, o agente AI do projeto CamplanaAI! Utiliza FastAPI para hospedagem e LangGraph para gerenciar o agente.

## 📂 Estrutura do Projeto
```text
lana-ai/ 
├── app/ 
│   ├── main.py                 # Ponto de entrada da API FastAPI (rotas chamadas pelo SpringBoot) 
│   ├── core/ 
│   │   └── config.py           # Configurações de API Keys (Gemini) e variáveis de ambiente 
│   ├── agent/                  # Lógica do LangGraph
│   │   ├── state.py            # Definição da classe de Estado (AgentState) 
│   │   ├── supervisor.py       # Nó Router / Supervisor (deliberação e decisão de rotas) 
│   │   └── graph.py            # Construção do Grafo de Estados do LangGraph 
│   ├── tools/                  # Definição e Pydantic Schemas das Tools 
│   │   ├── query_tool.py      # Chamadas HTTP para os endpoints da API Java 
│   │   ├── code_tool.py       # Gerador, parser (AST) e executor do código Python 
│   │   └── slot_fill.py        # Ferramenta para comunicação fácil com usuário
│   └── schemas/                # DTOs de entrada/saída HTTP (Pydantic) 
├── requirements.txt
├── env.example
└── README.md
```

## ⌨️ Executando
Clone o repositório, acesse a raiz e rode os seguinte comandos:
```bash 
python -m venv venv
.\venv\Scripts\activate             #CMD
source venv/bin/activate            #bash

python -m pip install -r requirements.txt
uvicorn main:app --reload           #localhost:8000
```