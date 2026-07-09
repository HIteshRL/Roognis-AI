import base64

import structlog

from src.infrastructure.videogen.base import AbstractVideoGenerator, VideoResult

logger = structlog.get_logger(__name__)

# Minimal ISO-BMFF mp4 container (ftyp + mdat) — served as a placeholder so the
# full job/attachment/polling pipeline can run on a machine without a GPU.
_PLACEHOLDER_MP4 = base64.b64decode(
    "AAAAHGZ0eXBpc29tAAACAGlzb21pc28ybXA0MQAAAAhmcmVlAAAAKG1kYXQAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)


def _synthesize_with_imageio(num_frames: int, fps: int) -> bytes | None:
    """Produce a real, playable gradient clip if imageio+numpy are installed."""
    try:
        import io

        import imageio.v3 as iio
        import numpy as np
    except ImportError:
        return None

    frames = []
    for i in range(max(1, min(num_frames, 48))):
        shade = int(255 * (i / max(1, num_frames)))
        frame = np.full((256, 256, 3), shade, dtype=np.uint8)
        frame[:, :, 0] = (shade + 80) % 256
        frames.append(frame)

    buf = io.BytesIO()
    iio.imwrite(buf, frames, extension=".mp4", fps=fps)
    return buf.getvalue()


class StubVideoGenerator(AbstractVideoGenerator):
    """GPU-less stand-in for LTX — real clip via imageio if present, else a
    tiny placeholder mp4. Lets the job lifecycle + UI be exercised without CUDA.
    """

    @property
    def provider_name(self) -> str:
        return "stub"

    def generate(self, prompt: str, num_frames: int = 97, fps: int = 24) -> VideoResult:
        data = _synthesize_with_imageio(num_frames, fps)
        if data is None:
            logger.warning("stub_video_placeholder", reason="imageio_unavailable")
            data = _PLACEHOLDER_MP4
        return VideoResult(data=data, content_type="video/mp4")
