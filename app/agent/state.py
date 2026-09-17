from app.core.config import ENV
from typing import TypedDict, Annotated
from langchain.messages import HumanMessage
from langgraph.graph.message import add_messages
from langchain_openrouter import ChatOpenRouter

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

llm = ChatOpenRouter(
    model="openai/gpt-4o-mini",
    api_key=ENV.OPENROUTER_API_KEY,
)