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
async def get_days_until_out_of_mainframe(numHoursToForecast = '2h35m'):
    global cachedPrices
    hoursString = numHoursToForecast.split('h')[0]
    minuteString = numHoursToForecast.split('h')[1].split('m')[0]
    numHoursInt = int(hoursString)
    numMinutesInt = int(minuteString)
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

    hoursToForecastInclPartial = numHoursInt
    if numMinutesInt > 0:
        hoursToForecastInclPartial+=1
    
    startIdx = 0
    endIdx = 0
    min_sum = float('inf')
    for i in range(len(FuturePrices)-(numHoursToForecast-1)):
        window_sum = 0
        for j in range(numHoursToForecast):
            window_sum += FuturePrices[i+j].price
        if window_sum < min_sum:
            min_sum = window_sum
            startTs = i
            endTs = i+numHoursToForecast-1
    #Were we asked to forecast a partial hour? If so, either attach this partial hour to the beginning or the end - depending on price.
    price = 0
    if numMinutesInt>0:
        firstHourPrice = FuturePrices[startIdx].price
        lastHourPrice = FuturePrices[endIdx].price
        if firstHourPrice < lastHourPrice:
            startTs = FuturePrices[startIdx].fromTs
            endTs = FuturePrices[endIdx-1].toTs + timedelta(minutes=numMinutesInt)
            print(f'looping from {startIdx} to {endIdx}')
            for i in range(startIdx, endIdx-1):
                print(i)
                min_sum += FuturePrices[i].price * 60
            min_sum += FuturePrices[endIdx-1].price*numMinutesInt
            price = min_sum / (numHoursInt*60 + numMinutesInt)
        else:
            startTs = FuturePrices[startIdx].fromTs +  timedelta(minutes=60-numMinutesInt)
            endTs = FuturePrices[endIdx].toTs
            print(f'looping from {startIdx} to {endIdx}')
            for i in range(startIdx+1, endIdx):
                print(i)
                min_sum += FuturePrices[i].price * 60
            min_sum += FuturePrices[endIdx-1].price*(numMinutesInt)
            price = min_sum / (numHoursInt*60 + numMinutesInt)
    else:
        startTs = FuturePrices[startIdx].fromTs
        endTs = FuturePrices[endIdx].toTs
        price = min_sum/numHoursToForecast
    return {'price' : {'fromTs': startTs, 'toTs': endTs, 'price': price}}

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
