"""
Object detection tool (stub).

Accepts an image_id (from the image store) or image/video bytes, draws random bounding boxes with
labels, and returns the processed file with annotations and detection metadata.
"""

import logging
import random
import time
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage, ImageDraw, ImageFont
from fastmcp.utilities.types import Image  # MCP Image type

from tools.image_store import get_image
import httpx
import os
import base64

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)

logger = logging.getLogger("mcp-object-detection")

# Directory where received and annotated images are saved for verification
_SAVE_DIR = Path("saved_images")
_SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Fake class labels used for the random detections
_FAKE_CLASSES = [
    "person", "car", "truck", "bicycle", "dog", "cat",
    "bird", "boat", "airplane", "tree", "building", "bus",
]

# Colours for bounding boxes (one per box, cycled)
_BOX_COLOURS = ["red", "lime", "blue", "yellow", "cyan", "magenta", "orange"]


def _draw_random_detections(
    image: PILImage.Image,
    num_boxes: int = 3,
) -> tuple[PILImage.Image, list[dict]]:
    """
    Draw *num_boxes* random bounding boxes on *image* and return the
    annotated image together with fake detection metadata.
    """
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)

    # Try to use a nicer font; fall back to the default bitmap font.
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except (IOError, OSError):
        font = ImageFont.load_default()

    w, h = image.size
    detections: list[dict] = []

    for i in range(num_boxes):
        # Generate a random box that is at least 10 % of the image in each dim
        min_side_w = max(int(w * 0.10), 20)
        min_side_h = max(int(h * 0.10), 20)

        x1 = random.randint(0, max(w - min_side_w - 1, 0))
        y1 = random.randint(0, max(h - min_side_h - 1, 0))
        x2 = random.randint(x1 + min_side_w, min(x1 + int(w * 0.5), w))
        y2 = random.randint(y1 + min_side_h, min(y1 + int(h * 0.5), h))

        class_name = random.choice(_FAKE_CLASSES)
        confidence = round(random.uniform(0.50, 0.99), 2)
        colour = _BOX_COLOURS[i % len(_BOX_COLOURS)]

        label = f"{class_name} {confidence:.2f}"

        # Draw bounding box
        draw.rectangle([x1, y1, x2, y2], outline=colour, width=3)

        # Draw label background + text
        text_bbox = draw.textbbox((x1, y1), label, font=font)
        draw.rectangle(
            [text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 2, text_bbox[3] + 2],
            fill=colour,
        )
        draw.text((x1, y1), label, fill="white", font=font)

        detections.append(
            {
                "class": class_name,
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2],
            }
        )

    return annotated, detections


def detect_objects_in_image(
    image_input,
    num_boxes: int = 3,
    is_video: bool = False
) -> tuple:
    """
    Draw random bounding boxes on a stored image or image/video bytes (stub for real object
    detection).

    Parameters
    ----------
    image_input : str or bytes
        Either the ID of a previously uploaded image (from the image store) or image/video bytes.
    num_boxes : int, optional
        Number of random bounding boxes to draw (default 3).
    is_video : bool, optional
        Whether the input is a video file (default False).

    Returns
    -------
    tuple
        - For images: (MCP Image with bounding boxes, list of detection dicts)
        - For videos: (Processed video bytes, list of detection dicts)

    Raises
    ------
    ValueError
        If the ``image_id`` is not found in the store or invalid input is provided.
    """
    if isinstance(image_input, str):
        # Handle the legacy case where image_id is passed
        image_bytes = get_image(image_input)
        if image_bytes is None:
            raise ValueError(f"Image with id '{image_input}' not found in the store. Upload it first using the upload_image tool.")
        
        pil_image = PILImage.open(BytesIO(image_bytes)).convert("RGB")
        image_id = image_input
    elif isinstance(image_input, bytes):
        # Handle the new case where image/video bytes are passed directly
        if is_video:
            # For video processing, we would typically process frame by frame
            # For this stub, we'll just return the original bytes with placeholder detections
            # In a real implementation, you'd use a video processing library like OpenCV
            logger.info("Processing video file...")
            
            # Placeholder for video processing
            # In a real implementation, you would:
            # 1. Extract frames from the video
            # 2. Process each frame with object detection
            # 3. Reconstruct the video with annotations
            
            # For now, return the original video bytes with fake detections
            detections = []
            for i in range(num_boxes):
                class_name = random.choice(_FAKE_CLASSES)
                confidence = round(random.uniform(0.50, 0.99), 2)
                
                detections.append({
                    "frame": i,
                    "class": class_name,
                    "confidence": confidence,
                    "bbox": [random.randint(0, 100), random.randint(0, 100), 
                             random.randint(100, 200), random.randint(100, 200)],
                })
            
            logger.info(f"Generated {len(detections)} random detection(s) for video.")
            return image_input, detections
        else:
            # Handle image bytes directly
            pil_image = PILImage.open(BytesIO(image_input)).convert("RGB")
            image_id = f"bytes_{int(time.time() * 1000)}"
    else:
        raise ValueError("Input must be either an image_id string or image/video bytes")
    
    if not is_video:
        logger.info(
            "Running (stub) object detection on image %s (%dx%d) …",
            image_id,
            pil_image.width,
            pil_image.height,
        )

        # Save the received (original) image for verification
        timestamp = int(time.time() * 1000)
        original_path = _SAVE_DIR / f"{timestamp}_{image_id}_original.jpg"
        pil_image.save(original_path, format="JPEG", quality=90)
        logger.info("Saved received image to %s", original_path)

        annotated_image, detections = _draw_random_detections(pil_image, num_boxes)

        logger.info("Generated %d random detection(s).", len(detections))

        # Save the annotated image for verification
        annotated_path = _SAVE_DIR / f"{timestamp}_{image_id}_annotated.jpg"
        annotated_image.save(annotated_path, format="JPEG", quality=90)
        logger.info("Saved annotated image to %s", annotated_path)

        # Encode the annotated image as JPEG bytes for MCP transport
        buffer = BytesIO()
        annotated_image.save(buffer, format="JPEG", quality=85)
        annotated_bytes = buffer.getvalue()

        mcp_image = Image(data=annotated_bytes, format="jpeg")

        return mcp_image, detections
    
    # This return is just to satisfy the linter, as video case is handled earlier
    return None, []


async def detect_objects_with_external_api(image_id: str):
    """
    Call an external API to perform object detection on an image.

    Args:
        image_id: The ID of the image to process.

    Returns:
        The annotated image with bounding boxes and detection metadata from the external API.
    """
    import httpx
    import os
    from io import BytesIO
    from fastmcp.utilities.types import Image  # MCP Image type
    from tools.image_store import get_image
    
    # Get the image data from the image store
    image_bytes = get_image(image_id)
    if image_bytes is None:
        raise ValueError(f"Image with id '{image_id}' not found in the store. Upload it first using the upload_image tool.")
    
    # Get the external API URL from environment variables, with a default fallback
    external_api_url = os.getenv("EXTERNAL_OBJECT_DETECTION_API_URL", "http://localhost:8001/detect")
    
    # Prepare the file for upload
    files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
    
    # Make the async request to the external API
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(external_api_url, files=files)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Parse the response - assuming the API returns JSON with image data and detections
            result = response.json()
            
            # Extract the annotated image and detections from the response
            # This assumes the external API returns a structure like:
            # {
            #   "annotated_image": <base64_encoded_image>,
            #   "detections": [...]
            # }
            
            if "annotated_image" in result:
                # If the API returns a base64 encoded image
                import base64
                annotated_image_data = base64.b64decode(result["annotated_image"])
            elif "image_bytes" in result:
                # If the API returns raw bytes
                annotated_image_data = result["image_bytes"]
            else:
                # If the API returns the image in a different format, adjust accordingly
                raise ValueError("External API did not return image data in expected format")
            
            detections = result.get("detections", [])
            
            # Create an MCP Image object from the annotated image data
            mcp_image = Image(data=annotated_image_data, format="jpeg")
            
            logger.info(f"Object detection completed via external API: {len(detections)} object(s) found.")
            
            return [mcp_image, {"detections": detections}]
        
        except httpx.RequestError as e:
            logger.error(f"Error connecting to external object detection API: {str(e)}")
            raise ValueError(f"Could not connect to external object detection API: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"External API returned error status {e.response.status_code}: {str(e)}")
            raise ValueError(f"External API error: {e.response.status_code} - {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during object detection: {str(e)}")
            raise ValueError(f"Object detection failed: {str(e)}")

