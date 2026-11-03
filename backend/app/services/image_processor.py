from io import BytesIO

from PIL import Image, UnidentifiedImageError


def validate_photo(data: bytes, max_bytes: int) -> tuple[int, int]:
    if len(data) > max_bytes:
        raise ValueError("Candidate photograph exceeds the configured file-size limit.")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError("Candidate photograph dimensions exceed the supported limit.")
            return image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Candidate photograph is not a supported image.") from exc
