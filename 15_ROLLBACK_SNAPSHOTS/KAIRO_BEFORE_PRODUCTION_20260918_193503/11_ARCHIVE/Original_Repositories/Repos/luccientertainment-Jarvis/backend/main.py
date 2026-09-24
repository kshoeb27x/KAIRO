from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import asyncio
from datetime import datetime, timedelta, timezone

# Absolute pathing for reliable imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.modules.agents.gmail_agent import start_gmail_agent, stop_gmail_agent
from backend.modules.agents.research_agent import ResearchAgent
from backend.modules.research.research_tool import set_research_agent
from backend.modules.google.gmail_storage import get_inbox
from backend.modules.google.calendar_tool import get_calendar_summary


# Background task references
gmail_task = None
startup_task = None

# Agent instances
research_agent = None

calendar_summary_cache = {
    "data": None,
    "updated_at": None,
}

CALENDAR_CACHE_MINUTES = 15

def get_gmail_summary():
    inbox = get_inbox()

    if not isinstance(inbox, list):
        inbox = []

    return {
        "unread_count": len(inbox),
    }

def get_cached_calendar_summary(force_refresh: bool = False):
    now = datetime.now(timezone.utc)

    cached_data = calendar_summary_cache.get("data")
    updated_at = calendar_summary_cache.get("updated_at")

    cache_is_valid = (
        cached_data is not None
        and updated_at is not None
        and now - updated_at < timedelta(minutes=CALENDAR_CACHE_MINUTES)
    )

    if cache_is_valid and not force_refresh:
        return cached_data

    fresh_summary = get_calendar_summary()

    calendar_summary_cache["data"] = fresh_summary
    calendar_summary_cache["updated_at"] = now

    return fresh_summary

async def delayed_agent_startup():
    global gmail_task
    global research_agent

    try:
        # Create the research agent when Jarvis starts.
        # If active_research.json contains unfinished work, ResearchAgent will resume it automatically.
        research_agent = ResearchAgent()
        set_research_agent(research_agent)

        # Delay Gmail startup so the backend/UI can finish loading first.
        await asyncio.sleep(5)
        gmail_task = await start_gmail_agent()

    except asyncio.CancelledError:
        print("Startup: Delayed agent startup cancelled.")
        raise


async def cancel_task(task):
    if task is None or task.done():
        return

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_task

    startup_task = asyncio.create_task(delayed_agent_startup())

    try:
        yield

    finally:
        # Handles Ctrl+C during the initial startup delay.
        await cancel_task(startup_task)

        # Handles Ctrl+C after the Gmail polling loop has started.
        if gmail_task:
            await stop_gmail_agent(gmail_task)


app = FastAPI(lifespan=lifespan)

async def broadcast_message(message: dict):
    disconnected = []

    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        connected_clients.discard(client)


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# UI state
connected_clients = set()
current_status = "idle"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global current_status

    await websocket.accept()
    connected_clients.add(websocket)

    await websocket.send_json({"status": current_status})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception:
        connected_clients.discard(websocket)


async def broadcast_status(status: str):
    global current_status

    current_status = status
    disconnected = []

    for client in connected_clients:
        try:
            await client.send_json({"status": status})
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        connected_clients.discard(client)


@app.get("/status")
async def get_status():
    return {"status": current_status}


@app.get("/trigger-listening")
async def trigger_listening():
    await broadcast_status("listening")
    return {"ok": True, "status": current_status}


@app.get("/trigger-thinking")
async def trigger_thinking():
    await broadcast_status("thinking")
    return {"ok": True, "status": current_status}


@app.get("/trigger-speaking")
async def trigger_speaking():
    await broadcast_status("speaking")
    return {"ok": True, "status": current_status}


@app.get("/trigger-idle")
async def trigger_idle():
    await broadcast_status("idle")
    return {"ok": True, "status": current_status}


@app.get("/trigger-email-check")
async def trigger_email_check():
    await broadcast_status("checking-email")
    return {"ok": True, "status": current_status}


@app.get("/trigger-finish-tasks")
async def trigger_finish_tasks():
    global research_agent

    await broadcast_status("thinking")

    # Safety fallback in case the startup task has not created it yet.
    # Creating ResearchAgent will automatically resume unfinished research if active_research.json has a running status.
    if research_agent is None:
        research_agent = ResearchAgent()

    message = research_agent.get_status()

    await broadcast_status("idle")

    return {
        "ok": True,
        "message": message,
        "status": current_status,
    }


@app.get("/research/status")
async def research_status():
    global research_agent

    if research_agent is None:
        research_agent = ResearchAgent()

    return {
        "ok": True,
        "message": research_agent.get_status(),
    }

@app.get("/research/show-completed")
async def show_completed_research():
    global research_agent

    if research_agent is None:
        research_agent = ResearchAgent()
        set_research_agent(research_agent)

    history = research_agent.list_completed_research()

    items = []

    for item in history:
        report = item.get("report", "")
        items.append({
            "topic": item.get("topic", "Untitled research"),
            "summary": item.get("summary") or item.get("report", "")[:350],
            "report": item.get("report", ""),
            "facts": item.get("facts", []),
            "sources": item.get("sources", []),
            "created_at": item.get("created_at", "unknown date"),
        })

    await broadcast_message({
        "type": "show_completed_research",
        "items": items,
    })

    await broadcast_message({
        "type": "research_summary",
        **research_agent.get_research_summary(),
    })
    return {
        "ok": True,
        "count": len(items),
    }

@app.get("/research/close")
async def close_research():

    await broadcast_message({
        "type": "home"
    })

    return {"ok": True}    

@app.get("/research/summary")
async def research_summary():
    global research_agent

    if research_agent is None:
        research_agent = ResearchAgent()
        set_research_agent(research_agent)

    return {
        "ok": True,
        **research_agent.get_research_summary(),
    }

@app.get("/gmail/summary")
async def gmail_summary():
    return {
        "ok": True,
        **get_gmail_summary(),
    }


@app.get("/gmail/refresh-summary")
async def refresh_gmail_summary():
    summary = get_gmail_summary()

    await broadcast_message({
        "type": "gmail_summary",
        **summary,
    })

    return {
        "ok": True,
        **summary,
    }

@app.get("/calendar/summary")
async def calendar_summary():
    return {
        "ok": True,
        **get_cached_calendar_summary(force_refresh=False),
    }


@app.get("/calendar/refresh-summary")
async def refresh_calendar_summary():
    summary = get_cached_calendar_summary(force_refresh=True)

    await broadcast_message({
        "type": "calendar_summary",
        **summary,
    })

    return {
        "ok": True,
        **summary,
    }