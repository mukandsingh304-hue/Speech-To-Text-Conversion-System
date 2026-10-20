"""
Unit and Integration Tests for Speech-to-Text and Text-to-Speech System
========================================================================
Covers:
- Flask routes and server availability
- Health check endpoint
- System voices endpoint
- Text-to-Speech validation (empty text, long text, rate limits)
- Speech-to-Text input validation (missing file, invalid format, empty file)
- Word Error Rate (WER) algorithmic calculations (Levenshtein Distance)
- Audio generation with pyttsx3
- End-to-end STT audio file transcription
"""

import io
import os
import json
import pytest
import pyttsx3
from app import app, compute_wer, HAS_PYTHONCOM

if HAS_PYTHONCOM:
    import pythoncom


@pytest.fixture
def client():
    """Create a Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ============================================================================
# 1. Server & Health Check Tests
# ============================================================================

def test_home_page_renders(client):
    """Test that the home page (GET /) returns status 200 and loads HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"VoiceFlow System" in response.data or b"Speech-to-Text" in response.data


def test_health_endpoint(client):
    """Test that GET /health returns 200 and operational health metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "healthy"
    assert "stt" in data
    assert "tts" in data
    assert "evaluation" in data


def test_voices_endpoint(client):
    """Test that GET /api/voices returns a valid JSON response."""
    response = client.get("/api/voices")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert isinstance(data["voices"], list)


# ============================================================================
# 2. Text-to-Speech Validation & Synthesis Tests
# ============================================================================

def test_tts_empty_text_validation(client):
    """Test that POST /api/text-to-speech with empty text returns 400."""
    response = client.post(
        "/api/text-to-speech",
        json={"text": "   "},
        content_type="application/json"
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "empty" in data["error"].lower()


def test_tts_excessive_length_validation(client):
    """Test that text exceeding 5,000 characters is rejected with 400."""
    excessive_text = "word " * 1500  # > 5000 chars
    response = client.post(
        "/api/text-to-speech",
        json={"text": excessive_text},
        content_type="application/json"
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "too long" in data["error"].lower()


def test_tts_valid_synthesis(client):
    """Test that POST /api/text-to-speech generates a valid base64 WAV payload."""
    response = client.post(
        "/api/text-to-speech",
        json={
            "text": "Hello world test",
            "rate": 150,
            "volume": 0.8
        },
        content_type="application/json"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "audio_url" in data
    assert data["audio_url"].startswith("data:audio/wav;base64,")
    assert data["word_count"] == 3
    assert data["file_size"] > 0


# ============================================================================
# 3. Speech-to-Text Input Validation & Transcription Tests
# ============================================================================

def test_stt_no_file_uploaded(client):
    """Test that POST /api/speech-to-text without an audio file returns 400."""
    response = client.post("/api/speech-to-text", data={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "no audio file" in data["error"].lower()


def test_stt_invalid_file_extension(client):
    """Test that uploading a non-audio file (.txt) returns 400."""
    data = {
        "file": (io.BytesIO(b"fake text content"), "test_file.txt")
    }
    response = client.post(
        "/api/speech-to-text",
        data=data,
        content_type="multipart/form-data"
    )
    assert response.status_code == 400
    res_data = json.loads(response.data)
    assert res_data["success"] is False
    assert "unsupported" in res_data["error"].lower()


def test_stt_empty_audio_file(client):
    """Test that uploading a 0-byte WAV file returns 400."""
    data = {
        "file": (io.BytesIO(b""), "empty.wav")
    }
    response = client.post(
        "/api/speech-to-text",
        data=data,
        content_type="multipart/form-data"
    )
    assert response.status_code == 400
    res_data = json.loads(response.data)
    assert res_data["success"] is False
    assert "empty" in res_data["error"].lower()


def test_stt_end_to_end_transcription(client):
    """
    End-to-end integration test:
    Generates a real WAV file with pyttsx3, sends to /api/speech-to-text,
    and validates successful recognition.
    """
    temp_wav = "test_speech_sample.wav"
    try:
        if HAS_PYTHONCOM:
            pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.save_to_file("speech recognition works wonderfully", temp_wav)
        engine.runAndWait()
        engine.stop()

        with open(temp_wav, "rb") as f:
            wav_bytes = f.read()

        data = {
            "file": (io.BytesIO(wav_bytes), "sample.wav")
        }
        response = client.post(
            "/api/speech-to-text",
            data=data,
            content_type="multipart/form-data"
        )
        assert response.status_code == 200
        res_data = json.loads(response.data)
        assert res_data["success"] is True
        assert "speech recognition works wonderfully" in res_data["text"].lower()
    finally:
        if HAS_PYTHONCOM:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except OSError:
                pass


# ============================================================================
# 4. Word Error Rate (WER) Evaluation Tests
# ============================================================================

def test_wer_identical_strings():
    """Test that identical reference and hypothesis give 0% WER and 100% accuracy."""
    res = compute_wer("the quick brown fox", "the quick brown fox")
    assert res["wer"] == 0.0
    assert res["accuracy"] == 100.0
    assert res["substitutions"] == 0
    assert res["deletions"] == 0
    assert res["insertions"] == 0
    assert res["correct"] == 4
    assert res["reference_words"] == 4


def test_wer_with_errors():
    """
    Test WER with substitutions and insertions.
    Ref:  'the quick brown fox' (4 words)
    Hyp:  'the fast brown fox today' (quick->fast: 1 sub, 'today': 1 ins)
    Errors = 2, N = 4 -> WER = 50.0%, Accuracy = 50.0%
    """
    res = compute_wer("the quick brown fox", "the fast brown fox today")
    assert res["wer"] == 50.0
    assert res["accuracy"] == 50.0
    assert res["substitutions"] == 1
    assert res["insertions"] == 1
    assert res["deletions"] == 0
    assert res["correct"] == 3


def test_wer_endpoint_empty_inputs(client):
    """Test that POST /api/evaluate-wer with empty inputs returns 400."""
    response = client.post(
        "/api/evaluate-wer",
        json={"reference": "  ", "hypothesis": "  "},
        content_type="application/json"
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False


def test_wer_endpoint_valid_calculation(client):
    """Test that POST /api/evaluate-wer computes and returns complete statistics."""
    response = client.post(
        "/api/evaluate-wer",
        json={
            "reference": "speech recognition is amazing",
            "hypothesis": "speech cognition is amazing"
        },
        content_type="application/json"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    res = data["results"]
    assert res["reference_words"] == 4
    assert res["substitutions"] == 1
    assert res["wer"] == 25.0
    assert res["accuracy"] == 75.0
