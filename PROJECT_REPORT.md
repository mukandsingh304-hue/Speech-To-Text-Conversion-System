# PROJECT REPORT
## SPEECH-TO-TEXT AND TEXT-TO-SPEECH CONVERSION SYSTEM
**Course:** Bachelor of Computer Applications (BCA)  
**Academic Year:** Final Year Project Submission  
**Domain:** Artificial Intelligence & Natural Language Processing / Human-Computer Interaction  

---

### TABLE OF CONTENTS
1. Abstract
2. Introduction
3. Problem Statement
4. Objectives
5. Literature Review: Existing System vs. Proposed System
6. System Requirements Specification (SRS)
   - 6.1 Hardware Requirements
   - 6.2 Software Requirements
7. System Architecture & Design
8. Module Descriptions
   - 8.1 Speech-to-Text (STT) Module
   - 8.2 Text-to-Speech (TTS) Module
   - 8.3 Word Error Rate (WER) Evaluation Module
   - 8.4 REST API & Web Interface Module
9. Algorithms & Workflows
   - 9.1 Audio Capture & PCM WAV Serialization
   - 9.2 Acoustic Inference & Language Decoding Workflow
   - 9.3 SAPI5 Speech Synthesis Workflow
   - 9.4 Levenshtein Dynamic Programming Algorithm for WER
10. Testing & Verification
    - 10.1 Unit Testing
    - 10.2 Integration Testing
    - 10.3 Test Results Summary
11. Advantages & Limitations
12. Future Scope
13. Conclusion
14. References

---

## 1. ABSTRACT

Communication between humans and computer systems has traditionally relied on manual alphanumeric inputs (keyboards, touchscreens) and visual display devices (monitors). However, voice is the most natural, rapid, and expressive mode of human communication. 

This project presents the **Speech-to-Text and Text-to-Speech Conversion System**, a dual-directional voice processing application engineered using Python, Flask, `pyttsx3`, `SpeechRecognition`, and modern web technologies. The system accepts spoken audio either via local uncompressed WAV file uploads or live in-browser microphone capture, transcribing it into editable digital text. Conversely, the system converts written text into high-fidelity human speech with customizable speaking rates and voice profiles operating completely offline via the Windows SAPI5 subsystem. 

Furthermore, unlike typical applications that merely perform inference without academic validation, this project integrates an AI/ML Evaluation Module that computes the **Word Error Rate (WER)** using the **Levenshtein Dynamic Programming Algorithm**. This allows students, researchers, and examiners to quantitatively measure speech recognition accuracy against a ground truth transcript without downloading multi-gigabyte training datasets. The project adheres to software engineering best practices with modular architecture, automated test suites, input validation, and thread-safe COM synchronization on Windows.

---

## 2. INTRODUCTION

Speech processing is an interdisciplinary subfield of Artificial Intelligence (AI), Digital Signal Processing (DSP), and Natural Language Processing (NLP). It encompasses two primary complimentary domains:

1. **Automatic Speech Recognition (ASR) / Speech-to-Text (STT):** The algorithmic process of translating acoustic audio signals captured through a transducer (microphone) into machine-readable digital text strings.
2. **Text-to-Speech Synthesis (TTS):** The computational synthesis of intelligible, natural-sounding artificial human speech waveforms from raw orthographic or phonetic text tokens.

In modern computing, these technologies power virtual assistants (Siri, Alexa, Google Assistant), automated accessibility software for visually and motor-impaired individuals, hands-free automotive telematics, and automated lecture/meeting transcription systems.

This project implements a unified web-based software suite that provides both services through an intuitive, beginner-friendly interface. It was specifically architected to run seamlessly on standard Windows personal computers without relying on expensive cloud subscriptions, proprietary API keys, or demanding GPU hardware clusters.

---

## 3. PROBLEM STATEMENT

Despite rapid advancements in computational voice technologies, accessibility and educational clarity remain persistent hurdles:
- **Typing Fatigue and Inaccessibility:** Physically impaired individuals, elderly users, and individuals with dyslexia face considerable barriers when interacting with standard text interfaces.
- **Visual Strain:** Prolonged reading of extensive textual content causes digital eye strain and lowers productivity in environments where visual attention must be maintained elsewhere (e.g., machinery operation or driving).
- **High Resource Overhead in AI Education:** Many modern deep-learning speech recognition tutorials require downloading 50GB–100GB datasets from platforms like Kaggle, requiring specialized CUDA-enabled Nvidia GPUs and days of training time. This presents a steep barrier for BCA college students and normal laptop configurations.
- **Lack of Unified Tools:** Existing open-source tools typically isolate STT or TTS into disjoint command-line utilities without an interactive user interface or objective quantitative evaluation metrics.

---

## 4. OBJECTIVES

The core objectives of this project are:
1. To design and implement a web-based, user-friendly **Speech-to-Text (STT)** module capable of transcribing WAV audio files and live microphone recordings.
2. To develop a **100% Offline Text-to-Speech (TTS)** engine on Windows leveraging `pyttsx3` and Windows SAPI5 with adjustable speed and voice settings.
3. To build a client-side **Web SpeechSynthesis Fallback** ensuring cross-platform resilience.
4. To implement an **AI/ML Evaluation Module** based on the Levenshtein Distance algorithm to calculate Word Error Rate (WER), Substitutions, Deletions, and Insertions without external datasets.
5. To develop a responsive, modern blue-and-white web interface with cross-module data routing (e.g., sending STT transcriptions directly to TTS playback or WER evaluation).
6. To validate the system through automated unit and integration tests using `pytest`.

---

## 5. LITERATURE REVIEW: EXISTING SYSTEM VS. PROPOSED SYSTEM

| Parameter | Existing Traditional Systems | Proposed VoiceFlow System |
|---|---|---|
| **User Interface** | Command-line scripts or clunky legacy desktop GUIs. | Responsive, modern Single-Page Application (SPA) using Bootstrap 5. |
| **Dataset Requirement** | Often requires 20GB+ Kaggle datasets (e.g., LibriSpeech, CommonVoice). | **Zero external datasets required.** Uses pretrained ASR inference and algorithmic WER evaluation. |
| **Speech-to-Text Input** | Restricted to pre-existing audio files on disk. | Dual input: Direct drag-and-drop file upload AND live browser microphone recording. |
| **Audio Format Handling** | Frequently crashes on format mismatch without FFmpeg. | Pure in-browser 16-bit PCM WAV encoding with 44-byte RIFF header generation. |
| **TTS Connectivity** | Dependent on paid, cloud-based REST APIs (Google Cloud TTS, AWS Polly). | **100% Offline synthesis** via Windows SAPI5 plus client-side Web Speech fallback. |
| **Evaluation Metric** | No built-in verification of recognition quality. | Interactive Word Error Rate (WER) calculator with step-by-step mathematical breakdown. |
| **Deployment Simplicity** | Requires complex Docker containers and C++ build chains. | Simple pip installation on standard Windows laptop running Python 3.10–3.13. |

---

## 6. SYSTEM REQUIREMENTS SPECIFICATION (SRS)

### 6.1 Hardware Requirements
- **CPU:** Intel Core i3 / AMD Ryzen 3 or higher.
- **RAM:** Minimum 4 GB (8 GB recommended for smooth multitasking).
- **Hard Disk:** Minimum 500 MB free space.
- **Audio Devices:** Standard integrated laptop microphone or external USB headset, and stereo speakers.

### 6.2 Software Requirements
- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Programming Language:** Python 3.10 to 3.13.
- **Web Framework:** Flask 3.1 with `flask-cors`.
- **Speech Libraries:** `SpeechRecognition` 3.17+, `pyttsx3` 2.99+, `pythoncom` (pywin32).
- **Web Browser:** Google Chrome, Microsoft Edge, or Mozilla Firefox.
- **Test Framework:** `pytest` 8.0+.

---

## 7. SYSTEM ARCHITECTURE & DESIGN

The application follows a clean 3-Tier Client-Server Architecture:

```
[ CLIENT TIER ]
   │  HTML5 + CSS3 + Bootstrap 5
   │  Web Audio API (PCM 16-bit WAV Encoder)
   │  SpeechSynthesis (Client Fallback)
   ▼
[ APPLICATION TIER - Flask Server ]
   │  app.py (RESTful API Endpoints)
   │  File Validator & Temp File Lifecycle Manager
   │  Levenshtein DP WER Engine
   ▼
[ ENGINE TIER ]
   │  Google Web Speech API (Cloud ASR Pretrained Inference)
   │  pyttsx3 / Windows SAPI5 (Local Offline Speech Synthesizer)
```

---

## 8. MODULE DESCRIPTIONS

### 8.1 Speech-to-Text (STT) Module
- **File Upload Handler:** Accepts user-submitted audio files, verifies MIME type, checks for `.wav` extension, and validates that file size is within the 16MB ceiling.
- **Microphone Recorder:** Utilizes the browser's `AudioContext` and `ScriptProcessorNode` to capture raw Float32 audio samples from the microphone, converting them into 16-bit integer PCM values and appending a standard 44-byte RIFF header.
- **ASR Transcriber:** Feeds the PCM audio into `speech_recognition.Recognizer()`, which invokes the pretrained Google Web Speech API to obtain the textual transcription.

### 8.2 Text-to-Speech (TTS) Module
- **Text Normalizer:** Checks input text for length limits (max 5,000 characters) and strips extraneous whitespace.
- **Voice Parameter Controller:** Allows configuration of speech velocity (words per minute, 50 to 250 WPM) and volume level (0.0 to 1.0).
- **SAPI5 Synthesizer:** Initializes the COM apartment via `pythoncom.CoInitialize()`, instructs `pyttsx3` to synthesize speech directly into a temporary `.wav` file, encodes the resultant audio into a Base64 data URL, and streams it back to the client.
- **Browser Fallback Synthesizer:** Uses the HTML5 `SpeechSynthesisUtterance` interface to synthesize speech directly within the browser engine if server synthesis is disabled or unavailable.

### 8.3 Word Error Rate (WER) Evaluation Module
- Implements an automated Levenshtein Distance dynamic programming matrix at the word token level.
- Computes exact counts of:
  - **Substitutions ($S$):** Replaced words.
  - **Deletions ($D$):** Omitted words.
  - **Insertions ($I$):** Extraneous words.
  - **Correct Words ($C$):** Exactly matched words.
- Outputs the percentage WER and Recognition Accuracy: $\text{Accuracy} = \max(0, 1 - \text{WER}) \times 100\%$.

### 8.4 REST API & Web Interface Module
- Implements endpoints: `GET /`, `GET /health`, `GET /api/voices`, `POST /api/speech-to-text`, `POST /api/text-to-speech`, and `POST /api/evaluate-wer`.
- Designed with responsive cards, visual loaders, audio players, copy/clear utilities, and cross-tab data routing.

---

## 9. ALGORITHMS & WORKFLOWS

### 9.1 In-Browser 16-Bit PCM WAV Serialization
To guarantee that recorded audio can be decoded without requiring external third-party tools like FFmpeg on Windows, the client JavaScript constructs a compliant RIFF/WAVE container in memory:

```
[Bytes 0-3]   'RIFF'
[Bytes 4-7]   File size - 8
[Bytes 8-11]  'WAVE'
[Bytes 12-15] 'fmt '
[Bytes 16-19] Subchunk size (16 for PCM)
[Bytes 20-21] Audio format (1 = uncompressed PCM)
[Bytes 22-23] Channels (1 = Mono)
[Bytes 24-27] Sample rate (e.g., 16000 or 44100 Hz)
[Bytes 28-31] Byte rate = SampleRate * NumChannels * BitsPerSample / 8
[Bytes 32-33] Block align = NumChannels * BitsPerSample / 8
[Bytes 34-35] Bits per sample (16 bits)
[Bytes 36-39] 'data'
[Bytes 40-43] Data size = Number of samples * 2
[Bytes 44+]   Signed 16-bit PCM sample values (-32768 to 32767)
```

### 9.2 Levenshtein Dynamic Programming Algorithm for WER
Let $R = [r_1, r_2, \dots, r_m]$ be the sequence of reference words.  
Let $H = [h_1, h_2, \dots, h_n]$ be the sequence of hypothesis words.  

The edit distance matrix $D_{(m+1) \times (n+1)}$ is defined recursively:

1. **Initialization:**
   $$D(i, 0) = i \quad \forall i \in \{0, \dots, m\}$$
   $$D(0, j) = j \quad \forall j \in \{0, \dots, n\}$$

2. **Recurrence Relation:**
   For $1 \le i \le m$ and $1 \le j \le n$:
   $$\text{cost} = \begin{cases} 0 & \text{if } r_i = h_j \\ 1 & \text{if } r_i \ne h_j \end{cases}$$
   $$D(i, j) = \min \begin{cases} D(i-1, j) + 1 & \text{(Deletion)} \\ D(i, j-1) + 1 & \text{(Insertion)} \\ D(i-1, j-1) + \text{cost} & \text{(Match or Substitution)} \end{cases}$$

3. **Backtracking:**
   Starting at $(m, n)$, trace back to $(0, 0)$ to resolve exact counts for $S, D, I,$ and $C$.

---

## 10. TESTING & VERIFICATION

Testing was conducted using the `pytest` test framework across 14 automated test suites:

| Test Case Identifier | Component Tested | Input / Condition | Expected Result | Status |
|---|---|---|---|---|
| `TC-01` | Server Startup | `GET /` | HTTP 200, HTML returned | **PASS** |
| `TC-02` | Health Endpoint | `GET /health` | HTTP 200, status "healthy" | **PASS** |
| `TC-03` | Voices Enumeration | `GET /api/voices` | HTTP 200, list of SAPI5 voices | **PASS** |
| `TC-04` | TTS Empty Input | `POST /api/text-to-speech` with `""` | HTTP 400, "Text cannot be empty" | **PASS** |
| `TC-05` | TTS Length Ceiling | Text with > 5000 characters | HTTP 400, "Text is too long" | **PASS** |
| `TC-06` | TTS Synthesis | Valid text ("Hello world test") | HTTP 200, valid base64 WAV | **PASS** |
| `TC-07` | STT Missing File | Empty multipart POST | HTTP 400, "No audio file" | **PASS** |
| `TC-08` | STT Invalid Extension | File named `test.txt` | HTTP 400, "Unsupported format" | **PASS** |
| `TC-09` | STT Empty Audio File | 0-byte `.wav` upload | HTTP 400, "File is empty" | **PASS** |
| `TC-10` | STT End-to-End | Synthetic speech WAV file | HTTP 200, transcription matched | **PASS** |
| `TC-11` | WER Identical Match | "the quick brown fox" vs identical | WER = 0.0%, Accuracy = 100.0% | **PASS** |
| `TC-12` | WER With Errors | 1 Substitution, 1 Insertion | WER = 50.0%, Accuracy = 50.0% | **PASS** |
| `TC-13` | WER Empty Input | Empty reference & hypothesis | HTTP 400, validation error | **PASS** |
| `TC-14` | WER Full Endpoint | Non-empty strings via API | HTTP 200, detailed stats returned | **PASS** |

**Overall Test Result:** 14 Passed / 0 Failed (100% Pass Rate).

---

## 11. ADVANTAGES & LIMITATIONS

### Advantages:
1. **Lightweight & Fast:** Runs easily on normal student laptops without high-end GPUs.
2. **Offline TTS:** Text-to-Speech runs without internet connectivity via Windows SAPI5.
3. **No External Datasets:** Bypasses Kaggle storage requirements while retaining rigorous AI evaluation.
4. **Thread-Safe Architecture:** COM apartment initialization prevents Flask worker crashes on Windows.
5. **Educational Value:** Word Error Rate module provides clear mathematical insights into ASR metrics.

### Limitations:
1. **Internet Dependency for STT:** Speech recognition uses Google's public cloud endpoint and requires an active internet connection.
2. **Audio Container Constraint:** Only standard uncompressed 16-bit PCM `.wav` is supported unless FFmpeg is installed manually.
3. **Local Voices:** The quality and accent of pyttsx3 depends on the voices pre-installed in the Windows operating system.

---

## 12. FUTURE SCOPE

1. **Embedded Offline STT Model:** Integrate lightweight local neural models such as Vosk or OpenAI Whisper (`tiny.en`) for 100% offline speech recognition.
2. **Multilingual Support:** Add Hindi, Spanish, French, and regional language models for non-English transcription.
3. **WebSocket Real-Time Streaming:** Implement real-time audio chunk streaming over WebSockets for live subtitle generation.
4. **Speech Summarization:** Incorporate a lightweight transformer model (such as T5-small) to summarize transcribed lectures automatically.

---

## 13. CONCLUSION

The **Speech-to-Text and Text-to-Speech Conversion System** successfully demonstrates a practical, robust, and accessible application of voice processing in modern computing. By combining Flask, `SpeechRecognition`, `pyttsx3`, and client-side Web Audio API PCM encoding, the system achieves rapid voice-to-text transcription and offline text-to-voice synthesis. Furthermore, the inclusion of the Word Error Rate (WER) evaluation module establishes a rigorous academic foundation, allowing students to evaluate recognition quality algorithmically without the burden of training multi-gigabyte datasets. The project is production-tested, fully documented, and well-suited for college presentation and viva evaluation.

---

## 14. REFERENCES

1. Jurafsky, D., & Martin, J. H. (2023). *Speech and Language Processing*. Pearson.
2. Levenshtein, V. I. (1966). Binary codes capable of correcting deletions, insertions, and reversals. *Soviet Physics Doklady*, 10(8), 707–710.
3. Microsoft Corporation. (2022). *Microsoft Speech API (SAPI) 5.4 Overview*. MSDN Documentation.
4. Grinberg, M. (2018). *Flask Web Development: Developing Web Applications with Python*. O'Reilly Media.
5. W3C Web Audio Working Group. (2021). *Web Audio API: W3C Recommendation*. W3C Standards.
