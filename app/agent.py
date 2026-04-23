from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState

from app.config import settings


def build_agent():
    llm = ChatOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        model=settings.model_name,
    )

    def call_llm(state: MessagesState):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("call_llm", call_llm)
    graph.add_edge(START, "call_llm")
    graph.add_edge("call_llm", END)

    return graph.compile()


agent = build_agent()
