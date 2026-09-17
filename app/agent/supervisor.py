from app.agent.state import AgentState, llm

def agentNode(state: AgentState) -> AgentState:
    """This is the AI Agent node"""
    AgentRes = llm.stream(state["messages"])

    # Iterando sob os chunks da resposta da AI
    full = None
    for chunk in AgentRes:
        full = chunk if full is None else full + chunk

        if chunk.content:
            print(chunk.content, end="", flush=True)

    return {"messages": [full]}