from app.agent.state import AgentState
from app.agent.supervisor import agentNode
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver

graph = StateGraph(AgentState)

graph.add_node("agent", agentNode)
graph.set_entry_point("agent")
graph.set_finish_point("agent")

checkpointer = InMemorySaver()

lana = graph.compile(checkpointer=checkpointer)

# Código da CLI alocado temporariamente para fase de testes:
while True:
    print("\nHOMEPAGE")
    thread_id = input("ID da conversa: ").strip()

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    print(f"\nCHAT {thread_id}. | '!q' para voltar.")
    while True:
        user_input = input("\nVocê: ")

        if user_input == "!q":
            break

        print("AI: ", end="")

        lana.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )