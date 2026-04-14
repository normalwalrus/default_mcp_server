from fastmcp import FastMCP
from tools.object_detection import detect_objects_in_image
from tools.fake_object_detection import fake_detect_objects
from tools.image_store import store_image, list_images
from tools.video_store import store_video, list_videos
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)

logger = logging.getLogger("mcp-server")

# Create MCP server
mcp = FastMCP("mcp-server")

@mcp.tool(
    name="upload_image",
    description="Upload a base64-encoded image to the server and receive a short image_id. Use this to store images before passing them to other tools like object_detection.",
)
def upload_image(image_base64: str) -> str:
    """
    Upload a base64-encoded image and get back a short image_id.

    Args:
        image_base64: The image as a base64 string (data-URL prefix is stripped automatically).

    Returns:
        A short image_id string that can be passed to other tools.
    """
    image_id = store_image(image_base64)
    logger.info(f"Image uploaded with id: {image_id}")
    return image_id


@mcp.tool(
    name="list_uploaded_images",
    description="List all image IDs currently stored on the server.",
)
def list_uploaded_images() -> list[str]:
    """
    List all stored image IDs.

    Returns:
        A list of image_id strings.
    """
    ids = list_images()
    logger.info(f"Listed {len(ids)} stored image(s).")
    return ids

@mcp.tool(
    name="upload_video",
    description="Upload a base64-encoded video to the server and receive a short video_id. Use this to store videos before passing them to other tools like object_detection.",
)
def upload_video(video_base64: str) -> str:
    """
    Upload a base64-encoded video and get back a short video_id.

    Args:
        video_base64: The video as a base64 string (data-URL prefix is stripped automatically).

    Returns:
        A short video_id string that can be passed to other tools.
    """
    video_id = store_video(video_base64)
    logger.info(f"Video uploaded with id: {video_id}")
    return video_id


@mcp.tool(
    name="list_uploaded_videos",
    description="List all video IDs currently stored on the server.",
)
def list_uploaded_videos() -> list[str]:
    """
    List all stored video IDs.

    Returns:
        A list of video_id strings.
    """
    ids = list_videos()
    logger.info(f"Listed {len(ids)} stored video(s).")
    return ids


@ mcp.tool(
    name="fake_object_detection",
    description="Perform fake object detection on a previously uploaded image or video for testing purposes. Pass the media_id returned by upload_image or upload_video. Returns the annotated media with bounding boxes and a list of randomly generated detected objects.",
)
def fake_object_detection(media_id: str):
    """
    Run fake object detection on a previously uploaded image or video for testing purposes.
    
    Args:
        media_id: The ID returned by the upload_image or upload_video tool.
    
    Returns:
        The annotated media with bounding boxes and detection metadata.
    """
    mcp_result, detections = fake_detect_objects(media_id)
    logger.info(f"Fake object detection completed: {len(detections)} object(s) found.")

    return [mcp_result, {"detections": detections}]


@mcp.tool(
    name="object_detection",
    description="Perform object detection on a previously uploaded image or video. Pass the media_id returned by upload_image or upload_video. Returns the annotated media with bounding boxes and a list of detected objects.",
)
async def object_detection(media_id: str):
    """
    Run object detection on a previously uploaded image or video by calling an external API.
    
    Args:
        media_id: The ID returned by the upload_image or upload_video tool.
    
    Returns:
        The annotated media with bounding boxes and detection metadata.
    """
    from tools.object_detection import detect_objects_with_external_api
    result = await detect_objects_with_external_api(media_id)
    return result


import os

if __name__ == "__main__":
    # Start MCP server
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
