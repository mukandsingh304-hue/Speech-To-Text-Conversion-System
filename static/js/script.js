/**
 * VoiceFlow Speech System - Frontend Controller
 * ==============================================
 * Handles:
 * - Live microphone recording with in-browser 16-bit PCM WAV encoding.
 * - Drag-and-drop & file selection for audio uploads (.wav).
 * - Speech-to-Text inference API communication.
 * - Text-to-Speech synthesis (pyttsx3 & Web Speech API fallback).
 * - Word Error Rate (WER) algorithmic evaluation.
 */

document.addEventListener("DOMContentLoaded", () => {
    // State variables
    let currentAudioBlob = null;
    let audioContext = null;
    let mediaStream = null;
    let scriptProcessor = null;
    let recordedBuffers = [];
    let isRecording = false;
    let recordingTimerInterval = null;
    let recordingStartTime = 0;
    let serverVoices = [];

    // DOM Elements - STT
    const sttModeUpload = document.getElementById("sttModeUpload");
    const sttModeMic = document.getElementById("sttModeMic");
    const uploadContainer = document.getElementById("uploadContainer");
    const micContainer = document.getElementById("micContainer");
    const audioDropZone = document.getElementById("audioDropZone");
    const audioFileInput = document.getElementById("audioFileInput");
    const fileDetails = document.getElementById("fileDetails");
    const selectedFileName = document.getElementById("selectedFileName");
    const selectedFileSize = document.getElementById("selectedFileSize");
    const btnRemoveFile = document.getElementById("btnRemoveFile");
    const audioPreviewContainer = document.getElementById("audioPreviewContainer");
    const audioPreviewPlayer = document.getElementById("audioPreviewPlayer");
    const btnStartRecord = document.getElementById("btnStartRecord");
    const btnStopRecord = document.getElementById("btnStopRecord");
    const recordingVisualizer = document.getElementById("recordingVisualizer");
    const recordingTimer = document.getElementById("recordingTimer");
    const recordingStatusText = document.getElementById("recordingStatusText");
    const btnTranscribe = document.getElementById("btnTranscribe");
    const sttLoading = document.getElementById("sttLoading");
    const sttOutputArea = document.getElementById("sttOutputArea");
    const transcriptionText = document.getElementById("transcriptionText");
    const sttStats = document.getElementById("sttStats");
    const sttDurationBadge = document.getElementById("sttDurationBadge");
    const sttAlert = document.getElementById("sttAlert");
    const btnCopyTranscription = document.getElementById("btnCopyTranscription");
    const btnClearTranscription = document.getElementById("btnClearTranscription");
    const btnSendToTTS = document.getElementById("btnSendToTTS");
    const btnSendToWER = document.getElementById("btnSendToWER");

    // DOM Elements - TTS
    const ttsTextInput = document.getElementById("ttsTextInput");
    const ttsCharCount = document.getElementById("ttsCharCount");
    const ttsWordCount = document.getElementById("ttsWordCount");
    const btnClearTTS = document.getElementById("btnClearTTS");
    const btnSynthesize = document.getElementById("btnSynthesize");
    const ttsLoading = document.getElementById("ttsLoading");
    const ttsAudioPlayer = document.getElementById("ttsAudioPlayer");
    const btnDownloadTTS = document.getElementById("btnDownloadTTS");
    const ttsGeneratedSize = document.getElementById("ttsGeneratedSize");
    const ttsGeneratedStatus = document.getElementById("ttsGeneratedStatus");
    const ttsVoiceSelect = document.getElementById("ttsVoiceSelect");
    const speechRateRange = document.getElementById("speechRateRange");
    const speechRateValue = document.getElementById("speechRateValue");
    const speechVolumeRange = document.getElementById("speechVolumeRange");
    const speechVolumeValue = document.getElementById("speechVolumeValue");
    const btnResetTTSControls = document.getElementById("btnResetTTSControls");
    const ttsEngineSelect = document.getElementById("ttsEngineSelect");
    const engineNotice = document.getElementById("engineNotice");
    const ttsAlert = document.getElementById("ttsAlert");

    // DOM Elements - WER
    const werReferenceText = document.getElementById("werReferenceText");
    const werHypothesisText = document.getElementById("werHypothesisText");
    const btnCalculateWER = document.getElementById("btnCalculateWER");
    const btnWerSample = document.getElementById("btnWerSample");
    const werResultsArea = document.getElementById("werResultsArea");
    const werValue = document.getElementById("werValue");
    const werBadge = document.getElementById("werBadge");
    const werAccuracyValue = document.getElementById("werAccuracyValue");
    const werSubstitutions = document.getElementById("werSubstitutions");
    const werDeletions = document.getElementById("werDeletions");
    const werInsertions = document.getElementById("werInsertions");
    const werCorrect = document.getElementById("werCorrect");
    const werRefWords = document.getElementById("werRefWords");
    const werHypWords = document.getElementById("werHypWords");
    const werFormulaCalculation = document.getElementById("werFormulaCalculation");

    // ------------------------------------------------------------------------
    // 1. Initial Setup & System Voices Loading
    // ------------------------------------------------------------------------
    async function loadVoices() {
        try {
            const response = await fetch("/api/voices");
            const data = await response.json();
            if (data.success && data.voices && data.voices.length > 0) {
                serverVoices = data.voices;
                ttsVoiceSelect.innerHTML = "";
                serverVoices.forEach((voice, index) => {
                    const opt = document.createElement("option");
                    opt.value = voice.id;
                    opt.textContent = `${voice.name} (${voice.gender || "System"})`;
                    if (index === 0) opt.selected = true;
                    ttsVoiceSelect.appendChild(opt);
                });
            } else {
                ttsVoiceSelect.innerHTML = '<option value="">Default System Voice</option>';
            }
        } catch (err) {
            console.warn("Could not fetch system voices from server:", err);
            ttsVoiceSelect.innerHTML = '<option value="">Default System Voice</option>';
        }
    }
    loadVoices();

    // Check system health on load
    fetch("/health")
        .then(res => res.json())
        .then(data => {
            const pill = document.getElementById("system-status-pill");
            if (pill && data.status === "healthy") {
                pill.innerHTML = `<span class="status-dot"></span> System Ready (${data.tts.mode})`;
            }
        })
        .catch(() => {
            const pill = document.getElementById("system-status-pill");
            if (pill) {
                pill.className = "badge bg-warning-subtle text-warning border border-warning-subtle rounded-pill px-3 py-2";
                pill.textContent = "Offline / Standalone Mode";
            }
        });

    // ------------------------------------------------------------------------
    // 2. Speech-to-Text Mode Toggling (Upload vs Microphone)
    // ------------------------------------------------------------------------
    sttModeUpload.addEventListener("change", () => {
        if (sttModeUpload.checked) {
            uploadContainer.classList.remove("d-none");
            micContainer.classList.add("d-none");
            stopRecordingIfActive();
        }
    });

    sttModeMic.addEventListener("change", () => {
        if (sttModeMic.checked) {
            uploadContainer.classList.add("d-none");
            micContainer.classList.remove("d-none");
        }
    });

    // ------------------------------------------------------------------------
    // 3. Audio File Upload & Drag-and-Drop
    // ------------------------------------------------------------------------
    audioDropZone.addEventListener("click", () => audioFileInput.click());

    audioDropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        audioDropZone.classList.add("dragover");
    });

    audioDropZone.addEventListener("dragleave", () => {
        audioDropZone.classList.remove("dragover");
    });

    audioDropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        audioDropZone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleSelectedFile(e.dataTransfer.files[0]);
        }
    });

    audioFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    function handleSelectedFile(file) {
        if (!file.name.toLowerCase().endsWith(".wav")) {
            showSttAlert("Please select a standard uncompressed WAV audio file (.wav).", "danger");
            return;
        }

        if (file.size > 16 * 1024 * 1024) {
            showSttAlert("The selected file is too large. Maximum allowed size is 16MB.", "danger");
            return;
        }

        currentAudioBlob = file;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);
        fileDetails.classList.remove("d-none");
        fileDetails.classList.add("d-flex");

        // Preview player
        audioPreviewPlayer.src = URL.createObjectURL(file);
        audioPreviewContainer.classList.remove("d-none");
        hideSttAlert();
    }

    btnRemoveFile.addEventListener("click", () => {
        currentAudioBlob = null;
        audioFileInput.value = "";
        fileDetails.classList.add("d-none");
        fileDetails.classList.remove("d-flex");
        audioPreviewContainer.classList.add("d-none");
        audioPreviewPlayer.src = "";
    });

    // ------------------------------------------------------------------------
    // 4. Live Microphone Recording with 16-bit PCM WAV Encoding
    // ------------------------------------------------------------------------
    btnStartRecord.addEventListener("click", async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaStream = stream;

            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            audioContext = new AudioCtx();
            const source = audioContext.createMediaStreamSource(stream);

            // Buffer size 4096, 1 input channel (mono)
            scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
            recordedBuffers = [];

            scriptProcessor.onaudioprocess = (e) => {
                if (!isRecording) return;
                const channelData = e.inputBuffer.getChannelData(0);
                recordedBuffers.push(new Float32Array(channelData));
            };

            source.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);

            isRecording = true;
            btnStartRecord.classList.add("d-none");
            btnStopRecord.classList.remove("d-none");
            recordingVisualizer.classList.add("recording");
            recordingStatusText.textContent = "Listening... Speak clearly into your microphone.";

            recordingStartTime = Date.now();
            recordingTimer.textContent = "00:00";
            recordingTimerInterval = setInterval(() => {
                const elapsedSec = Math.floor((Date.now() - recordingStartTime) / 1000);
                const mm = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
                const ss = String(elapsedSec % 60).padStart(2, "0");
                recordingTimer.textContent = `${mm}:${ss}`;
            }, 500);

            hideSttAlert();
        } catch (err) {
            console.error("Microphone access error:", err);
            showSttAlert("Could not access microphone. Please check browser microphone permissions or upload a WAV file.", "danger");
        }
    });

    btnStopRecord.addEventListener("click", () => {
        stopRecording();
    });

    function stopRecordingIfActive() {
        if (isRecording) {
            stopRecording();
        }
    }

    function stopRecording() {
        if (!isRecording) return;
        isRecording = false;

        clearInterval(recordingTimerInterval);
        btnStartRecord.classList.remove("d-none");
        btnStopRecord.classList.add("d-none");
        recordingVisualizer.classList.remove("recording");
        recordingStatusText.textContent = "Recording complete! Audio ready for transcription.";

        // Clean up audio nodes
        if (scriptProcessor) scriptProcessor.disconnect();
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
        }

        // Encode recorded buffers into 16-bit PCM WAV
        if (recordedBuffers.length > 0 && audioContext) {
            const wavBlob = encodeWAV(recordedBuffers, audioContext.sampleRate);
            currentAudioBlob = wavBlob;
            audioPreviewPlayer.src = URL.createObjectURL(wavBlob);
            audioPreviewContainer.classList.remove("d-none");
        }

        if (audioContext && audioContext.state !== "closed") {
            audioContext.close();
        }
    }

    /**
     * Encodes raw Float32 audio buffers into a standard 16-bit PCM WAV Blob.
     */
    function encodeWAV(buffers, sampleRate) {
        // Flatten buffers
        let totalLength = 0;
        for (let i = 0; i < buffers.length; i++) {
            totalLength += buffers[i].length;
        }
        const mergedSamples = new Float32Array(totalLength);
        let offset = 0;
        for (let i = 0; i < buffers.length; i++) {
            mergedSamples.set(buffers[i], offset);
            offset += buffers[i].length;
        }

        // WAV Header: 44 bytes
        const buffer = new ArrayBuffer(44 + mergedSamples.length * 2);
        const view = new DataView(buffer);

        // RIFF chunk descriptor
        writeString(view, 0, "RIFF");
        view.setUint32(4, 36 + mergedSamples.length * 2, true);
        writeString(view, 8, "WAVE");

        // fmt sub-chunk
        writeString(view, 12, "fmt ");
        view.setUint32(16, 16, true);          // Subchunk1Size (16 for PCM)
        view.setUint16(20, 1, true);           // AudioFormat (1 = PCM)
        view.setUint16(22, 1, true);           // NumChannels (1 = Mono)
        view.setUint32(24, sampleRate, true);  // SampleRate
        view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * 1 * 16/8)
        view.setUint16(32, 2, true);           // BlockAlign (1 * 16/8)
        view.setUint16(34, 16, true);          // BitsPerSample (16 bits)

        // data sub-chunk
        writeString(view, 36, "data");
        view.setUint32(40, mergedSamples.length * 2, true);

        // Write 16-bit PCM samples
        let sampleOffset = 44;
        for (let i = 0; i < mergedSamples.length; i++, sampleOffset += 2) {
            let s = Math.max(-1, Math.min(1, mergedSamples[i]));
            view.setInt16(sampleOffset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }

        return new Blob([view], { type: "audio/wav" });
    }

    function writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    // ------------------------------------------------------------------------
    // 5. Speech-to-Text Transcription Request
    // ------------------------------------------------------------------------
    btnTranscribe.addEventListener("click", async () => {
        stopRecordingIfActive();

        if (!currentAudioBlob) {
            showSttAlert("Please upload a WAV audio file or record speech first.", "warning");
            return;
        }

        hideSttAlert();
        sttLoading.classList.remove("d-none");
        sttOutputArea.classList.add("opacity-50");
        btnTranscribe.disabled = true;

        const formData = new FormData();
        const filename = currentAudioBlob.name || "recording.wav";
        formData.append("file", currentAudioBlob, filename);

        try {
            const response = await fetch("/api/speech-to-text", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                transcriptionText.value = data.text;
                updateSTTStats();
                if (data.audio_duration) {
                    sttDurationBadge.textContent = `Duration: ${data.audio_duration}s`;
                    sttDurationBadge.classList.remove("d-none");
                }
                showSttAlert("Audio transcribed successfully!", "success");
            } else {
                showSttAlert(data.error || "Speech recognition failed. Please try again.", "danger");
            }
        } catch (err) {
            console.error("STT network error:", err);
            showSttAlert("Network error while connecting to server. Please ensure the Flask app is running.", "danger");
        } finally {
            sttLoading.classList.add("d-none");
            sttOutputArea.classList.remove("opacity-50");
            btnTranscribe.disabled = false;
        }
    });

    transcriptionText.addEventListener("input", updateSTTStats);

    function updateSTTStats() {
        const text = transcriptionText.value.trim();
        const chars = text.length;
        const words = text ? text.split(/\s+/).length : 0;
        sttStats.textContent = `Characters: ${chars} | Words: ${words}`;
    }

    btnCopyTranscription.addEventListener("click", () => {
        if (!transcriptionText.value.trim()) return;
        navigator.clipboard.writeText(transcriptionText.value).then(() => {
            const originalHtml = btnCopyTranscription.innerHTML;
            btnCopyTranscription.innerHTML = '<i class="bi bi-check2 text-success me-1"></i> Copied!';
            setTimeout(() => {
                btnCopyTranscription.innerHTML = originalHtml;
            }, 2000);
        });
    });

    btnClearTranscription.addEventListener("click", () => {
        transcriptionText.value = "";
        updateSTTStats();
        sttDurationBadge.classList.add("d-none");
        hideSttAlert();
    });

    // Cross-Module Handlers
    btnSendToTTS.addEventListener("click", () => {
        const text = transcriptionText.value.trim();
        if (!text) {
            showSttAlert("No recognized text to send to Text-to-Speech.", "warning");
            return;
        }
        ttsTextInput.value = text;
        updateTTSCounts();
        // Switch to TTS tab
        const ttsTabTrigger = document.getElementById("tts-tab");
        const tab = new bootstrap.Tab(ttsTabTrigger);
        tab.show();
    });

    btnSendToWER.addEventListener("click", () => {
        const text = transcriptionText.value.trim();
        if (!text) {
            showSttAlert("No recognized text to send to WER Evaluator.", "warning");
            return;
        }
        werHypothesisText.value = text;
        // Switch to WER tab
        const werTabTrigger = document.getElementById("wer-tab");
        const tab = new bootstrap.Tab(werTabTrigger);
        tab.show();
    });

    function showSttAlert(msg, type = "info") {
        sttAlert.className = `alert alert-${type} mt-3 mb-0`;
        sttAlert.textContent = msg;
        sttAlert.classList.remove("d-none");
    }

    function hideSttAlert() {
        sttAlert.classList.add("d-none");
    }

    // ------------------------------------------------------------------------
    // 6. Text-to-Speech (TTS) Feature
    // ------------------------------------------------------------------------
    ttsTextInput.addEventListener("input", updateTTSCounts);

    function updateTTSCounts() {
        const text = ttsTextInput.value;
        ttsCharCount.textContent = `Characters: ${text.length} / 5000`;
        const words = text.trim() ? text.trim().split(/\s+/).length : 0;
        ttsWordCount.textContent = `Words: ${words}`;
    }

    // Sliders
    speechRateRange.addEventListener("input", () => {
        const rate = speechRateRange.value;
        let speedLabel = "Normal";
        if (rate < 120) speedLabel = "Slow";
        else if (rate > 180) speedLabel = "Fast";
        speechRateValue.textContent = `${rate} WPM (${speedLabel})`;
    });

    speechVolumeRange.addEventListener("input", () => {
        const pct = Math.round(speechVolumeRange.value * 100);
        speechVolumeValue.textContent = `${pct}%`;
    });

    btnResetTTSControls.addEventListener("click", () => {
        speechRateRange.value = 150;
        speechRateValue.textContent = "150 WPM (Normal)";
        speechVolumeRange.value = 1.0;
        speechVolumeValue.textContent = "100%";
        if (ttsVoiceSelect.options.length > 0) ttsVoiceSelect.selectedIndex = 0;
    });

    btnClearTTS.addEventListener("click", () => {
        ttsTextInput.value = "";
        updateTTSCounts();
        hideTtsAlert();
    });

    // Preset buttons
    document.querySelectorAll(".preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            ttsTextInput.value = btn.dataset.text;
            updateTTSCounts();
            hideTtsAlert();
        });
    });

    ttsEngineSelect.addEventListener("change", () => {
        if (ttsEngineSelect.value === "browser") {
            engineNotice.textContent = "Browser SpeechSynthesis runs directly inside your web browser.";
        } else {
            engineNotice.textContent = "pyttsx3 runs 100% offline on Windows using the SAPI5 speech engine.";
        }
    });

    // Synthesize button
    btnSynthesize.addEventListener("click", async () => {
        const text = ttsTextInput.value.trim();
        if (!text) {
            showTtsAlert("Please enter text to synthesize into speech.", "warning");
            return;
        }

        hideTtsAlert();
        const engine = ttsEngineSelect.value;

        // Option 1: Browser Web Speech API fallback
        if (engine === "browser") {
            if ("speechSynthesis" in window) {
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = speechRateRange.value / 150;
                utterance.volume = parseFloat(speechVolumeRange.value);
                window.speechSynthesis.speak(utterance);
                ttsGeneratedStatus.textContent = "Playing via Browser SpeechSynthesis";
                showTtsAlert("Speaking via browser speech synthesis...", "success");
            } else {
                showTtsAlert("Browser speech synthesis is not supported in this browser.", "danger");
            }
            return;
        }

        // Option 2: Server Offline pyttsx3 (SAPI5 on Windows)
        ttsLoading.classList.remove("d-none");
        btnSynthesize.disabled = true;

        try {
            const payload = {
                text: text,
                rate: parseInt(speechRateRange.value, 10),
                volume: parseFloat(speechVolumeRange.value),
                voice_id: ttsVoiceSelect.value || null
            };

            const response = await fetch("/api/text-to-speech", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok && data.success) {
                ttsAudioPlayer.src = data.audio_url;
                ttsAudioPlayer.play().catch(() => {
                    // Browser autoplay policy might require manual click
                });

                btnDownloadTTS.href = data.audio_url;
                btnDownloadTTS.classList.remove("disabled");

                ttsGeneratedSize.textContent = `File Size: ${formatBytes(data.file_size)}`;
                ttsGeneratedStatus.textContent = "Status: Generated";
                showTtsAlert(`Audio synthesized successfully (${data.word_count} words).`, "success");
            } else {
                showTtsAlert(data.error || "Failed to generate speech.", "danger");
            }
        } catch (err) {
            console.error("TTS fetch error:", err);
            showTtsAlert("Network error connecting to TTS server. You can toggle to Browser SpeechSynthesis.", "danger");
        } finally {
            ttsLoading.classList.add("d-none");
            btnSynthesize.disabled = false;
        }
    });

    function showTtsAlert(msg, type = "info") {
        ttsAlert.className = `alert alert-${type} mt-3 mb-0`;
        ttsAlert.textContent = msg;
        ttsAlert.classList.remove("d-none");
    }

    function hideTtsAlert() {
        ttsAlert.classList.add("d-none");
    }

    // ------------------------------------------------------------------------
    // 7. AI/ML Word Error Rate (WER) Evaluation
    // ------------------------------------------------------------------------
    btnWerSample.addEventListener("click", () => {
        werReferenceText.value = "the quick brown fox jumps over the lazy dog";
        werHypothesisText.value = "the fast brown fox jumps over a lazy dog";
    });

    btnCalculateWER.addEventListener("click", async () => {
        const reference = werReferenceText.value.trim();
        const hypothesis = werHypothesisText.value.trim();

        if (!reference && !hypothesis) {
            alert("Please enter both reference text and recognized text to evaluate.");
            return;
        }

        try {
            const response = await fetch("/api/evaluate-wer", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reference, hypothesis })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                const res = data.results;
                werValue.textContent = `${res.wer}%`;
                werAccuracyValue.textContent = `${res.accuracy}%`;
                werSubstitutions.textContent = res.substitutions;
                werDeletions.textContent = res.deletions;
                werInsertions.textContent = res.insertions;
                werCorrect.textContent = res.correct;
                werRefWords.textContent = res.reference_words;
                werHypWords.textContent = res.hypothesis_words;

                // Color code WER badge
                if (res.wer <= 15.0) {
                    werBadge.className = "badge bg-success mx-auto px-3 py-1";
                    werBadge.textContent = "High Accuracy (Excellent)";
                } else if (res.wer <= 35.0) {
                    werBadge.className = "badge bg-warning text-dark mx-auto px-3 py-1";
                    werBadge.textContent = "Moderate Accuracy (Acceptable)";
                } else {
                    werBadge.className = "badge bg-danger mx-auto px-3 py-1";
                    werBadge.textContent = "Low Accuracy (Noisy / Error-Prone)";
                }

                werFormulaCalculation.textContent = `WER = (${res.substitutions} + ${res.deletions} + ${res.insertions}) / ${res.reference_words} = ${res.wer}%`;
                werResultsArea.classList.remove("d-none");
                werResultsArea.scrollIntoView({ behavior: "smooth" });
            } else {
                alert(data.error || "Error calculating WER.");
            }
        } catch (err) {
            console.error("WER calculation error:", err);
            alert("Error communicating with evaluation endpoint.");
        }
    });

    // Helper: format bytes
    function formatBytes(bytes, decimals = 1) {
        if (!bytes || bytes === 0) return "0 Bytes";
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
    }
});
