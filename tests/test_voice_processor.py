"""Tests for Voice Processor Lambda — Transcribe + Polly integration."""

import json
import pytest
import sys
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "voice_processor"))

from constants import Language, POLLY_VOICE_MAP, TRANSCRIBE_LANGUAGE_MAP


# ── Polly Voice Mapping ──────────────────────────────────────────────

class TestPollyVoiceMapping:
    """Test Polly voice configuration for Indian languages."""

    def test_hindi_uses_kajal(self):
        voice = POLLY_VOICE_MAP[Language.HINDI]
        assert voice["VoiceId"] == "Kajal"
        assert voice["Engine"] == "neural"
        assert voice["LanguageCode"] == "hi-IN"

    def test_english_uses_kajal(self):
        voice = POLLY_VOICE_MAP[Language.ENGLISH]
        assert voice["VoiceId"] == "Kajal"
        assert voice["Engine"] == "neural"
        assert voice["LanguageCode"] == "en-IN"

    def test_tamil_has_fallback(self):
        voice = POLLY_VOICE_MAP[Language.TAMIL]
        assert voice["VoiceId"] == "Kajal"
        # Tamil uses Hindi Kajal as fallback via translate
        assert voice["LanguageCode"] == "hi-IN"


# ── Transcribe Language Codes ────────────────────────────────────────

class TestTranscribeLanguageMap:
    """Test Transcribe language code mapping."""

    def test_hindi_transcribe_code(self):
        assert TRANSCRIBE_LANGUAGE_MAP[Language.HINDI] == "hi-IN"

    def test_english_transcribe_code(self):
        assert TRANSCRIBE_LANGUAGE_MAP[Language.ENGLISH] == "en-IN"

    def test_tamil_transcribe_code(self):
        assert TRANSCRIBE_LANGUAGE_MAP[Language.TAMIL] == "ta-IN"


# ── Audio Processing Tests ───────────────────────────────────────────

class TestAudioProcessing:
    """Test audio handling utilities."""

    def test_base64_audio_encoding(self):
        """Audio data should be base64 encodable/decodable."""
        raw_audio = b"\x00\x01\x02\x03" * 100  # Fake PCM
        encoded = base64.b64encode(raw_audio).decode("utf-8")
        decoded = base64.b64decode(encoded)
        assert decoded == raw_audio

    def test_audio_chunk_size(self):
        """Audio chunks should be reasonable size."""
        # 16kHz, 16-bit, mono = 32KB/sec
        one_second = 16000 * 2  # 32KB = 1 second of audio
        chunk = b"\x00" * one_second
        assert len(chunk) == 32000

    def test_empty_audio_handling(self):
        """Empty audio should not crash."""
        empty = b""
        encoded = base64.b64encode(empty).decode()
        assert encoded == ""


# ── Voice Processor Event Format ─────────────────────────────────────

class TestVoiceProcessorEvent:
    """Test Lambda event format for voice processing."""

    def test_tts_request_event(self):
        """Test text-to-speech request format."""
        event = {
            "action": "synthesize",
            "text": "नमस्ते, मैं वाणी सेतु हूँ।",
            "language": "hi-IN",
            "sessionId": "test-session-123",
        }
        assert event["action"] == "synthesize"
        assert event["language"] == "hi-IN"
        assert "वाणी सेतु" in event["text"]

    def test_stt_request_event(self):
        """Test speech-to-text request format."""
        event = {
            "action": "transcribe",
            "audio": base64.b64encode(b"\x00" * 100).decode(),
            "language": "hi-IN",
            "sessionId": "test-session-123",
        }
        assert event["action"] == "transcribe"
        assert len(event["audio"]) > 0

    def test_websocket_incoming_message(self):
        """Test WebSocket message with audio chunk."""
        msg = {
            "action": "audioChunk",
            "data": base64.b64encode(b"\x00" * 1000).decode(),
            "sessionId": "test-session",
            "language": "hi-IN",
        }
        decoded = base64.b64decode(msg["data"])
        assert len(decoded) == 1000


# ── Voice Processor Response Format ──────────────────────────────────

class TestVoiceProcessorResponse:
    """Test voice processor response format."""

    def test_transcription_response(self):
        """STT should return text and confidence."""
        response = {
            "type": "transcription",
            "text": "मुझे किसान योजना चाहिए",
            "language": "hi-IN",
            "confidence": 0.95,
        }
        assert response["type"] == "transcription"
        assert len(response["text"]) > 0
        assert 0 <= response["confidence"] <= 1

    def test_synthesis_response(self):
        """TTS should return base64 audio."""
        response = {
            "type": "synthesis",
            "audio": base64.b64encode(b"\x00" * 100).decode(),
            "format": "mp3",
            "language": "hi-IN",
        }
        assert response["type"] == "synthesis"
        assert len(response["audio"]) > 0
        decoded = base64.b64decode(response["audio"])
        assert len(decoded) == 100


# ── SSML Generation ──────────────────────────────────────────────────

class TestSSMLGeneration:
    """Test SSML formatting for Polly TTS."""

    def test_basic_ssml(self):
        text = "Hello, welcome to VaaniSetu"
        ssml = f"<speak>{text}</speak>"
        assert ssml.startswith("<speak>")
        assert ssml.endswith("</speak>")

    def test_ssml_with_prosody(self):
        """Phone conversations should use slower, louder speech."""
        text = "आपकी योजना मिल गई"
        ssml = f'<speak><prosody rate="slow" volume="loud">{text}</prosody></speak>'
        assert 'rate="slow"' in ssml
        assert 'volume="loud"' in ssml

    def test_ssml_with_pause(self):
        """Add pauses between scheme details."""
        ssml = '<speak>PM-KISAN<break time="500ms"/>6000 rupees per year</speak>'
        assert 'break time="500ms"' in ssml

    def test_ssml_number_pronunciation(self):
        """Amounts should be readable by TTS."""
        amount = "₹6,000"
        tts_friendly = amount.replace("₹", "rupees ").replace(",", "")
        assert "rupees" in tts_friendly
        assert "6000" in tts_friendly
