from fastmcp import FastMCP
from tools.object_detection import detect_objects_in_image
from tools.image_store import store_image, list_images
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
    name="fake_object_detection",
    description="Perform object detection on a previously uploaded image. Pass the image_id returned by upload_image. Returns the annotated image with bounding boxes and a list of detected objects.",
)
def fake_object_detection(image_id: str):
    """
    Run object detection on a previously uploaded image.

    Args:
        image_id: The ID returned by the upload_image tool.
        num_boxes: Number of objects to detect (default 3).

    Returns:
        The annotated image with bounding boxes and detection metadata.
    """
    mcp_image, detections = detect_objects_in_image(image_id)
    logger.info(f"Object detection completed: {len(detections)} object(s) found.")

    return [mcp_image, {"detections": detections}]


@mcp.tool(
    name="object_detection",
    description="Perform object detection on a previously uploaded image. Pass the image_id returned by upload_image. Returns the annotated image with bounding boxes and a list of detected objects.",
)
async def object_detection(image_id: str):
    """
    Run object detection on a previously uploaded image by calling an external API.

    Args:
        image_id: The ID returned by the upload_image tool.

    Returns:
        The annotated image with bounding boxes and detection metadata.
    """
    from tools.object_detection import detect_objects_with_external_api
    result = await detect_objects_with_external_api(image_id)
    return result


import os

if __name__ == "__main__":
    # Start MCP server
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
