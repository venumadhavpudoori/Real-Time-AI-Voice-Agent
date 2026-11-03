from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel


class AgentStateEnum(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    CALLING_TOOL = "CALLING_TOOL"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"


class WebSocketMessageType(str, Enum):
    USER_TRANSCRIPT = "user_transcript"
    AGENT_RESPONSE = "agent_response"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"
    STATE_CHANGE = "state_change"
    INTERRUPT = "interrupt"
    AUDIO_CHUNK = "audio_chunk"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class ClientMessage(BaseModel):
    type: WebSocketMessageType
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    session_id: Optional[str] = None


class ServerMessage(BaseModel):
    type: WebSocketMessageType
    state: Optional[AgentStateEnum] = None
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    guardrail_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

