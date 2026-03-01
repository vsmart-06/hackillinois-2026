"""Modal endpoint for Whisper voice transcription.

Deploy with: modal deploy modal/modal_whisper.py
Then call via HTTP POST to the deployed URL, or use the FastAPI backend proxy at POST /api/transcribe.
"""

import modal

app = modal.App("semflow-whisper")

# Build image with whisper and dependencies
whisper_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "openai-whisper==20231117",
        "torch==2.1.0",
        "torchaudio==2.1.0",
        "ffmpeg-python",
    )
    .apt_install("ffmpeg")
)


@app.cls(
    image=whisper_image,
    gpu="T4",
    keep_warm=1,  # Keep one container warm to avoid cold start in demo
    container_idle_timeout=300,
)
class WhisperTranscriber:
    @modal.enter()
    def load_model(self):
        import whisper

        # Load medium model — good balance of speed and accuracy
        self.model = whisper.load_model("medium")

    @modal.method()
    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text. Audio can be any format ffmpeg supports."""
        import os
        import tempfile

        # Write bytes to temp file since whisper needs a file path
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            result = self.model.transcribe(tmp_path, language="en")
            return result["text"].strip()
        finally:
            os.unlink(tmp_path)


# Web endpoint so FastAPI can call it via HTTP
@app.function(image=whisper_image, keep_warm=1)
@modal.web_endpoint(method="POST")
def transcribe_endpoint(payload: dict) -> dict:
    """
    POST body: { "audio_b64": "<base64 encoded audio bytes>" }
    Returns:   { "text": "<transcription>" }
    """
    import base64

    audio_b64 = payload.get("audio_b64", "")
    if not audio_b64:
        return {"error": "No audio_b64 provided", "text": ""}

    audio_bytes = base64.b64decode(audio_b64)
    transcriber = WhisperTranscriber()
    text = transcriber.transcribe.remote(audio_bytes)
    return {"text": text}
