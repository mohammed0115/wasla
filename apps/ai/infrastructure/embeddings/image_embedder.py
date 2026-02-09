from __future__ import annotations

from django.core.files.storage import default_storage

from apps.ai.domain.policies import validate_image_upload
from apps.ai.infrastructure.providers.registry import get_provider


class ImageEmbedder:
    @staticmethod
    def embed_uploaded(image_file) -> list[float]:
        validate_image_upload(image_file)
        image_bytes = image_file.read()
        provider = get_provider()
        result = provider.embed_image(image_bytes=image_bytes)
        return result.vector

    @staticmethod
    def embed_image_path(path: str) -> list[float]:
        with default_storage.open(path, "rb") as handle:
            image_bytes = handle.read()
        provider = get_provider()
        result = provider.embed_image(image_bytes=image_bytes)
        return result.vector
