import base64
import io
from io import BytesIO

import pytesseract
from PIL import Image, ImageDraw


def remove_text_from_image(image: Image.Image, padding: int = 5) -> Image.Image:
    """
    Remove text from image by filling text regions with white.
    Uses aggressive padding to ensure complete text removal.

    Args:
        image: PIL Image object
        padding: Extra pixels around text boxes to ensure complete removal

    Returns:
        Image with text removed
    """
    # Create a copy to avoid modifying original
    img_copy = image.copy()

    # Get text bounding boxes from OCR with more detailed output
    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT,
        config="--psm 11",  # Sparse text detection
    )

    # Create drawing context
    draw = ImageDraw.Draw(img_copy)

    # Get background color (use white)
    bg_color = 255 if img_copy.mode == "L" else (255, 255, 255)

    # Iterate through detected text boxes
    n_boxes = len(data["text"])
    for i in range(n_boxes):
        # Process if confidence is above -1 (detected) and text exists
        conf = int(data["conf"][i]) if data["conf"][i] != "" else -1
        if conf >= -1 and data["text"][i].strip():
            # Get bounding box coordinates with padding
            x = max(0, data["left"][i] - padding)
            y = max(0, data["top"][i] - padding)
            w = data["width"][i] + (padding * 2)
            h = data["height"][i] + (padding * 2)

            # Fill the text area with background color (white)
            draw.rectangle([x, y, x + w, y + h], fill=bg_color, outline=bg_color)

    return img_copy


def process_image(image: Image.Image, max_size: int = 600, quality: int = 40) -> str:
    """
    Process and compress image for database storage.
    Converts to grayscale and applies aggressive compression.

    Args:
        image: PIL Image object
        max_size: Maximum dimension (width/height)
        quality: JPEG quality (1-100, lower = smaller file)

    Returns:
        Base64 encoded image string
    """
    # Convert to grayscale (reduces size by ~66%)
    if image.mode != "L":
        image = image.convert("L")

    # Resize to reduce dimensions
    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # Compress as JPEG with lower quality
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=quality, optimize=True)

    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def should_skip_image(
    image: Image.Image, min_width: int = 100, min_height: int = 100
) -> bool:
    """Check if image should be skipped based on criteria."""
    # Skip images with transparency (likely icons/emojis)
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        return True

    # Skip very small images
    if image.width < min_width or image.height < min_height:
        return True

    return False
