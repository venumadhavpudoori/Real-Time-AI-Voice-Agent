import io
import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from gtts import gTTS

logger = logging.getLogger("voice_agent.tts")

_AUDIO_CACHE = {}
_executor = ThreadPoolExecutor(max_workers=2)


def _generate_mp3_bytes(clean_text: str, lang: str = "en") -> str:
    try:
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return base64.b64encode(fp.read()).decode("utf-8")
    except Exception as exc:
        logger.debug(f"gTTS network audio generation skipped: {exc}")
        return ""


class TTSService:
    """Text-to-Speech service converting agent dialogue into audio streams."""

    @staticmethod
    def synthesize_to_base64(text: str, lang: str = "en") -> str:
        """Converts text to an MP3 audio base64 data string with caching and non-blocking timeout."""
        if not text or not text.strip():
            return ""

        clean_text = text.strip()

        # Check in-memory cache
        if clean_text in _AUDIO_CACHE:
            return _AUDIO_CACHE[clean_text]

        # Use thread executor with 1.8s timeout so voice agent never blocks or hangs
        try:
            future = _executor.submit(_generate_mp3_bytes, clean_text, lang)
            encoded = future.result(timeout=1.8)
            if encoded and len(clean_text) < 150 and len(_AUDIO_CACHE) < 500:
                _AUDIO_CACHE[clean_text] = encoded
            return encoded or ""
        except Exception:
            # If Google TTS times out or fails, browser Web Speech API speaks instantly
            return ""


tts_service = TTSService()
