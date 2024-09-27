from fastapi import FastAPI
import asyncio
import requests
from datetime import datetime, timedelta, date
import json
import pytz

today = date.today()

app = FastAPI()

cachedPrices = {}

class EnergyPrice:
    def __init__(self, fromTs, toTs, price):
        self.fromTs = datetime.fromisoformat(fromTs)
        self.toTs = datetime.fromisoformat(toTs) #self.fromTs + timedelta(hours=1) - timedelta(seconds=1)
        self.price = price

@app.get("/api/next-optimal-hour")
async def get_days_until_out_of_mainframe(numHoursToForecast = 2):
    global cachedPrices
    numHoursToForecast = int(numHoursToForecast)
    today = date.today()
    tomorrow = today + timedelta(days=1)    
    if not today.strftime('%m/%d/%Y') in cachedPrices:
      cachedPrices[today.strftime('%m/%d/%Y')]= getprices(today)
    if not tomorrow.strftime('%m/%d/%Y') in cachedPrices:
      cachedPrices[tomorrow.strftime('%m/%d/%Y')]= getprices(tomorrow)

    FuturePrices = []
    FuturePrices.extend(cachedPrices[today.strftime('%m/%d/%Y')])
    FuturePrices.extend(cachedPrices[tomorrow.strftime('%m/%d/%Y')])
    utc=pytz.UTC
    FuturePrices = [e for e in FuturePrices if e.toTs >= utc.localize(datetime.now())]

    startTs = 0
    endTs = 0
    min_sum = float('inf')
    for i in range(len(FuturePrices)-(numHoursToForecast-1)):
        window_sum = 0
        for j in range(numHoursToForecast):
            window_sum += FuturePrices[i+j].price
        if window_sum < min_sum:
            min_sum = window_sum
            startTs = FuturePrices[i].fromTs
            endTs = FuturePrices[i+numHoursToForecast-1].toTs
    return {'price' : {'fromTs': startTs, 'toTs': endTs, 'price': min_sum/numHoursToForecast}}

def getprices(dateToFind):
    url = f'https://www.elprisenligenu.dk/api/v1/prices/{dateToFind.year}/{dateToFind.month:02d}-{dateToFind.day:02d}_DK1.json'
    string_json = requests.get(url)
    if(string_json.status_code == 200):
        contents = json.loads(string_json.content)
        possibleDates = [EnergyPrice(e['time_start'],e['time_end'],e['DKK_per_kWh']) for e in contents]
        return possibleDates
    return []

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
