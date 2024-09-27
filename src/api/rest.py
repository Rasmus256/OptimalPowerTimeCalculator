from fastapi import FastAPI
import asyncio
import requests
from datetime import datetime, timedelta, date
import json
import pytz

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
    tomorrow = today + timedelta(days=1)    

    todaysprices= getprices(today)
    tomorrowsprices= getprices(tomorrow)
    FuturePrices = []
    FuturePrices.extend(todaysprices)
    FuturePrices.extend(tomorrowsprices)
    numHoursToForecast = 2
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
    return {'price' : {'fromTs': startTs, 'toTs': endTs, 'price': min_sum/2}}

def getprices(dateToFind):
    url = f'https://www.elprisenligenu.dk/api/v1/prices/{dateToFind.year}/{dateToFind.month:02d}-{dateToFind.day:02d}_DK1.json'
    string_json = requests.get(url)
    if(string_json.status_code == 200):
        contents = json.loads(string_json.content)
        possibleDates = [EnergyPrice(e['time_start'],e['time_end'],e['DKK_per_kWh']) for e in contents]
        utc=pytz.UTC
        print(possibleDates)
        return [e for e in possibleDates if e.toTs >= utc.localize(datetime.now())]
    return []

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
