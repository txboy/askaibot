import glob
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import config

router = APIRouter(tags=["brand"])

DEFAULT_EXTS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}


def logo_path() -> str | None:
    os.makedirs(config.upload_dir, exist_ok=True)
    matches = glob.glob(os.path.join(config.upload_dir, "brand_logo.*"))
    return matches[0] if matches else None


@router.get("/logo/status")
def logo_status():
    return {"has_logo": logo_path() is not None}


@router.get("/logo")
def get_logo():
    path = logo_path()
    if not path:
        raise HTTPException(status_code=404, detail="暂无自定义logo")
    ext = os.path.splitext(path)[1].lower()
    return FileResponse(
        path, media_type=DEFAULT_EXTS.get(ext, "application/octet-stream")
    )
