from fastapi import Header, HTTPException
from app.config import API_KEY

async def check_api_key(authorization: str = Header(None)):
    # print(API_KEY)
    # if authorization != f"Bearer {API_KEY}":
    #     raise HTTPException(status_code=401, detail="Invalid API Key")
    return True
