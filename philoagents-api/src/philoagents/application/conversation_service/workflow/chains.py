from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from philoagents.application.conversation_service.workflow.tools import tools
from philoagents.config import settings
from philoagents.domain.prompts import (
    CONTEXT_SUMMARY_PROMPT,
    EXTEND_SUMMARY_PROMPT,
    GUARDRAIL_PROMPT,
    PHILOSOPHER_CHARACTER_CARD,
    PHILOSOPHER_REFUSAL_PROMPT,
    SUMMARY_PROMPT,
)


def get_chat_model(temperature: float = 0.7, model_name: str = settings.GROQ_LLM_MODEL) -> ChatGroq:
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=model_name,
        temperature=temperature,
    )


def get_philosopher_response_chain():
    model = get_chat_model()
    model = model.bind_tools(tools)
    system_message = PHILOSOPHER_CHARACTER_CARD

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message.prompt),
            MessagesPlaceholder(variable_name="messages"),
        ],
        template_format="jinja2",
    )

    return prompt | model


def get_conversation_summary_chain(summary: str = ""):
    model = get_chat_model(model_name=settings.GROQ_LLM_MODEL_SUMMARY)

    summary_message = EXTEND_SUMMARY_PROMPT if summary else SUMMARY_PROMPT

    prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="messages"),
            ("human", summary_message.prompt),
        ],
        template_format="jinja2",
    )

    return prompt | model


def get_context_summary_chain():
    model = get_chat_model(model_name=settings.GROQ_LLM_MODEL_CONTEXT_SUMMARY)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", CONTEXT_SUMMARY_PROMPT.prompt),
        ],
        template_format="jinja2",
    )

    return prompt | model


def get_guardrail_chain():
    # Use context summary model or main model for classification; let's use the main chat model for best accuracy.
    model = get_chat_model(temperature=0.0)  # low temperature for stable classification
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", GUARDRAIL_PROMPT.prompt),
        ],
        template_format="jinja2",
    )
    return prompt | model


def get_refusal_chain():
    model = get_chat_model()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", PHILOSOPHER_REFUSAL_PROMPT.prompt),
        ],
        template_format="jinja2",
    )
    return prompt | model