from langchain_core.messages import RemoveMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode

from pharma_agent.application.conversation_service.workflow.chains import (
    get_context_summary_chain,
    get_conversation_summary_chain,
    get_philosopher_response_chain,
    get_guardrail_chain,
    get_refusal_chain,
)
from pharma_agent.application.conversation_service.workflow.state import PhilosopherState
from pharma_agent.application.conversation_service.workflow.tools import tools
from pharma_agent.config import settings

retriever_node = ToolNode(tools)


async def guardrail_node(state: PhilosopherState, config: RunnableConfig):
    import json
    
    # Grab the latest user message
    user_query = state["messages"][-1].content
    
    # Run the guardrail classification
    guardrail_chain = get_guardrail_chain()
    classification_response = await guardrail_chain.ainvoke(
        {
            "philosopher_name": state["philosopher_name"],
            "philosopher_era": state["philosopher_era"],
            "user_query": user_query,
        },
    )
    
    classification_text = classification_response.content.strip()
    
    # Clean classification_text in case it has markdown backticks
    if classification_text.startswith("```"):
        lines = classification_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        classification_text = "\n".join(lines).strip()
        
    try:
        result = json.loads(classification_text)
        violates = result.get("violates_guardrail", False)
        reason = result.get("reason", "")
    except Exception:
        # Fallback if parsing fails
        violates = False
        reason = ""
        
    if violates:
        # Generate the in-character refusal
        refusal_chain = get_refusal_chain()
        refusal_response = await refusal_chain.ainvoke(
            {
                "philosopher_name": state["philosopher_name"],
                "philosopher_style": state["philosopher_style"],
                "user_query": user_query,
                "reason": reason,
            },
        )
        
        return {
            "guardrail_violated": True,
            "messages": [AIMessage(content=refusal_response.content)],
        }
        
    return {
        "guardrail_violated": False,
    }



async def conversation_node(state: PhilosopherState, config: RunnableConfig):
    summary = state.get("summary", "")
    conversation_chain = get_philosopher_response_chain()

    response = await conversation_chain.ainvoke(
        {
            "messages": state["messages"],
            "philosopher_context": state["philosopher_context"],
            "philosopher_name": state["philosopher_name"],
            "philosopher_perspective": state["philosopher_perspective"],
            "philosopher_style": state["philosopher_style"],
            "summary": summary,
        },
        config,
    )
    
    return {"messages": response}


async def summarize_conversation_node(state: PhilosopherState):
    summary = state.get("summary", "")
    summary_chain = get_conversation_summary_chain(summary)

    response = await summary_chain.ainvoke(
        {
            "messages": state["messages"],
            "philosopher_name": state["philosopher_name"],
            "summary": summary,
        }
    )

    delete_messages = [
        RemoveMessage(id=m.id)
        for m in state["messages"][: -settings.TOTAL_MESSAGES_AFTER_SUMMARY]
    ]
    return {"summary": response.content, "messages": delete_messages}


async def summarize_context_node(state: PhilosopherState):
    context_summary_chain = get_context_summary_chain()

    response = await context_summary_chain.ainvoke(
        {
            "context": state["messages"][-1].content,
        }
    )
    state["messages"][-1].content = response.content

    return {}


async def connector_node(state: PhilosopherState):
    return {}