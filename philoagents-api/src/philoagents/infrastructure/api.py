import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from opik.integrations.langchain import OpikTracer
from pydantic import BaseModel

from philoagents.application.conversation_service.generate_response import (
    get_response,
    get_streaming_response,
)
from philoagents.application.conversation_service.reset_conversation import (
    reset_conversation_state,
)
from philoagents.application.conversation_service.workflow.state import state_to_str
from philoagents.domain.philosopher_factory import PhilosopherFactory
from .opik_utils import configure

configure()

from philoagents.application.evaluation import log_chat_interaction_to_evidently
from .dashboard import build_dashboard_html


def log_interaction_background(user_query: str, response: str, philosopher_id: str, context: str = ""):
    try:
        log_chat_interaction_to_evidently(
            user_query=user_query,
            generated_response=response,
            philosopher_id=philosopher_id,
            context=context
        )
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    yield
    opik_tracer = OpikTracer()
    opik_tracer.flush()


app = FastAPI(
    lifespan=lifespan,
    title="Philoagents API",
    description="API for the Philoagents philosopher chat application.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    message: str
    philosopher_id: str


@app.get("/dashboard", response_class=HTMLResponse)
async def monitoring_dashboard():
    """Rich monitoring dashboard with hover tooltips."""
    return HTMLResponse(content=build_dashboard_html())


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint — returns a simple HTML status page with links."""
    philosophers = PhilosopherFactory.get_available_philosophers()
    phil_list = "".join(f"<li><code>{p}</code></li>" for p in philosophers)
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>Philoagents API</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0ff; margin: 0; padding: 40px; }}
            h1 {{ color: #a78bfa; font-size: 2rem; margin-bottom: 0; }}
            h2 {{ color: #818cf8; margin-top: 2rem; }}
            .badge {{ display: inline-block; background: #22c55e; color: #fff; border-radius: 6px; padding: 2px 10px; font-size: 0.85rem; margin-left: 12px; vertical-align: middle; }}
            a {{ color: #60a5fa; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            ul {{ line-height: 2; }}
            code {{ background: #1e1e3a; border-radius: 4px; padding: 2px 6px; color: #c4b5fd; }}
            .card {{ background: #1a1a2e; border: 1px solid #2d2d55; border-radius: 12px; padding: 20px 28px; margin-top: 16px; }}
        </style>
    </head>
    <body>
        <h1>🏛️ Philoagents API <span class="badge">● Online</span></h1>
        <p>Backend API for the Philoagents philosopher chat application.</p>

        <div class="card">
            <h2>🔗 Quick Links</h2>
            <ul>
                <li>🎮 <a href="http://localhost:8080" target="_blank">Game UI</a> — Play the philosopher game</li>
                <li>📊 <a href="/dashboard" target="_blank">Monitoring Dashboard</a> — Live metrics with explanations &amp; hover tooltips</li>
                <li>📈 <a href="http://localhost:8085" target="_blank">Evidently Raw UI</a> — Full Evidently dashboard</li>
                <li>📖 <a href="/docs" target="_blank">API Docs (Swagger)</a> — Interactive API documentation</li>
                <li>📋 <a href="/philosophers" target="_blank">Available Philosophers</a> — List of philosophers</li>
            </ul>
        </div>

        <div class="card">
            <h2>🧠 Available Philosophers ({len(philosophers)})</h2>
            <ul>{phil_list}</ul>
        </div>

        <div class="card">
            <h2>📡 Endpoints</h2>
            <ul>
                <li><code>POST /chat</code> — Send a message to a philosopher (REST)</li>
                <li><code>WS /ws/chat</code> — Streaming chat via WebSocket</li>
                <li><code>POST /reset-memory</code> — Reset conversation state</li>
                <li><code>GET /philosophers</code> — List available philosophers</li>
                <li><code>GET /health</code> — Health check</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return html


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "philoagents-api"}


@app.get("/philosophers")
async def list_philosophers():
    """Returns the list of all available philosopher IDs and their names."""
    factory = PhilosopherFactory()
    available_ids = factory.get_available_philosophers()
    philosophers = []
    for pid in available_ids:
        p = factory.get_philosopher(pid)
        philosophers.append({
            "id": p.id,
            "name": p.name,
            "era": p.era,
        })
    return {"philosophers": philosophers, "total": len(philosophers)}


@app.post("/chat")
async def chat(chat_message: ChatMessage):
    try:
        philosopher_factory = PhilosopherFactory()
        philosopher = philosopher_factory.get_philosopher(chat_message.philosopher_id)

        response, latest_state = await get_response(
            messages=chat_message.message,
            philosopher_id=chat_message.philosopher_id,
            philosopher_name=philosopher.name,
            philosopher_perspective=philosopher.perspective,
            philosopher_style=philosopher.style,
            philosopher_era=philosopher.era,
            philosopher_context="",
        )
        context = state_to_str(latest_state)
        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            None,
            log_interaction_background,
            chat_message.message,
            response,
            chat_message.philosopher_id,
            context,
        )
        return {"response": response}
    except Exception as e:
        opik_tracer = OpikTracer()
        opik_tracer.flush()

        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            if "message" not in data or "philosopher_id" not in data:
                await websocket.send_json(
                    {
                        "error": "Invalid message format. Required fields: 'message' and 'philosopher_id'"
                    }
                )
                continue

            try:
                philosopher_factory = PhilosopherFactory()
                philosopher = philosopher_factory.get_philosopher(
                    data["philosopher_id"]
                )

                response_stream = get_streaming_response(
                    messages=data["message"],
                    philosopher_id=data["philosopher_id"],
                    philosopher_name=philosopher.name,
                    philosopher_perspective=philosopher.perspective,
                    philosopher_style=philosopher.style,
                    philosopher_era=philosopher.era,
                    philosopher_context="",
                )

                await websocket.send_json({"streaming": True})

                full_response = ""
                async for chunk in response_stream:
                    full_response += chunk
                    await websocket.send_json({"chunk": chunk})

                await websocket.send_json(
                    {"response": full_response, "streaming": False}
                )

                context = ""
                try:
                    from philoagents.application.conversation_service.generate_response import get_latest_conversation_state
                    latest_state = await get_latest_conversation_state(data["philosopher_id"])
                    if latest_state:
                        context = state_to_str(latest_state)
                except Exception as ex:
                    from loguru import logger
                    logger.warning(f"Error fetching state for live logging: {ex}")

                loop = asyncio.get_running_loop()
                loop.run_in_executor(
                    None,
                    log_interaction_background,
                    data["message"],
                    full_response,
                    data["philosopher_id"],
                    context,
                )

            except Exception as e:
                opik_tracer = OpikTracer()
                opik_tracer.flush()
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        pass


@app.post("/reset-memory")
async def reset_conversation():
    """Resets the conversation state. It deletes the two collections needed for keeping LangGraph state in MongoDB.

    Raises:
        HTTPException: If there is an error resetting the conversation state.
    Returns:
        dict: A dictionary containing the result of the reset operation.
    """
    try:
        result = await reset_conversation_state()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
