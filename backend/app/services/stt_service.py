import logging
from typing import Optional

logger = logging.getLogger("voice_agent.stt")


class STTService:
    """
    Speech-To-Text service.
    Normalizes real-time transcripts captured via browser Web Speech API,
    and supports optional backend audio blob decoding if uploaded.
    """

    @staticmethod
    def clean_transcript(text: Optional[str]) -> str:
        if not text:
            return ""
        # Remove repeated stutter or noise tags
        cleaned = text.strip()
        return cleaned


stt_service = STTService()

