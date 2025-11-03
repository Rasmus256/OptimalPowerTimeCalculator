import json
import os
from datetime import UTC, date, datetime, timedelta

import requests
from fastapi import FastAPI, HTTPException

today = date.today()

app = FastAPI()

cachedPrices = {}

class EnergyPrice:
    def __init__(self, fromTs, price):
        self.fromTs = datetime.fromisoformat(fromTs)
        self.toTs = self.fromTs + timedelta(hours=1)
        self.price = price
    def __str__(self):
        return str(self.fromTs) + " " + str(self.toTs) + " " + str(self.price)

def getFuturePrices(cache_key):
    global cachedPrices
    today = date.today()
    tomorrow = today + timedelta(days=1)
    if str(cache_key)+"_"+today.strftime('%m/%d/%Y') not in cachedPrices:
      cachedPrices[str(cache_key)+"_"+today.strftime('%m/%d/%Y')]= getprices(today, cache_key)
    if (str(cache_key)+"_"+tomorrow.strftime('%m/%d/%Y') not in cachedPrices) or (not cachedPrices[str(cache_key)+"_"+tomorrow.strftime('%m/%d/%Y')]):
      cachedPrices[str(cache_key)+"_"+tomorrow.strftime('%m/%d/%Y')]= getprices(tomorrow, cache_key)

    FuturePrices = []
    FuturePrices.extend(cachedPrices[str(cache_key)+"_"+today.strftime('%m/%d/%Y')])
    FuturePrices.extend(cachedPrices[str(cache_key)+"_"+tomorrow.strftime('%m/%d/%Y')])
    return [e for e in FuturePrices if e.toTs >= datetime.now(UTC)]

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
async def get_most_optimal_start_and_end_for_duration(numHoursToForecast = '1h1m', glnNumber= None):
    if glnNumber is None:
        glnNumber = os.getenv('GLN_NUMBER')
    if glnNumber is None or glnNumber == '':
        raise HTTPException(status_code=500, detail="INVALID GLNNUMBER. EITHER SET IT TO VIA ENV OR PROVIDE AS PARAMETER")

    hoursString = numHoursToForecast.split('h')[0]
    minuteString = numHoursToForecast.split('h')[1].split('m')[0]
    numHoursInt = int(hoursString)
    numMinutesInt = int(minuteString)
    hoursToForecastInclPartial = numHoursInt
    if numMinutesInt > 0:
        hoursToForecastInclPartial+=1

    FuturePrices = getFuturePrices(glnNumber)
    startIdx, endIdx = determineLongestConsequtiveHours(hoursToForecastInclPartial, FuturePrices)
    print(startIdx)
    print(endIdx)
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
            print(f'Last hour is the least expensive. Using this as a full hour and taking partial hour from the first {allHours[0]}')
            fullHours = allHours[1:]
            partialHour = allHours[0]
            startTs = partialHour.toTs - timedelta(minutes=numMinutesInt)
            endTs = max([e.toTs for e in allHours])

        partialPriceSum = sum([fullHour.price for fullHour in fullHours])
        print(f'Partial hour: {partialHour}')
        partialPriceSum += partialHour.price*(numMinutesInt/60)
        price = partialPriceSum / (numHoursInt + numMinutesInt/60)
        priceIfImpatient = getTotalCostIfImpatient(FuturePrices,  numHoursInt*60+numMinutesInt)
    else:
        print(f"asked to present full hours only. Looking between these hours: {FuturePrices[startIdx]} and {FuturePrices[endIdx]}")
        fullHours = FuturePrices[startIdx:endIdx+1]
        startTs = min([e.fromTs for e in fullHours])
        endTs =   max([e.toTs   for e in fullHours])
        price = sum([e.price for e in fullHours]) / len(fullHours)
        priceIfImpatient = getTotalCostIfImpatient(FuturePrices,  numHoursInt*60+numMinutesInt)
    startTs = datetime.fromtimestamp(startTs.timestamp(), tz=UTC)
    endTs =   datetime.fromtimestamp(endTs.timestamp(), tz=UTC)
    return {'price' : {
        'fromTs': startTs,
        'toTs': endTs,
        'price': price,
        'suboptimalPriceMultiplier': priceIfImpatient*60/(price*(numHoursInt*60+numMinutesInt))},
        'credits': '<p>Elpriser leveret af <a href="www.http://elprisen.somjson.dk/">Elprisen som json.dk</a></p>'}

def getTotalCostIfImpatient(FuturePrices, numberOfMinutes):
    numberOfMinutesLeftInCurrentHour = 60 - datetime.today().minute
    totalPrice = numberOfMinutesLeftInCurrentHour * FuturePrices[0].price / 60
    numberOfMinutes -= numberOfMinutesLeftInCurrentHour
    i = 1
    while numberOfMinutes > 0 and i < len(FuturePrices):
        if numberOfMinutes > 60:
            totalPrice += FuturePrices[i].price
            numberOfMinutes -= 60
            i+=1
        else:
            totalPrice += FuturePrices[i].price * numberOfMinutes / 60
            numberOfMinutes = 0
            i+=1
    return totalPrice


def getprices(dateToFind, gln_number):
    url = f'https://elprisen.somjson.dk/elpris?GLN_Number={gln_number}&start={dateToFind.year}-{dateToFind.month:02d}-{dateToFind.day:02d}'
    string_json = requests.get(url)
    if(string_json.status_code == 200):
        contents = json.loads(string_json.content)
        contents = contents['records']
        possibleDates = [EnergyPrice(e['HourUTC']+'Z',e['Total']) for e in contents]
        return possibleDates
    else:
        print(f"Unable to fetch energy prices for {str(dateToFind)}. Got statuscode {string_json.status_code}")
    return []

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
