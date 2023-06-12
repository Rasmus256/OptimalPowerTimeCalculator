from fastapi import FastAPI
import numpy as np
import asyncio
from datetime import date

app = FastAPI()

@app.get("/api/udafmainframe")
async def get_days_until_out_of_mainframe():
    start = date.today()
    end = date(2040, 7, 24)

    days = int(np.busday_count(start, end))
    return {'days' :days}

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
