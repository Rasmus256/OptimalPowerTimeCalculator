from fastapi import FastAPI
import asyncio
import requests
from datetime import datetime, timedelta, date
import json
import pytz
import os

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

def getFuturePrices(price_class):
    global cachedPrices
    today = date.today()
    tomorrow = today + timedelta(days=1)
    if not str(price_class)+"_"+today.strftime('%m/%d/%Y') in cachedPrices:
      cachedPrices[str(price_class)+"_"+today.strftime('%m/%d/%Y')]= getprices(today, price_class)
    if not str(price_class)+"_"+tomorrow.strftime('%m/%d/%Y') in cachedPrices:
      cachedPrices[str(price_class)+"_"+tomorrow.strftime('%m/%d/%Y')]= getprices(tomorrow, price_class)

    FuturePrices = []
    FuturePrices.extend(cachedPrices[str(price_class)+"_"+today.strftime('%m/%d/%Y')])
    FuturePrices.extend(cachedPrices[str(price_class)+"_"+tomorrow.strftime('%m/%d/%Y')])
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
async def get_most_optimal_start_and_end_for_duration(numHoursToForecast = '1h1m', priceClass= None):
    if priceClass is None:
        priceClass = os.getenv('PRICE_CLASS')
    if not (priceClass == 'DK1' or priceClass == 'DK2'):
        return {'errorCode': "INVALID PRICE CLASS. EITHER SET IT TO 'DK1' or 'DK2'"}

    hoursString = numHoursToForecast.split('h')[0]
    minuteString = numHoursToForecast.split('h')[1].split('m')[0]
    numHoursInt = int(hoursString)
    numMinutesInt = int(minuteString)
    hoursToForecastInclPartial = numHoursInt
    if numMinutesInt > 0:
        hoursToForecastInclPartial+=1

    FuturePrices = getFuturePrices(priceClass)
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
            print(f'Last hour is the least expensive. Using this as a full hour and taking partial hour from the first {allHours[0]}')
            fullHours = allHours[1:]
            partialHour = allHours[0]
            startTs = partialHour.toTs - timedelta(minutes=numMinutesInt)
            endTs = max([e.toTs for e in allHours])

        partialPriceSum = sum([fullHour.price for fullHour in fullHours])
        print(f'Partial hour: {partialHour}')
        partialPriceSum += partialHour.price*(numHoursInt/60)
        price = partialPriceSum / (numHoursInt + numMinutesInt/60)
        priceIfImpatient = getTotalCostIfImpatient(FuturePrices,  numHoursInt*60+numMinutesInt)
    else:
        print(f"asked to present full hours only. Looking between these hours: {FuturePrices[startIdx]} and {FuturePrices[endIdx]}")
        fullHours = FuturePrices[startIdx:endIdx+1]
        startTs = min([e.fromTs for e in fullHours])
        endTs = max([e.toTs for e in fullHours])
        price = sum([e.price for e in fullHours]) / len(fullHours)
        priceIfImpatient = getTotalCostIfImpatient(FuturePrices,  numHoursInt*60+numMinutesInt)
    return {'price' : {'fromTs': startTs, 'toTs': endTs, 'price': price, 'suboptimalPrice': priceIfImpatient}, 'credits': '<p>Elpriser leveret af <a href="https://www.elprisenligenu.dk">Elprisen lige nu.dk</a></p>'}

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
    return totalPrice        
    
    
    

def getprices(dateToFind, price_class):
    url = f'https://www.elprisenligenu.dk/api/v1/prices/{dateToFind.year}/{dateToFind.month:02d}-{dateToFind.day:02d}_{price_class}.json'
    string_json = requests.get(url)
    if(string_json.status_code == 200):
        contents = json.loads(string_json.content)
        possibleDates = [EnergyPrice(e['time_start'],e['time_end'],e['DKK_per_kWh']) for e in contents]
        return possibleDates
    else:
        print(f"Unable to fetch energy prices for {str(dateToFind)}. Got statuscode {string_json.status_code}")
    return []

@app.get("/healthz", status_code=204)
def healthcheck():
    return None
