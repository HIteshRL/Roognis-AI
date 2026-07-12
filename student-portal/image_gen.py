"""Text-to-image for the Image Studio, via HF Inference (fal-ai provider).

Fail-open like the rest of the demo: when HF_TOKEN is unset or huggingface_hub
isn't installed, we return a clear message instead of a 500 so the studio UI can
degrade gracefully. The blocking network call + PNG encode run in a worker thread
(see app.py) so the event loop is never stalled.

Config (all optional):
  HF_TOKEN         — Hugging Face access token; enables generation when present.
  IMAGE_MODEL      — text-to-image model id (default: FLUX.1-schnell).
  IMAGE_PROVIDER   — HF Inference provider routing (default: fal-ai).
"""
import base64
import io
import os

_MODEL = os.getenv("IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
_PROVIDER = os.getenv("IMAGE_PROVIDER", "fal-ai")
# Portrait output so it fills the iPhone-15 screen with minimal cover-cropping.
_WIDTH = int(os.getenv("IMAGE_WIDTH", "768"))
_HEIGHT = int(os.getenv("IMAGE_HEIGHT", "1152"))


def is_configured() -> bool:
    return bool(os.getenv("HF_TOKEN"))


def generate(prompt: str) -> dict:
    """Return {"ok": True, "data_url": ..., "model": ...} or {"ok": False, "error": ...}.

    Synchronous (blocking) — call from a worker thread, never the event loop.
    """
    token = os.getenv("HF_TOKEN")
    if not token:
        return {"ok": False, "error": "Image Studio isn't switched on yet. "
                "Set HF_TOKEN on the server to enable it."}
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        return {"ok": False,
                "error": "The huggingface_hub package isn't installed on the server."}
    try:
        client = InferenceClient(provider=_PROVIDER, api_key=token)
        image = client.text_to_image(prompt, model=_MODEL, width=_WIDTH, height=_HEIGHT)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return {"ok": True, "data_url": f"data:image/png;base64,{b64}", "model": _MODEL}
    except Exception as exc:  # fail-open: never surface a 500 to the studio
        return {"ok": False, "error": f"Couldn't generate that image just now: {exc}"}
