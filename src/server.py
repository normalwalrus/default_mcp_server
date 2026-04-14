from fastmcp import FastMCP
from tools.object_detection import detect_objects_in_image
from tools.image_store import store_image, list_images
from tools.s3_tools import (
    upload_file_to_s3,
    upload_base64_image_to_s3,
    download_file_from_s3,
    download_image_from_s3_as_base64,
    delete_file_from_s3,
    list_s3_objects
)

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
    name="object_detection",
    description="Perform object detection on a previously uploaded image. Pass the image_id returned by upload_image. Returns the annotated image with bounding boxes and a list of detected objects.",
)
def object_detection(image_id: str, num_boxes: int = 3):
    """
    Run object detection on a previously uploaded image.

    Args:
        image_id: The ID returned by the upload_image tool.
        num_boxes: Number of objects to detect (default 3).

    Returns:
        The annotated image with bounding boxes and detection metadata.
    """
    mcp_image, detections = detect_objects_in_image(image_id, num_boxes)
    logger.info(f"Object detection completed: {len(detections)} object(s) found.")

    return [mcp_image, {"detections": detections}]


@mcp.tool(
    name="upload_file_to_s3",
    description="Upload a file to S3/MinIO storage. Takes file content and object name.",
)
def upload_file_to_s3_tool(file_content: str, object_name: str, content_type: str = None) -> str:
    """
    Upload a file to S3/MinIO storage.
    
    Args:
        file_content: Content of the file to upload
        object_name: Name to give the object in S3
        content_type: Optional content type (e.g., 'text/plain', 'application/json')
        
    Returns:
        Success message
    """
    result = upload_file_to_s3(file_content, object_name, content_type)
    logger.info(result)
    return result


@mcp.tool(
    name="upload_image_to_s3",
    description="Upload a base64-encoded image to S3/MinIO storage.",
)
def upload_image_to_s3_tool(base64_image: str, object_name: str) -> str:
    """
    Upload a base64-encoded image to S3/MinIO storage.
    
    Args:
        base64_image: Base64 encoded image string
        object_name: Name to give the image object in S3 (should include extension)
        
    Returns:
        Success message
    """
    result = upload_base64_image_to_s3(base64_image, object_name)
    logger.info(result)
    return result


@mcp.tool(
    name="download_file_from_s3",
    description="Download a file from S3/MinIO storage by object name.",
)
def download_file_from_s3_tool(object_name: str) -> str:
    """
    Download a file from S3/MinIO storage.
    
    Args:
        object_name: Name of the object in S3 to download
        
    Returns:
        Content of the downloaded file
    """
    content = download_file_from_s3(object_name)
    logger.info(f"Downloaded file {object_name} from S3")
    return content


@mcp.tool(
    name="download_image_from_s3",
    description="Download an image from S3/MinIO storage and return as base64 string.",
)
def download_image_from_s3_tool(object_name: str) -> str:
    """
    Download an image from S3/MinIO storage and return as base64 string.
    
    Args:
        object_name: Name of the image object in S3 to download
        
    Returns:
        Base64 encoded image string
    """
    base64_image = download_image_from_s3_as_base64(object_name)
    logger.info(f"Downloaded image {object_name} from S3 as base64")
    return base64_image


@mcp.tool(
    name="delete_file_from_s3",
    description="Delete a file from S3/MinIO storage by object name.",
)
def delete_file_from_s3_tool(object_name: str) -> str:
    """
    Delete a file from S3/MinIO storage.
    
    Args:
        object_name: Name of the object in S3 to delete
        
    Returns:
        Success message
    """
    result = delete_file_from_s3(object_name)
    logger.info(result)
    return result


@mcp.tool(
    name="list_s3_objects",
    description="List objects in S3/MinIO storage with optional prefix filtering.",
)
def list_s3_objects_tool(prefix: str = "") -> list[str]:
    """
    List objects in S3/MinIO storage.
    
    Args:
        prefix: Optional prefix to filter objects (default: "")
        
    Returns:
        List of object names
    """
    objects = list_s3_objects(prefix)
    logger.info(f"Listed {len(objects)} object(s) from S3 with prefix '{prefix}'")
    return objects


import os

if __name__ == "__main__":
    # Start MCP server
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
