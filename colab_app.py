"""
VoiceFlow - Google Colab Edition
=================================
A standalone Gradio-based interface for Speech-to-Text, Text-to-Speech,
and Word Error Rate (WER) Evaluation, optimized for Google Colab and headless environments.
"""

import os
import speech_recognition as sr
from gtts import gTTS
import gradio as gr


def speech_to_text(audio_path):
    """Transcribes input speech audio into text using Google Speech Recognition."""
    if not audio_path:
        return "⚠️ Error: Please record audio or upload an audio file first."

    recognizer = sr.Recognizer()
    temp_wav = "colab_temp.wav"

    # Convert any input audio format (mic, webm, mp3) to 16kHz PCM WAV format via ffmpeg
    os.system(f"ffmpeg -y -i '{audio_path}' -ar 16000 -ac 1 '{temp_wav}' > /dev/null 2>&1")

    try:
        with sr.AudioFile(temp_wav) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "⚠️ Error: Speech was unintelligible. Please speak clearly into the microphone."
    except sr.RequestError:
        return "⚠️ Error: Speech recognition service unavailable. Please check your internet connection."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


def text_to_speech(text):
    """Synthesizes input text into high-fidelity speech audio using gTTS."""
    if not text or not text.strip():
        return None
    out_path = "synthesized_speech.mp3"
    tts = gTTS(text=text.strip(), lang="en", slow=False)
    tts.save(out_path)
    return out_path


def compute_wer(ref, hyp):
    """Computes Word Error Rate (WER) and accuracy using Levenshtein distance."""
    ref_words = ref.strip().lower().split()
    hyp_words = hyp.strip().lower().split()
    r, h = len(ref_words), len(hyp_words)

    if r == 0:
        return "⚠️ Error: Reference text cannot be empty."

    dp = [[0] * (h + 1) for _ in range(r + 1)]
    for i in range(r + 1):
        dp[i][0] = i
    for j in range(h + 1):
        dp[0][j] = j

    for i in range(1, r + 1):
        for j in range(1, h + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j - 1] + 1, dp[i][j - 1] + 1, dp[i - 1][j] + 1)

    distance = dp[r][h]
    wer = round((distance / r) * 100, 2)
    acc = round(max(0.0, 100.0 - wer), 2)

    # Backtracking to extract individual error categories
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

    return f"""
    ### 📊 Evaluation Metrics:
    - **Word Error Rate (WER):** {wer}%
    - **Recognition Accuracy:** {acc}%
    - **Substitutions (S):** {sub}
    - **Deletions (D):** {dlt}
    - **Insertions (I):** {ins}
    - **Correct Words (C):** {cor}
    - **Total Reference Words (N):** {r}
    """


# Build Gradio UI
with gr.Blocks(title="VoiceFlow - Speech Processing System") as demo:
    gr.Markdown("# 🎙️ VoiceFlow: Speech-to-Text & Text-to-Speech System")
    gr.Markdown("**BCA Final Year College Project** | Automatic Speech Recognition (ASR) & Quantitative WER Evaluation")

    with gr.Tab("🎙️ Speech-to-Text (STT)"):
        gr.Markdown("Record speech using your microphone or upload an audio file (.wav / .mp3):")
        audio_in = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Audio Input")
        btn_stt = gr.Button("Convert Speech to Text", variant="primary")
        text_out = gr.Textbox(label="Transcribed Text Output", lines=4)
        btn_stt.click(speech_to_text, inputs=audio_in, outputs=text_out)

    with gr.Tab("🔊 Text-to-Speech (TTS)"):
        gr.Markdown("Enter text to synthesize into spoken audio (supports in-browser playback and download):")
        text_in = gr.Textbox(
            label="Enter Text to Speak",
            lines=3,
            placeholder="Welcome to our college project presentation on Speech-to-Text and Text-to-Speech conversion..."
        )
        btn_tts = gr.Button("Convert to Speech", variant="primary")
        audio_out = gr.Audio(label="Synthesized Speech Audio (Click 3-dots to download)")
        btn_tts.click(text_to_speech, inputs=text_in, outputs=audio_out)

    with gr.Tab("📊 AI/ML WER Evaluator"):
        gr.Markdown("Evaluate ASR transcription accuracy against ground truth using the Levenshtein Distance algorithm:")
        ref_in = gr.Textbox(
            label="Reference Text (Ground Truth)",
            lines=2,
            value="the quick brown fox jumps over the lazy dog"
        )
        hyp_in = gr.Textbox(
            label="Recognized Text (Hypothesis)",
            lines=2,
            value="the fast brown fox jumps over a lazy dog"
        )
        btn_wer = gr.Button("Calculate WER & Accuracy", variant="primary")
        wer_out = gr.Markdown()
        btn_wer.click(compute_wer, inputs=[ref_in, hyp_in], outputs=wer_out)

if __name__ == "__main__":
    demo.launch(share=True)
