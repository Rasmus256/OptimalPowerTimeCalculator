from fastapi import FastAPI
import numpy as np
import asyncio
import datetime

app = FastAPI()

@app.get("/api/udafmainframe")
async def get_reachable_nodes():
    start = datetime.now()
    end = datetime.date(2022, 4, 16)

    days = np.busday_count(start, end)
    return days

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
