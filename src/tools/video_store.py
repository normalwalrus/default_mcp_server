"""
In-memory video store for the MCP server.

Allows clients to upload base64-encoded videos and receive a short video_id
back. Tools can then retrieve the video bytes by ID instead of requiring the
LLM to pass enormous base64 strings as tool arguments.
"""

import base64
import logging
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)

logger = logging.getLogger("mcp-video-store")

# In-memory store: video_id -> raw video bytes
_store: dict[str, bytes] = {}


def store_video(video_base64: str) -> str:
    """
    Decode a base64-encoded video, store it, and return a
    short ``video_id``.

    Parameters
    ----------
    video_base64 : str
        The video as a base64 string.  A ``data:<mime>;base64,`` prefix is
        stripped automatically if present.

    Returns
    -------
    str
        A unique ``video_id`` that can be used to retrieve the video later.
    """
    # Strip optional data-URL prefix
    if "," in video_base64[:100]:
        video_base64 = video_base64.split(",", 1)[1]

    video_bytes = base64.b64decode(video_base64)

    video_id = str(uuid.uuid4())[:8]
    _store[video_id] = video_bytes

    logger.info(
        "Stored video %s (%d bytes)",
        video_id,
        len(video_bytes),
    )

    return video_id


def get_video(video_id: str) -> bytes | None:
    """
    Retrieve stored video bytes by ``video_id``.

    Returns
    -------
    bytes | None
        The raw video bytes, or ``None`` if the ID is not found.
    """
    return _store.get(video_id)


def delete_video(video_id: str) -> bool:
    """
    Remove a video from the store.

    Returns
    -------
    bool
        ``True`` if the video was found and deleted, ``False`` otherwise.
    """
    if video_id in _store:
        del _store[video_id]
        logger.info("Deleted video %s", video_id)
        return True
    return False


def list_videos() -> list[str]:
    """Return a list of all stored video IDs."""
    return list(_store.keys())