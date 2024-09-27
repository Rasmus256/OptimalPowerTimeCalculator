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

@app.get("/api/next-optimal-hour")
async def get_days_until_out_of_mainframe():
    url = 'https://api.energy-charts.info/price?bzn=DK1'
    string_json = requests.get(url).content
    print(string_json)
    contents = json.loads(string_json)
    FuturePrices = [EnergyPrice(e,f) for e,f in zip(contents["unix_seconds"],contents["price"])]
    return {'price' :min(FuturePrices, key=lambda r:r['price'])}

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
