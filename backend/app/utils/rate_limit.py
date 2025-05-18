import redis
from fastapi import Request, HTTPException

r = redis.Redis(host="localhost", port=6379, db=0)

async def rate_limiter(request: Request):
    ip = request.client.host
    key = f"rl:{ip}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 60)
    elif count > 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
