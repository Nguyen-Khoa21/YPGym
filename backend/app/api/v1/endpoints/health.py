from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "success",
        "message": "YPGym API is running",
        "version": "0.1.0",
    }
