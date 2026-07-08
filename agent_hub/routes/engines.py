"""/api/engines 路由"""

from fastapi import APIRouter

from ..detector import detect_all

router = APIRouter()


@router.get("/engines")
async def list_engines():
    engines = detect_all()
    return {
        "engines": [
            {
                "name": e.name,
                "display_name": e.display_name,
                "vendor": e.vendor,
                "installed": e.installed,
                "executable": e.executable,
                "version": e.version,
                "config_dir": e.config_dir,
                "models": e.models,
                "error": e.error,
            }
            for e in engines
        ]
    }


@router.get("/engines/{name}/models")
async def engine_models(name: str):
    from ..detector import detect_one
    engine = detect_one(name)
    if not engine:
        return {"error": "引擎不存在"}, 404
    return {"name": name, "models": engine.models}
