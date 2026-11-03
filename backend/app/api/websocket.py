import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.database import get_db
from app.schemas.agent import (
    ClientMessage, 
    ServerMessage, 
    WebSocketMessageType, 
    AgentStateEnum
)
from app.services.agent_service import agent_service

logger = logging.getLogger("voice_agent.websocket")
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/voice-agent")
async def voice_agent_websocket(
    websocket: WebSocket,
    session_id: str = Query("default-session")
):
    await websocket.accept()
    logger.info(f"WebSocket client connected: session_id={session_id}")

    # Helper function to emit structured JSON to frontend
    async def emit_server_message(msg: ServerMessage):
        try:
            await websocket.send_text(msg.model_dump_json())
        except Exception as err:
            logger.error(f"Error sending message over WebSocket: {err}")

    # Initial handshake
    await emit_server_message(ServerMessage(
        type=WebSocketMessageType.STATE_CHANGE,
        state=AgentStateEnum.LISTENING,
        text="Connected to Grand Bistro Voice Concierge. Ready for voice interaction."
    ))

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
                msg_type = payload.get("type")
            except Exception:
                logger.warning(f"Malformed WS payload: {raw_data}")
                continue

            # Handle PING
            if msg_type == WebSocketMessageType.PING:
                await emit_server_message(ServerMessage(type=WebSocketMessageType.PONG))
                continue

            # Handle Barge-in / Interruption
            if msg_type == WebSocketMessageType.INTERRUPT:
                async for db in get_db():
                    await agent_service.handle_interruption(session_id, emit_server_message, db=db)
                continue

            # Handle Incoming Speech Transcript
            if msg_type == WebSocketMessageType.USER_TRANSCRIPT:
                transcript_text = payload.get("text", "")
                if transcript_text:
                    async for db in get_db():
                        await agent_service.process_user_speech(
                            session_id=session_id,
                            raw_text=transcript_text,
                            emit_func=emit_server_message,
                            db=db
                        )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: session_id={session_id}")
    except Exception as exc:
        logger.error(f"WebSocket unhandled exception: {exc}")

