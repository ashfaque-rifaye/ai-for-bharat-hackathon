"""Polly Module — Amazon Polly Neural TTS integration with SSML support.

Why SSML?
  SSML (Speech Synthesis Markup Language) lets us control *how* Polly speaks —
  adding natural pauses between sentences, adjusting speed for Hindi government
  terminology, and emphasising scheme names so users catch them clearly.
"""

import base64
import logging
import os
import re

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_REGION", "us-east-1")

# Voice mappings for supported languages
VOICE_MAP = {
    "hi-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "en-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "en-IN"},
    "ta-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback
    "bn-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "te-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "mr-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "kn-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "ml-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
}

# Known government scheme names — emphasised in SSML so users hear them clearly
_SCHEME_KEYWORDS = [
    "PM-KISAN", "PM-AWAS", "AYUSHMAN", "UJJWALA", "MUDRA",
    "PM-GARIB-KALYAN", "FASAL BIMA", "SUKANYA SAMRIDDHI",
    "SOIL HEALTH CARD", "RKVY", "पीएम किसान", "आयुष्मान",
    "उज्ज्वला", "मुद्रा", "प्रधानमंत्री",
]

_polly_client = boto3.client("polly", region_name=REGION)


# ── SSML Helpers ─────────────────────────────────────────────────────

def _escape_ssml(text: str) -> str:
    """Escape XML-special characters so they don't break the SSML tag tree."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def _wrap_ssml(text: str, language: str = "hi-IN") -> str:
    """Convert plain text → SSML with natural prosody, pauses, and emphasis.

    What this does (plain-English):
      1. Escapes any XML-special characters in the text.
      2. Adds 300 ms pauses after every sentence-ending punctuation (।, ., !, ?)
         so the speech sounds natural and not rushed.
      3. Wraps recognised government-scheme keywords in <emphasis> tags so the
         listener hears them clearly.
      4. Sets an overall speaking rate of 95 % for Hindi-like languages (people
         need a bit more time to parse government terminology) and 100 % for English.
    """
    escaped = _escape_ssml(text)

    # Insert 300 ms break after Hindi purna viram (।) and standard punctuation
    escaped = re.sub(
        r"([।.!?])\s*",
        r'\1<break time="300ms"/> ',
        escaped,
    )

    # Neural voices don't support <emphasis>, so we add a tiny pause before
    # scheme keywords for a natural emphasis effect.
    for keyword in _SCHEME_KEYWORDS:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        escaped = pattern.sub(
            f'<break time="100ms"/>{_escape_ssml(keyword)}',
            escaped,
        )

    # Choose speaking rate — a touch slower for Indic languages
    rate = "95%" if language != "en-IN" else "100%"

    return (
        f'<speak><prosody rate="{rate}">'
        f"{escaped}"
        f"</prosody></speak>"
    )


# ── Main TTS Function ───────────────────────────────────────────────

def synthesize_speech(
    text: str,
    language: str = "hi-IN",
    output_format: str = "mp3",
    use_ssml: bool = True,
) -> dict:
    """Convert text → speech using Amazon Polly Neural voices.

    Args:
        text:          The text to speak.
        language:      BCP-47 language tag (e.g. "hi-IN").
        output_format: "mp3" | "ogg_vorbis" | "pcm".
        use_ssml:      When True, wraps the text in SSML for better prosody.

    Returns:
        {"audio": "<base64>", "contentType": "audio/mpeg", "language": "hi-IN"}
    """
    if not text or not text.strip():
        return {"audio": "", "contentType": "", "language": language}

    voice_config = VOICE_MAP.get(language, VOICE_MAP["hi-IN"])

    # For languages without a native Polly voice, translate to Hindi first
    actual_text = text
    needs_translation = language not in ("hi-IN", "en-IN")
    if needs_translation:
        source_lang = language.split("-")[0]
        actual_text = _translate_for_tts(text, source_lang, "hi")
        voice_config = VOICE_MAP["hi-IN"]

    # Build SSML if requested
    text_type = "text"
    polly_text = actual_text
    if use_ssml:
        polly_text = _wrap_ssml(actual_text, language)
        text_type = "ssml"

    try:
        response = _polly_client.synthesize_speech(
            Text=polly_text,
            TextType=text_type,
            OutputFormat=output_format,
            VoiceId=voice_config["VoiceId"],
            Engine=voice_config["Engine"],
            LanguageCode=voice_config["LanguageCode"],
        )

        audio_stream = response["AudioStream"].read()
        audio_b64 = base64.b64encode(audio_stream).decode("utf-8")

        content_type = {
            "mp3": "audio/mpeg",
            "ogg_vorbis": "audio/ogg",
            "pcm": "audio/pcm",
        }.get(output_format, "audio/mpeg")

        return {
            "audio": audio_b64,
            "contentType": content_type,
            "language": language,
        }

    except Exception as e:
        logger.exception(f"Polly synthesis error: {e}")
        return {"audio": "", "contentType": "", "language": language, "error": str(e)}


def _translate_for_tts(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text for TTS when direct voice isn't available."""
    try:
        translate_client = boto3.client("translate", region_name=REGION)
        response = translate_client.translate_text(
            Text=text,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang,
        )
        return response["TranslatedText"]
    except Exception as e:
        logger.warning(f"Translation failed, using original text: {e}")
        return text


def detect_language(text: str) -> str:
    """Detect language of text using Amazon Translate/Comprehend."""
    try:
        translate_client = boto3.client("translate", region_name=REGION)
        # Use translate to detect the source language
        response = translate_client.translate_text(
            Text=text[:100],  # Use first 100 chars for detection
            SourceLanguageCode="auto",
            TargetLanguageCode="en",
        )
        detected = response.get("SourceLanguageCode", "hi")

        # Map to our language codes
        lang_map = {"hi": "hi-IN", "ta": "ta-IN", "en": "en-IN"}
        return lang_map.get(detected, "hi-IN")

    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return "hi-IN"  # Default to Hindi
