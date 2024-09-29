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
    def __str__(self):
        return str(self.fromTs) + " " + str(self.toTs) + " " + str(self.price)

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
    for i in range(len(FuturePrices)-(hoursToForecastInclPartial-1)):
        window_sum = 0
        for j in range(hoursToForecastInclPartial):
            window_sum += FuturePrices[i+j].price
        if window_sum < min_sum:
            min_sum = window_sum
            startIdx = i
            endIdx = i+hoursToForecastInclPartial-1
    #Were we asked to forecast a partial hour? If so, either attach this partial hour to the beginning or the end - depending on price.
    price = 0
    if numMinutesInt>0:
        if FuturePrices[startIdx].price < FuturePrices[endIdx].price:
            fullHours = FuturePrices[startIdx:endIdx]
            partialHour = FuturePrices[endIdx]
            allHours = FuturePrices[startIdx:endIdx+1]
            print('First hour is the least expensive')
            startTs = min([e.fromTs for e in allHours])
            endTs = partialHour.fromTs + timedelta(minutes=numMinutesInt)

        else:
            allHours = FuturePrices[startIdx:endIdx+1]
            fullHours = FuturePrices[startIdx+1:endIdx+1]
            partialHour = FuturePrices[startIdx]
            print('Last hour is least expensive')
            startTs = partialHour.toTs - timedelta(minutes=numMinutesInt)
            endTs = max([e.toTs for e in allHours])

        for fullHour in fullHours:
            print(fullHour)
            min_sum += fullHour.price
        print(f'Partial hour: {partialHour}')
        min_sum += partialHour.price*(numHoursInt/60)
        price = min_sum / (numHoursInt + numMinutesInt/60)
    else:
        startTs = FuturePrices[startIdx].fromTs
        endTs = FuturePrices[endIdx].toTs
        price = min_sum/hoursToForecastInclPartial
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
