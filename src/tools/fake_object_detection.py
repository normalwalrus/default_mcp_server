"""
Fake object detection tool for testing purposes.

This tool randomly adds labels to images or videos to simulate object detection
results without calling an external endpoint. This is useful for testing the
agent and tool calling functionality.
"""

import logging
import random
import time
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage, ImageDraw, ImageFont
from fastmcp.utilities.types import Image  # MCP Image type

from tools.image_store import get_image
from tools.video_store import get_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)

logger = logging.getLogger("mcp-fake-object-detection")

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


def fake_detect_objects(
    media_input,
    num_boxes: int = 3
) -> tuple:
    """
    Randomly add labels to a stored image or video for testing purposes.

    Parameters
    ----------
    media_input : str or bytes
        Either the ID of a previously uploaded image/video (from the image/video store) or media bytes.
    num_boxes : int, optional
        Number of random bounding boxes to draw (default 3).

    Returns
    -------
    tuple
        - For images: (MCP Image with bounding boxes, list of detection dicts)
        - For videos: (Processed video bytes, list of detection dicts)

    Raises
    ------
    ValueError
        If the ``media_input`` is not found in the store or invalid input is provided.
    """
    if isinstance(media_input, str):
        # Handle the case where media_id is passed
        # First try to get it from the image store
        media_bytes = get_image(media_input)
        media_type = "image"
        
        if media_bytes is None:
            # If not found in image store, try video store
            media_bytes = get_video(media_input)
            media_type = "video"
        
        if media_bytes is None:
            raise ValueError(f"Media with id '{media_input}' not found in the stores. Upload it first using the upload_image or upload_video tool.")
        
        media_id = media_input
        
        if media_type == "image":
            pil_image = PILImage.open(BytesIO(media_bytes)).convert("RGB")
        else:  # video
            # For video processing in the fake tool, return placeholder detections
            logger.info("Processing video file (fake detection)...")
            
            # Generate random detections for video
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
            # Return a placeholder image for the video case in the fake tool
            # Create a simple placeholder image
            placeholder_img = PILImage.new('RGB', (640, 480), color=(73, 109, 137))
            buffer = BytesIO()
            placeholder_img.save(buffer, format="JPEG", quality=85)
            annotated_bytes = buffer.getvalue()
            mcp_image = Image(data=annotated_bytes, format="jpeg")
            return mcp_image, detections
    elif isinstance(media_input, bytes):
        # Handle the case where media bytes are passed directly
        # Try to open as image first, if that fails, treat as video
        try:
            pil_image = PILImage.open(BytesIO(media_input)).convert("RGB")
            media_id = f"bytes_{int(time.time() * 1000)}"
            media_type = "image"
        except Exception:
            # If opening as image fails, treat as video
            logger.info("Processing video bytes (fake detection)...")
            
            # Generate random detections for video
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
            # Return a placeholder image for the video case in the fake tool
            # Create a simple placeholder image
            placeholder_img = PILImage.new('RGB', (640, 480), color=(73, 109, 137))
            buffer = BytesIO()
            placeholder_img.save(buffer, format="JPEG", quality=85)
            annotated_bytes = buffer.getvalue()
            mcp_image = Image(data=annotated_bytes, format="jpeg")
            return mcp_image, detections
    else:
        raise ValueError("Input must be either a media_id string or media bytes")
    
    if media_type == "image":
        logger.info(
            "Running (fake) object detection on image %s (%dx%d) …",
            media_id,
            pil_image.width,
            pil_image.height,
        )

        # Save the received (original) image for verification
        timestamp = int(time.time() * 1000)
        original_path = _SAVE_DIR / f"{timestamp}_{media_id}_original.jpg"
        pil_image.save(original_path, format="JPEG", quality=90)
        logger.info("Saved received image to %s", original_path)

        annotated_image, detections = _draw_random_detections(pil_image, num_boxes)

        logger.info("Generated %d random detection(s).", len(detections))

        # Save the annotated image for verification
        annotated_path = _SAVE_DIR / f"{timestamp}_{media_id}_annotated.jpg"
        annotated_image.save(annotated_path, format="JPEG", quality=90)
        logger.info("Saved annotated image to %s", annotated_path)

        # Encode the annotated image as JPEG bytes for MCP transport
        buffer = BytesIO()
        annotated_image.save(buffer, format="JPEG", quality=85)
        annotated_bytes = buffer.getvalue()

        mcp_image = Image(data=annotated_bytes, format="jpeg")

        return mcp_image, detections
    
    # This should not be reached due to early returns in video cases,
    # but included for completeness
    raise ValueError(f"Unsupported media type: {media_type}")