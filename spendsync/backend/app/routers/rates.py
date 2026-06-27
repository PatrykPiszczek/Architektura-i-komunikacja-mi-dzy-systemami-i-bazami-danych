import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from .. import models
from ..config import settings
from ..deps import get_current_user

router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("")
async def get_rate(code: str = "EUR", user: models.User = Depends(get_current_user)):
    code = code.upper()
    if code == "PLN":
        return {"code": "PLN", "rate": 1.0, "source": "base"}

    url = f"{settings.nbp_base_url}/exchangerates/rates/A/{code}/?format=json"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url)
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Currency service unavailable")

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown currency code: {code}")
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Currency service error")

    data = response.json()
    quote = data["rates"][0]
    return {"code": code, "rate": quote["mid"], "date": quote["effectiveDate"], "source": "NBP"}
