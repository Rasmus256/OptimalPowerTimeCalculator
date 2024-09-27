from fastapi import FastAPI
import asyncio
import requests
from datetime import datetime, timedelta, date
import json

today = date.today()

app = FastAPI()

class EnergyPrice:
    def __init__(self, fromTs, toTs, price):
        self.fromTs = datetime.fromisoformat(fromTs)
        self.toTs = datetime.fromisoformat(toTs) #self.fromTs + timedelta(hours=1) - timedelta(seconds=1)
        self.price = price

@app.get("/api/next-optimal-hour")
async def get_days_until_out_of_mainframe():
    today = date.today()
    tomorrow = today + timedelta(day=1)    

    todaysprices= getprices(today)
    tomorrowsprices= getprices(tomorrow)
    FuturePrices = [].extend(todaysprices).extend(tomorrowsprices)

    return {'price' :min(FuturePrices, key=lambda r:r.price)}

def getprices(dateToFind):
    url = f'https://www.elprisenligenu.dk/api/v1/prices/{dateToFind.year}/{dateToFind.month:02d}-{dateToFind.day:02d}_DK1.json'
    string_json = requests.get(url)
    if(string_json.status_code == 200):
        contents = json.loads(string_json.content)
        return [EnergyPrice(e['time_start'],e['time_end'],e['DKK_per_kWh']) for e in contents]
    return []

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
