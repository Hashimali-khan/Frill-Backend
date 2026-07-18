import uuid

from supabase import Client, create_client

from app.config import settings
from app.core.exceptions import ValidationAppError

_supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


async def upload_file(bucket: str, file_bytes: bytes, content_type: str, extension: str) -> str:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationAppError(f"Unsupported file type: {content_type}")
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValidationAppError("File too large (max 10MB)")

    path = f"{uuid.uuid4()}.{extension}"
    _supabase.storage.from_(bucket).upload(path, file_bytes, {"content-type": content_type})
    return _supabase.storage.from_(bucket).get_public_url(path)