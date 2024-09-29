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

def getFuturePrices():
    global cachedPrices
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
    return [e for e in FuturePrices if e.toTs >= utc.localize(datetime.now())]

def determineLongestConsequtiveHours(hoursToForecastInclPartial, FuturePrices):
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
    return startIdx, endIdx


@app.get("/api/next-optimal-hour")
async def get_days_until_out_of_mainframe(numHoursToForecast = '2h35m'):
    hoursString = numHoursToForecast.split('h')[0]
    minuteString = numHoursToForecast.split('h')[1].split('m')[0]
    numHoursInt = int(hoursString)
    numMinutesInt = int(minuteString)
    hoursToForecastInclPartial = numHoursInt
    if numMinutesInt > 0:
        hoursToForecastInclPartial+=1

    FuturePrices = getFuturePrices()
    startIdx, endIdx = determineLongestConsequtiveHours(hoursToForecastInclPartial, FuturePrices)

    #Were we asked to forecast a partial hour? If so, either attach this partial hour to the beginning or the end - depending on price.
    price = 0
    if numMinutesInt>0:
        allHours = FuturePrices[startIdx:endIdx+1]
        if FuturePrices[startIdx].price <= FuturePrices[endIdx].price:
            print(f'First hour is the least expensive. Using this as a full hour and taking partial from the end {allHours[-1]}')
            fullHours = allHours[:-1]
            partialHour = allHours[-1]
            startTs = min([e.fromTs for e in allHours])
            endTs = partialHour.fromTs + timedelta(minutes=numMinutesInt)
        else:
            print(f'First hour is the least expensive. Using this as a full hour and taking partial hour from the first {allHours[0]}')
            fullHours = allHours[1:]
            partialHour = allHours[0]
            startTs = partialHour.toTs - timedelta(minutes=numMinutesInt)
            endTs = max([e.toTs for e in allHours])

        partialPriceSum = sum([fullHour.price for fullHour in fullHours])
        print(f'Partial hour: {partialHour}')
        partialPriceSum += partialHour.price*(numHoursInt/60)
        price = partialPriceSum / (numHoursInt + numMinutesInt/60)
    else:
        fullHours = FuturePrices[startIdx:endIdx+1]
        startTs = min([e.fromTs for e in fullHours])
        endTs = max([e.toTs for e in fullHours])
        price = avg([e.price for e in fullHours])
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
