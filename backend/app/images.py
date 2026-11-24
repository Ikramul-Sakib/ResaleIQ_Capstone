"""Safe handling of uploaded product photos.

Every upload is opened with Pillow, so only real JPG/PNG/WebP images are accepted.
Photos are rotated upright, shrunk to at most 1600 px and re-saved as JPEG with a
random name, which also strips hidden metadata such as GPS location.
"""

import io
import logging
import os
import uuid

from flask import current_app
from PIL import Image, ImageOps

from .errors import ApiError

log = logging.getLogger(__name__)

Image.MAX_IMAGE_PIXELS = 50_000_000  # refuse "decompression bomb" images
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}  # MPO = JPEG from some phone cameras
MAX_SIDE = 1600


def save_image(file_storage) -> str:
    name = file_storage.filename or "photo"
    data = file_storage.read()
    if not data:
        raise ApiError(f"{name} is empty.", 422, {"images": f"{name} is empty."})
    if len(data) > current_app.config["MAX_IMAGE_BYTES"]:
        raise ApiError("Each photo must be 8 MB or smaller.", 413, {"images": f"{name} is larger than 8 MB."})

    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        image = Image.open(io.BytesIO(data))
        if image.format not in ALLOWED_FORMATS:
            raise ValueError(image.format)
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.getchannel("A"))
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((MAX_SIDE, MAX_SIDE))
    except ApiError:
        raise
    except Exception:  # Pillow raises many different error types for bad files
        message = f"{name} is not a valid JPG, PNG or WebP image."
        raise ApiError(message, 422, {"images": message})

    filename = f"{uuid.uuid4().hex}.jpg"
    image.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename), "JPEG", quality=85, optimize=True)
    return filename


def delete_image_files(filenames) -> None:
    folder = current_app.config["UPLOAD_FOLDER"]
    for filename in filenames:
        try:
            os.remove(os.path.join(folder, filename))
        except FileNotFoundError:
            pass
        except OSError:
            log.warning("Could not delete image %s", filename)
