"""Project directory routes."""

import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ProjectPathRequest(BaseModel):
    path: str


def _directory_payload(path: Path) -> dict:
    resolved = path.expanduser().resolve()
    return {
        "path": str(resolved),
        "name": resolved.name or str(resolved),
    }


@router.get("/projects/current")
async def get_current_project():
    return _directory_payload(Path(os.getcwd()))


@router.post("/projects/choose")
async def choose_project():
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'POSIX path of (choose folder with prompt "选择 Agent Hub 项目文件夹")',
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except FileNotFoundError:
        result = None
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=400, detail="选择文件夹超时") from exc

    if result and result.returncode == 0:
        return _directory_payload(Path(result.stdout.strip()))
    if result and result.returncode != 0:
        raise HTTPException(status_code=400, detail="已取消选择文件夹")

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="选择 Agent Hub 项目文件夹")
        root.destroy()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="当前环境无法打开文件夹选择器") from exc

    if not path:
        raise HTTPException(status_code=400, detail="已取消选择文件夹")
    return _directory_payload(Path(path))


@router.post("/projects/validate")
async def validate_project(payload: ProjectPathRequest):
    raw_path = payload.path.strip()
    if not raw_path:
        raise HTTPException(status_code=400, detail="项目目录不能为空")

    path = Path(raw_path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=400, detail="项目目录不存在")
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="请选择一个文件夹")

    return _directory_payload(path)
