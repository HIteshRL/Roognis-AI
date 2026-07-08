import os
import tempfile

import structlog

from src.infrastructure.videogen.base import AbstractVideoGenerator, VideoResult

logger = structlog.get_logger(__name__)

# Cache the loaded pipeline across calls — model load is expensive (several GB).
_pipeline = None


class LTXVideoGenerator(AbstractVideoGenerator):
    """Self-hosted LTX-Video via diffusers, running on a CUDA GPU.

    torch/diffusers are heavy, optional deps — imported lazily so the app runs
    without them installed (use the 'stub' provider on GPU-less machines).
    Install with: pip install -e '.[video]'
    """

    def __init__(
        self,
        model_id: str = "Lightricks/LTX-Video",
        width: int = 704,
        height: int = 480,
        num_inference_steps: int = 40,
        guidance_scale: float = 3.0,
    ) -> None:
        self._model_id = model_id
        self._width = width
        self._height = height
        self._steps = num_inference_steps
        self._guidance_scale = guidance_scale

    @property
    def provider_name(self) -> str:
        return "ltx"

    def _load_pipeline(self):
        global _pipeline
        if _pipeline is not None:
            return _pipeline
        try:
            import torch
            from diffusers import LTXPipeline
        except ImportError as exc:
            raise RuntimeError(
                "Video backend not configured: torch/diffusers not installed. "
                "Install with pip install -e '.[video]' and ensure a CUDA GPU is available."
            ) from exc

        if not torch.cuda.is_available():
            raise RuntimeError("Video backend requires a CUDA GPU (torch.cuda unavailable)")

        pipe = LTXPipeline.from_pretrained(self._model_id, torch_dtype=torch.bfloat16)
        pipe.to("cuda")
        _pipeline = pipe
        logger.info("ltx_pipeline_loaded", model=self._model_id)
        return _pipeline

    def generate(self, prompt: str, num_frames: int = 97, fps: int = 24) -> VideoResult:
        from diffusers.utils import export_to_video

        pipe = self._load_pipeline()
        result = pipe(
            prompt=prompt,
            width=self._width,
            height=self._height,
            num_frames=num_frames,
            num_inference_steps=self._steps,
            guidance_scale=self._guidance_scale,
        )
        frames = result.frames[0]

        tmp_path = ""
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            export_to_video(frames, tmp_path, fps=fps)
            with open(tmp_path, "rb") as f:
                data = f.read()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        logger.info("ltx_video_generated", bytes=len(data), frames=num_frames)
        return VideoResult(data=data, content_type="video/mp4")
