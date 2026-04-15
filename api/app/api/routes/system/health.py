from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", summary="健康检查")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
