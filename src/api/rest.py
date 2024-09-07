from fastapi import FastAPI
import asyncio
import requests
from datetime import datetime, timedelta
import json

app = FastAPI()

class EnergyPrice:
    def __init__(self, fromTs, price):
        self.fromTs = datetime.fromtimestamp(fromTs)
        self.toTs = self.fromTs + timedelta(hours=1) - timedelta(seconds=1)
        self.price = price

FuturePrices = [
    EnergyPrice(1725069600, 10.0),
    EnergyPrice(1725073200, 3.0),
    EnergyPrice(1725076800, 4.0)
    ]

@app.get("/api/next-optimal-hour")
async def get_days_until_out_of_mainframe():
    global FuturePrices
    url = 'https://api.energy-charts.info/price?bzn=DK1'
    response = requests.get(url)
    contents = json.loads(response.content)
    ts = contents["unix_seconds"]
    prices = contents["price"]
    FuturePrices = [EnergyPrice(e,f) for e,f in zip(ts,prices)]
    result = min(FuturePrices, key=lambda r:r['price'])
    return {'price' :result}

@app.get("/healthz", status_code=204)
def healthcheck():
    return None