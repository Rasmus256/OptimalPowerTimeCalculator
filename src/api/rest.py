from fastapi import FastAPI
import asyncio
import requests
from datetime import datetime, timedelta, date
import json

today = date.today()

app = FastAPI()

class EnergyPrice:
    def __init__(self, fromTs, price):
        self.fromTs = datetime.fromtimestamp(fromTs)
        self.toTs = self.fromTs + timedelta(hours=1) - timedelta(seconds=1)
        self.price = price

@app.get("/api/next-optimal-hour")
async def get_days_until_out_of_mainframe():
    today = date.today()
    
    url = f'https://www.elprisenligenu.dk/api/v1/prices/{today.year}/{today.month}-{today.day}_DK1.json'
    print(url)
    string_json = requests.get(url).content
    print(string_json)
    contents = json.loads(string_json)
    FuturePrices = [EnergyPrice(e['time_start'],e['DKK_per_kWh']) for e in contents]
    return {'price' :min(FuturePrices, key=lambda r:r.price)}

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
