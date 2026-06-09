"""Artifact storage. Phase 1 stubs the pre-signed URL (real S3/R2 wiring deferred).

The renderer already writes the xlsx to disk during drafting; persisting it to
object storage and returning a real signed URL is out of scope for Phase 1.
"""

from __future__ import annotations

from obelisk_api.config import get_settings


def presigned_artifact_url(block_id: str, kind: str, version: int = 1) -> str:
    """Return a (stubbed) pre-signed URL for the latest artifact of a kind."""
    settings = get_settings()
    endpoint = settings.obelisk_s3_endpoint or f"https://{settings.obelisk_s3_bucket}.example"
    return f"{endpoint}/{block_id}/{kind}/v{version}?stub=1"
