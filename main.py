import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.agent.router import router as agent_router
from app.simulacao.router import router as simulacao_router
from app.grpc_server import serve_grpc  # Ajusta o caminho para onde está a tua função serve_grpc
from app.core.config import get_settings
from app.core.logs import configurar_logs_da_lana
from app.rag.base_vetorial import iniciar_base_conhecimento, obter_base_conhecimento
from app.rag.trechos import carregar_corpus

# A6-128: sem isso, os eventos JSON de nível INFO (ex.: rag_indexado) não aparecem no log.
configurar_logs_da_lana()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # A6-128: Indexação da base de conhecimento no startup antes do gRPC quando RAG_ATIVO
    settings = get_settings()
    if settings.RAG_ATIVO:
        await asyncio.to_thread(iniciar_base_conhecimento, obter_base_conhecimento, carregar_corpus)

    # Inicia o servidor gRPC em background
    grpc_task = asyncio.create_task(serve_grpc())
    print("Servidor gRPC iniciado na porta 50051")
    
    yield  # Mantém o FastAPI e as rotas HTTP a rodar normalmente
    
    # Encerra o gRPC ao desligar a aplicação
    grpc_task.cancel()
    try:
        await grpc_task
    except asyncio.CancelledError:
        print("Servidor gRPC encerrado")

app = FastAPI(title="lana-ai", lifespan=lifespan)

# Mantém todos os teus routers HTTP ativos
app.include_router(agent_router)
app.include_router(simulacao_router)

@app.get("/")
def read_root():
    return {
        "status": "lana-ai is running",
        "grpc": "active on port 50051"
    }