"""Local file preview routes."""

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter()

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


@router.get("/files/preview")
async def preview_file(path: str = Query(..., min_length=1)):
    file_path = Path(unquote(path)).expanduser()
    try:
        resolved = file_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=404, detail="文件不存在") from exc

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    if resolved.suffix.lower() not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="暂不支持预览该文件类型")

    return FileResponse(str(resolved))
