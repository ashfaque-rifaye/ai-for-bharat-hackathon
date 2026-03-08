"""Transcribe Module — Amazon Transcribe Streaming integration for STT."""

import logging
import os

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_REGION", "us-east-1")

# Language code mapping
LANGUAGE_MAP = {
    "hi-IN": "hi-IN",
    "ta-IN": "ta-IN",
    "en-IN": "en-IN",
    "auto": "en-IN",  # Default fallback for auto-detection
}

_transcribe_client = boto3.client("transcribe", region_name=REGION)


def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN", sample_rate: int = 16000) -> dict:
    """
    Transcribe audio using Amazon Transcribe (non-streaming for simplicity).

    For the hackathon MVP, we use the batch/synchronous approach.
    Streaming transcription would be used in production for real-time.

    Returns:
        {"text": "transcribed text", "language": "detected language", "confidence": 0.95}
    """
    import uuid
    import time
    import json

    s3_client = boto3.client("s3", region_name=REGION)
    audio_bucket = os.environ.get("AUDIO_BUCKET", "")

    if not audio_bucket:
        logger.warning("AUDIO_BUCKET not set, cannot transcribe")
        return {"text": "", "language": language, "confidence": 0}

    # Upload audio to S3 temporarily
    job_name = f"vaanisetu-{uuid.uuid4().hex[:8]}"
    s3_key = f"temp-audio/{job_name}.wav"

    s3_client.put_object(
        Bucket=audio_bucket,
        Key=s3_key,
        Body=audio_bytes,
        ContentType="audio/wav",
    )

    # Start transcription job
    lang_code = LANGUAGE_MAP.get(language, "hi-IN")

    try:
        _transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            LanguageCode=lang_code,
            MediaFormat="wav",
            MediaSampleRateHertz=sample_rate,
            Media={"MediaFileUri": f"s3://{audio_bucket}/{s3_key}"},
            Settings={
                "ShowSpeakerLabels": False,
            },
        )

        # Poll for completion (with timeout)
        for _ in range(30):  # Max 30 seconds
            time.sleep(1)
            status = _transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]

            if job_status == "COMPLETED":
                # Get transcript
                transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                import urllib.request
                with urllib.request.urlopen(transcript_uri) as resp:
                    transcript_data = json.loads(resp.read().decode())

                results = transcript_data.get("results", {})
                transcripts = results.get("transcripts", [])
                text = transcripts[0]["transcript"] if transcripts else ""

                # Get confidence
                items = results.get("items", [])
                confidences = [
                    float(item.get("alternatives", [{}])[0].get("confidence", 0))
                    for item in items
                    if item.get("alternatives")
                ]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                return {
                    "text": text,
                    "language": lang_code,
                    "confidence": round(avg_confidence, 2),
                }

            elif job_status == "FAILED":
                reason = status["TranscriptionJob"].get("FailureReason", "Unknown")
                logger.error(f"Transcription failed: {reason}")
                return {"text": "", "language": lang_code, "confidence": 0}

        logger.error("Transcription timed out")
        return {"text": "", "language": lang_code, "confidence": 0}

    finally:
        # Cleanup
        try:
            _transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception:
            pass
        try:
            s3_client.delete_object(Bucket=audio_bucket, Key=s3_key)
        except Exception:
            pass
