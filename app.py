"""
Speech-to-Text and Text-to-Speech Conversion System
====================================================
A BCA Final Year / Semester College Project.

Features:
1. Speech-to-Text (STT):
   - Upload audio files (.wav format).
   - Record live audio using browser microphone (encoded to WAV).
   - Pretrained speech recognition engine (Google Web Speech API via SpeechRecognition).
2. Text-to-Speech (TTS):
   - Offline text-to-speech synthesis using pyttsx3 (Windows SAPI5 engine).
   - Voice and speech rate adjustments.
   - Browser Web Speech Synthesis fallback.
3. AI/ML Evaluation (Word Error Rate - WER):
   - Evaluates speech recognition accuracy against a reference text using Levenshtein distance.
   - No external dataset or model training required.
"""

import os
import io
import wave
import base64
import logging
import tempfile
from typing import Dict, Any, List

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS

import speech_recognition as sr
import pyttsx3

# COM threading support for Windows pyttsx3
try:
    import pythoncom
    HAS_PYTHONCOM = True
except ImportError:
    HAS_PYTHONCOM = False

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("SpeechConverter")

app = Flask(__name__)
CORS(app)

# Configuration limits
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # Max 16MB file upload
ALLOWED_EXTENSIONS = {"wav", "wave", "flac", "aiff", "aif"}


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has a supported audio extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_system_voices() -> List[Dict[str, Any]]:
    """Retrieve available speech synthesis voices installed on the host system."""
    voices_list = []
    if HAS_PYTHONCOM:
        pythoncom.CoInitialize()
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        if voices:
            for v in voices:
                voices_list.append({
                    "id": getattr(v, "id", ""),
                    "name": getattr(v, "name", "System Voice"),
                    "languages": getattr(v, "languages", []),
                    "gender": getattr(v, "gender", "unknown")
                })
        engine.stop()
    except Exception as exc:
        logger.warning("Could not enumerate system voices: %s", exc)
    finally:
        if HAS_PYTHONCOM:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
    return voices_list


def compute_wer(reference: str, hypothesis: str) -> Dict[str, Any]:
    """
    Compute Word Error Rate (WER) using Dynamic Programming (Levenshtein Distance at word level).

    Formula:
        WER = (Substitutions + Deletions + Insertions) / Total Reference Words
        Accuracy = max(0.0, 1.0 - WER) * 100%

    This evaluates the accuracy of the recognized speech against a ground truth transcript.
    """
    ref_words = reference.strip().lower().split()
    hyp_words = hypothesis.strip().lower().split()

    r = len(ref_words)
    h = len(hyp_words)

    if r == 0:
        if h == 0:
            return {
                "wer": 0.0,
                "accuracy": 100.0,
                "substitutions": 0,
                "deletions": 0,
                "insertions": 0,
                "correct": 0,
                "reference_words": 0,
                "hypothesis_words": 0,
                "message": "Both reference and recognized text are empty."
            }
        return {
            "wer": 100.0,
            "accuracy": 0.0,
            "substitutions": 0,
            "deletions": 0,
            "insertions": h,
            "correct": 0,
            "reference_words": 0,
            "hypothesis_words": h,
            "message": "Reference text is empty but hypothesis has words."
        }

    # Initialize dynamic programming table
    dp = [[0] * (h + 1) for _ in range(r + 1)]
    for i in range(r + 1):
        dp[i][0] = i
    for j in range(h + 1):
        dp[0][j] = j

    # Compute edit distance
    for i in range(1, r + 1):
        for j in range(1, h + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                substitution = dp[i - 1][j - 1] + 1
                insertion = dp[i][j - 1] + 1
                deletion = dp[i - 1][j + 1 - 1] + 1  # dp[i - 1][j] + 1
                dp[i][j] = min(substitution, insertion, deletion)

    distance = dp[r][h]
    wer = distance / r

    # Backtracking to count individual operations (Substitutions, Deletions, Insertions, Correct)
    i, j = r, h
    sub, ins, dlt, cor = 0, 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_words[i - 1] == hyp_words[j - 1]:
            cor += 1
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            sub += 1
            i -= 1
            j -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            ins += 1
            j -= 1
        else:
            dlt += 1
            i -= 1

    accuracy = max(0.0, (1.0 - wer)) * 100.0

    return {
        "wer": round(wer * 100.0, 2),
        "accuracy": round(accuracy, 2),
        "substitutions": sub,
        "deletions": dlt,
        "insertions": ins,
        "correct": cor,
        "reference_words": r,
        "hypothesis_words": h,
        "formula": "WER = (Substitutions + Deletions + Insertions) / Total Words in Reference"
    }


# ==========================================
# Routes
# ==========================================

@app.route("/")
def index():
    """Serve the single-page application frontend."""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    """Return health status and configuration details for the system."""
    return jsonify({
        "status": "healthy",
        "service": "Speech-to-Text and Text-to-Speech Conversion System",
        "version": "1.0.0",
        "platform": os.name,
        "stt": {
            "engine": "Google Web Speech API (Pretrained Cloud ASR via SpeechRecognition)",
            "mode": "Online inference",
            "supported_formats": list(ALLOWED_EXTENSIONS)
        },
        "tts": {
            "engine": "pyttsx3 (SAPI5 on Windows)",
            "mode": "Offline local synthesis",
            "fallback": "HTML5 Web SpeechSynthesis (Client-side)"
        },
        "evaluation": {
            "metric": "Word Error Rate (WER) & Levenshtein Distance",
            "mode": "Offline algorithmic calculation without external datasets"
        }
    }), 200


@app.route("/api/voices", methods=["GET"])
def get_voices():
    """API endpoint to list available system TTS voices."""
    voices = get_system_voices()
    return jsonify({
        "success": True,
        "voices": voices,
        "count": len(voices)
    }), 200


@app.route("/api/speech-to-text", methods=["POST"])
def speech_to_text():
    """
    API endpoint: Convert uploaded or recorded audio into text.
    Accepts multipart/form-data with 'audio' or 'file'.
    Uses speech_recognition with Google Web Speech API.
    """
    file_obj = None
    if "file" in request.files:
        file_obj = request.files["file"]
    elif "audio" in request.files:
        file_obj = request.files["audio"]

    if not file_obj or file_obj.filename == "":
        return jsonify({
            "success": False,
            "error": "No audio file was uploaded. Please upload a WAV audio file or record speech."
        }), 400

    filename = file_obj.filename
    if not allowed_file(filename):
        return jsonify({
            "success": False,
            "error": f"Unsupported audio file format '{filename}'. Please provide a .wav file."
        }), 400

    temp_path = None
    try:
        # Create temporary file to safely store and process audio
        suffix = "." + filename.rsplit(".", 1)[1].lower() if "." in filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            file_obj.save(temp_path)

        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            return jsonify({
                "success": False,
                "error": "The uploaded audio file is empty (0 bytes). Please record or select a valid audio file."
            }), 400

        # Calculate approximate duration if standard WAV
        audio_duration = 0.0
        try:
            with wave.open(temp_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    audio_duration = round(frames / float(rate), 2)
        except Exception:
            # Non-critical if duration calculation fails on special WAV variants
            pass

        # Perform Speech-to-Text using SpeechRecognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_path) as source:
            # Adjust for ambient noise and record
            audio_data = recognizer.record(source)

        # Call pretrained Google Web Speech API engine
        recognized_text = recognizer.recognize_google(audio_data)

        logger.info("Successfully transcribed audio (%s s): '%s'", audio_duration, recognized_text)

        return jsonify({
            "success": True,
            "text": recognized_text,
            "audio_duration": audio_duration,
            "engine": "Google Web Speech API",
            "mode": "Pretrained Model Inference (Online)"
        }), 200

    except sr.UnknownValueError:
        return jsonify({
            "success": False,
            "error": "Speech was unintelligible or no words could be recognized. Please speak more clearly or check audio clarity."
        }), 422

    except sr.RequestError as exc:
        logger.error("Speech recognition service request error: %s", exc)
        return jsonify({
            "success": False,
            "error": "Could not connect to the speech recognition service. Please check your internet connection."
        }), 503

    except ValueError as exc:
        logger.error("Audio decoding value error: %s", exc)
        return jsonify({
            "success": False,
            "error": f"Audio file format error: {str(exc)}. Ensure the file is uncompressed 16-bit PCM WAV."
        }), 400

    except Exception as exc:
        logger.error("Unexpected error in speech_to_text: %s", exc)
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred during transcription: {str(exc)}"
        }), 500

    finally:
        # Guarantee cleanup of temporary audio file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as cleanup_err:
                logger.warning("Could not remove temp file %s: %s", temp_path, cleanup_err)


@app.route("/api/text-to-speech", methods=["POST"])
def text_to_speech():
    """
    API endpoint: Convert input text into speech audio.
    Accepts JSON:
      {
        "text": "Hello world",
        "voice_id": "optional_voice_id",
        "rate": 150,     (words per minute, range 50 - 350)
        "volume": 1.0    (0.0 to 1.0)
      }
    Returns base64 encoded WAV audio in JSON.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({
            "success": False,
            "error": "Text cannot be empty. Please enter text to convert to speech."
        }), 400

    if len(text) > 5000:
        return jsonify({
            "success": False,
            "error": f"Text is too long ({len(text)} characters). Maximum limit is 5000 characters."
        }), 400

    # Validate rate & volume
    rate = data.get("rate", 150)
    try:
        rate = int(rate)
        if rate < 50 or rate > 350:
            rate = 150
    except (ValueError, TypeError):
        rate = 150

    volume = data.get("volume", 1.0)
    try:
        volume = float(volume)
        volume = max(0.0, min(1.0, volume))
    except (ValueError, TypeError):
        volume = 1.0

    voice_id = data.get("voice_id", None)

    temp_wav_path = None
    if HAS_PYTHONCOM:
        pythoncom.CoInitialize()

    try:
        # Step 1: Attempt offline pyttsx3 synthesis
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_wav_path = temp_file.name

            # On Windows, explicitly request sapi5 driver
            if os.name == "nt":
                engine = pyttsx3.init("sapi5")
            else:
                engine = pyttsx3.init()

            engine.setProperty("rate", rate)
            engine.setProperty("volume", volume)

            if voice_id:
                try:
                    engine.setProperty("voice", voice_id)
                except Exception as vexc:
                    logger.warning("Could not set voice %s: %s", voice_id, vexc)

            engine.save_to_file(text, temp_wav_path)
            engine.runAndWait()
            engine.stop()

            if not os.path.exists(temp_wav_path) or os.path.getsize(temp_wav_path) == 0:
                raise RuntimeError("pyttsx3 generated empty audio file")

            with open(temp_wav_path, "rb") as f:
                audio_bytes = f.read()

            base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            data_url = f"data:audio/wav;base64,{base64_audio}"
            engine_name = "pyttsx3 (Offline Windows SAPI5)" if os.name == "nt" else "pyttsx3 (Linux eSpeak)"

        except Exception as pyttsx3_err:
            logger.warning("pyttsx3 failed (%s). Falling back to gTTS...", pyttsx3_err)
            # Step 2: Automatic fallback to gTTS (Google Text-to-Speech)
            from gtts import gTTS
            tts = gTTS(text=text, lang="en")
            bio = io.BytesIO()
            tts.write_to_fp(bio)
            audio_bytes = bio.getvalue()
            base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            data_url = f"data:audio/mp3;base64,{base64_audio}"
            engine_name = "gTTS (Google Speech Engine Fallback)"

        word_count = len(text.split())
        logger.info("Successfully synthesized text (%d words, %d bytes) via %s", word_count, len(audio_bytes), engine_name)

        return jsonify({
            "success": True,
            "audio_url": data_url,
            "file_size": len(audio_bytes),
            "word_count": word_count,
            "char_count": len(text),
            "engine": engine_name,
            "rate": rate,
            "volume": volume
        }), 200

    except Exception as exc:
        logger.error("Text-to-speech synthesis error: %s", exc)
        return jsonify({
            "success": False,
            "error": f"Text-to-speech error: {str(exc)}. You can use the browser fallback synthesis toggle."
        }), 500

    finally:
        if HAS_PYTHONCOM:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except OSError as cleanup_err:
                logger.warning("Could not remove temp wav %s: %s", temp_wav_path, cleanup_err)


@app.route("/api/evaluate-wer", methods=["POST"])
def evaluate_wer():
    """
    API endpoint: Calculate Word Error Rate (WER) and recognition accuracy.
    Accepts JSON:
      {
        "reference": "Expected original speech transcript (Ground Truth)",
        "hypothesis": "Transcribed speech output from STT model"
      }
    Returns detailed metrics (WER %, Accuracy %, Substitutions, Deletions, Insertions).
    """
    data = request.get_json(silent=True) or {}
    reference = data.get("reference", "")
    hypothesis = data.get("hypothesis", "")

    if not reference.strip() and not hypothesis.strip():
        return jsonify({
            "success": False,
            "error": "Please enter both reference text and recognized text to evaluate."
        }), 400

    results = compute_wer(reference, hypothesis)
    return jsonify({
        "success": True,
        "results": results
    }), 200


# Application entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting Speech-to-Text and Text-to-Speech System on http://127.0.0.1:%s", port)
    app.run(host="127.0.0.1", port=port, debug=True)
