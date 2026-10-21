
from functools import lru_cache
from uuid import uuid4

from supabase import Client, create_client

from app.core.config import settings


class SupabaseStorageClient:
    """Handle file uploads and deletions in Supabase Storage."""

    def __init__(self, client: Client, bucket_name: str = "product-images") -> None:
        self.client = client
        self.bucket_name = bucket_name

    def upload(
        self,
        *,
        product_id: int,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> tuple[str, str]:
        """Upload an image and return (storage_key, public_url)."""
        extension = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }[content_type]

        storage_key = f"products/{product_id}/{uuid4().hex}.{extension}"

        self.client.storage.from_(self.bucket_name).upload(
            path=storage_key,
            file=content,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )

        public_url = (
            self.client.storage.from_(self.bucket_name)
            .get_public_url(storage_key)
        )

        return storage_key, str(public_url)

    def delete(self, storage_key: str) -> None:
        """Delete an image from Supabase Storage."""
        self.client.storage.from_(self.bucket_name).remove([storage_key])


@lru_cache(maxsize=1)
def get_storage_client() -> SupabaseStorageClient:
    """Create and reuse one configured storage client."""
    supabase = create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )
    return SupabaseStorageClient(supabase)
