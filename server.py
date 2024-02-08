from binance.client import Client
import binance
import requests
import json
import math
import pandas as pd
import numpy as np
import time
from os import walk

binanceRequestBase = 'https://api.binance.com/api/v3/'

BINANCE_SECRET_KEY = 'your_secret_key_here'
BINANCE_API_KEY = 'your_api_key_here'

client = binance.client.Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

smaLow = 20
smaHigh = 100

perTP = 0.6
perSL = 0.4

shortOpened = False
longOpened = False

balance = 0

priceTP = 0
priceSL = 0

rsiBullMax = 0
rsiBearMin = 100

leverage = 20
fee = 0.03

quantityPrecision = 0.001 # quantity precision for ETH

def RSI(df, periods = 14, ema = True):
	""" Returns a pd.Series with the relative strength index. """

	closeDelta = df['close'].diff()

	# make two series: one for lower closes and one for higher closes
	up = closeDelta.clip(lower=0)
	down = -1 * closeDelta.clip(upper=0)
	
	if ema == True:
		# use exponential moving average
		maUp = up.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
		maDown = down.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
	else:
		# use simple moving average
		maUp = up.rolling(window = periods, adjust=False).mean()
		maDown = down.rolling(window = periods, adjust=False).mean()
		
	rsi = ma_up / ma_down
	rsi = 100 - (100/(1 + rsi))
	return rsi

def SMA(rng, candles):
	""" Returns SMA series """
    arr = []
    sma = []
    for i in range(rng):
        sma.append(float("Nan"))
        arr.append(float(candles['close'][i]))
    
    for i in range(rng, len(candles['close'])):
        sma.append(sum(arr) / rng)
        arr.pop(0)
        arr.append(float(candles['close'][i]))

    return sma

def GetCandles(symbol):
	""" Saves candle data for given symbol """

	data = {}
	data['line'] = []
	#klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "27 May, 2021", "20 July, 2021")
	klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_5MINUTE, "120 day ago UTC")
	for k in klines:
		line = []
		line.append(k[0])
		line.append(float(k[1]))
		line.append(float(k[2]))
		line.append(float(k[3]))
		line.append(float(k[4]))
		data['line'].append(line)

	with open('candles.json', 'w') as outfile:
		json.dump(data, outfile)

def OHLC(klines):
	""" Makes pd.DataFrame from given kline data """

	data = []

	for k in klines:
		line = []
		line.append(k[0])
		line.append(float(k[1]))
		line.append(float(k[4]))
		line.append(float(k[2]))
		line.append(float(k[3]))
		data.append(line)

	ohlc_ret = pd.DataFrame(data=data, columns=['t','open','close','high','low'])
	return ohlc_ret

def GetBalance(symbol):
	for acc in client.futures_account_balance(): 
		if acc['asset'] == symbol:
			return(acc['balance'])

def OpenShort(price, percentageAmount):
	""" Opens short position """

	CloseAllPositions()

	global priceTP
	global priceSL

	quantityToOrder = (int(percentageAmount) / 100) * float(GetBalance('BUSD'))
	quantityToOrder = int(quantityToOrder)

	quantityToOrder = quantityToOrder / price
	quantityToOrder = quantityToOrder / quantityPrecision

	quantityToOrder = math.floor(quantityToOrder)
	quantityToOrder = quantityToOrder * quantityPrecision

	quantityToOrder = quantityToOrder * leverage

	quantityToOrder = round(quantityToOrder, 3)
	
	print("Quantity to order: ", str(quantityToOrder))

	# REGULAR ORDER

	orderComplete = False

	while not orderComplete:
		try:
			order = client.futures_create_order(
				symbol='ETHBUSD',
				side='SELL',
				type='MARKET',
				positionSide='SHORT',
				quantity=quantityToOrder
			)
			orderComplete = True
		except:
			print("Failed to order, trying again...")
			time.sleep(1)

	print("Order ID: ", str(order['orderId']))

	try:
		openPrice = float(client.futures_get_order(symbol='ETHBUSD', orderId=order['orderId'])['avgPrice'])
	except:
		print("Couldn't get last order info!")
		openPrice = price

	priceTP = round(openPrice * (1 - perTP / 100), 2)
	priceSL = round(openPrice * (1 + perSL / 100), 2)

	# STOP LOSS ORDER
	SLorder = client.futures_create_order(
		symbol='ETHBUSD',
		type='STOP_MARKET',
		positionSide='SHORT',
		side='BUY',
		stopPrice=priceSL,
		closePosition=True
	)

	# TAKE PROFIT ORDER
	TPorder = client.futures_create_order(
		symbol='ETHBUSD',
		type='TAKE_PROFIT_MARKET',
		positionSide='SHORT',
		side='BUY',
		stopPrice=priceTP,
		closePosition=True
	)

	print("TP price: ", str(priceTP))
	print("SL price: ", str(priceSL))

	return(order['orderId'])

def OpenLong(price, percentageAmount):
	""" Opens long position """

	CloseAllPositions()

	global priceTP
	global priceSL

	quantityToOrder = (int(percentageAmount) / 100) * float(GetBalance('BUSD'))
	quantityToOrder = int(quantityToOrder)

	quantityToOrder = quantityToOrder / price
	quantityToOrder = quantityToOrder / quantityPrecision

	quantityToOrder = math.floor(quantityToOrder)
	quantityToOrder = quantityToOrder * quantityPrecision

	quantityToOrder = quantityToOrder * leverage

	quantityToOrder = round(quantityToOrder, 3)

	print("Quantity to order: ", str(quantityToOrder))

	# REGULAR ORDER

	orderComplete = False

	while not orderComplete:
		try:
			order = client.futures_create_order(
				symbol='ETHBUSD',
				positionSide='LONG',
				type='MARKET',
				side='BUY',
				quantity=quantityToOrder
			)
			orderComplete = True
		except:
			print("Failed to order, trying again...")
			time.sleep(1)

	print("Order ID: ", str(order['orderId']))

	try:
		openPrice = float(client.futures_get_order(symbol='ETHBUSD', orderId=order['orderId'])['avgPrice'])
	except:
		print("Couldn't get last order info!")
		openPrice = price

	priceTP = round(openPrice * (1 + perTP / 100), 2)
	priceSL = round(openPrice * (1 - perSL / 100), 2)

	# STOP LOSS ORDER
	SLorder = client.futures_create_order(
		symbol='ETHBUSD',
		type='STOP_MARKET',
		positionSide='LONG',
		side='SELL',
		stopPrice=priceSL,
		closePosition=True
	)

	# TAKE PROFIT ORDER
	TPorder = client.futures_create_order(
		symbol='ETHBUSD',
		type='TAKE_PROFIT_MARKET',
		positionSide='LONG',
		side='SELL',
		stopPrice=priceTP,
		closePosition=True
	)

	print("TP price: ", str(priceTP))
	print("SL price: ", str(priceSL))

	return(order['orderId'])

def TrackLive(symbol):
	""" Live tracking """

	global rsiBullMax
	global rsiBearMin

	global shortOpened
	global longOpened
	global priceTP
	global priceSL
	global balance

	positionPrice = 0

	profits = 0
	losses = 0

	rsiDifference = 30

	feesToPay = 0

	currentRsi = 0

	while True:

		if shortOpened or longOpened:
			# WE ARE IN TRADE AND WE ARE CHECKING IF BINANCE SOLD THE POSITION

			opened = False
			positions = client.futures_account()['positions']

			# WE CHECK FOR OPENED POSITIONS, IF YES THEN WE SET opened = true
			for position in positions:
				if (position['symbol'] == 'ETHBUSD' and float(position['maintMargin']) != 0):
					opened = True

			# NO POSITIONS ARE OPENED
			if not opened:
				openedOrders = client.futures_get_open_orders()

				for o in openedOrders:
					if o['type'] == 'TAKE_PROFIT_MARKET':
						# LOSS

						print("Position closed with LOSS of ", perSL, " | Time: ", time.strftime("%b %d %Y %H:%M:%S", time.localtime()))
						losses = losses + 1

						balance = GetBalance('BUSD')
						print("Balance: ", balance)
						print("Profits: ", profits)
						print("Losses: ", losses)
						print("W/L ratio: ", (profits / (profits + losses)) * 100)

						if longOpened:
							rsiBullMax = currentRsi
						elif shortOpened:
							rsiBearMin = currentRsi
						
					elif o['type'] == 'STOP_MARKET':
						# PROFIT

						print("Position closed with PROFIT of ", perTP, " | Time: ", time.strftime("%b %d %Y %H:%M:%S", time.localtime()))
						profits = profits + 1

						balance = GetBalance('BUSD')
						print("Balance: ", balance)
						print("Profits: ", profits)
						print("Losses: ", losses)
						print("W/L ratio: ", (profits / (profits + losses)) * 100)

						if longOpened:
							rsiBullMax = currentRsi
						elif shortOpened:
							rsiBearMin = currentRsi

				shortOpened = False
				longOpened = False

				client.futures_cancel_all_open_orders(symbol='ETHBUSD')

		else:
			# WE ARE NOT IN TRADE AND DOWNLOADING CHART DATA TO OPEN POSITION

			getKlines = False
			while not getKlines:
				try:
					klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_5MINUTE, "24 hour ago UTC")
					getKlines = True
				except:
					print("Couldn't get klines, trying again in 1 seconds!")
					time.sleep(1)

			ohlc = OHLC(klines)

			rsi = RSI(ohlc)

			smaLowValues = SMA(smaLow, ohlc)
			smaHighValues = SMA(smaHigh, ohlc)

			currentPrice = float(ohlc['close'][len(ohlc['close']) - 2])
			currentPrice = round(currentPrice, 2)
			currentRsi = rsi[len(rsi) - 1]
			currentSmaHigh = smaHighValues[-1]
			currentSmaLow = smaLowValues[-1]

			smaDifference = abs(currentSmaLow - currentSmaHigh)
			minSmaDifference = currentPrice / 500

			# *********************************************************************************************************************************
			# ************************************************** OPENING POSITIONS ************************************************************
			# *********************************************************************************************************************************

			if (currentSmaLow < currentSmaHigh):

				#BEAR : OPENING SHORT POSITIONS
				rsiBullMax = 0

				rsiBearMin = min(rsiBearMin, currentRsi)

				if currentRsi - rsiBearMin > rsiDifference and smaDifference > minSmaDifference and not shortOpened and not longOpened:
					print("************************************")
					print("Short opened at: ", str(currentPrice), " | Time: ", time.strftime("%b %d %Y %H:%M:%S", time.localtime()))

					positionPrice = currentPrice

					order = OpenShort(currentPrice, 100)

					shortOpened = True
			else:

				#BULL : OPENING LONG POSITIONS
				rsiBearMin = 100

				rsiBullMax = max(rsiBullMax, currentRsi)

				if rsiBullMax - currentRsi > rsiDifference and smaDifference > minSmaDifference and not longOpened and not shortOpened:
					print("************************************")
					print("Long opened at: ", str(currentPrice), " | Time: ", time.strftime("%b %d %Y %H:%M:%S", time.localtime()))

					positionPrice = currentPrice

					order = OpenLong(currentPrice, 100)

					longOpened = True

			# *********************************************************************************************************************************
			# *********************************************************************************************************************************
			# *********************************************************************************************************************************

		time.sleep(1)

def CloseAllPositions():
	""" Closes all open positions if any """

	try:
		client.futures_cancel_all_open_orders(symbol='ETHBUSD')
	except:
		print("Error while canceling all open orders!")


	positions = client.futures_account()['positions']
	for position in positions:
		if (position['symbol'] == 'ETHBUSD' and float(position['maintMargin']) != 0):

			# WE CLOSE LONG POSITION
			if (position['positionSide'] == 'LONG'):
				print("Closing long...")
				order = client.futures_create_order(
					symbol='ETHBUSD',
					positionSide='LONG',
					type='MARKET',
					side='SELL',
					quantity=float(position['positionAmt'])
				)
				print("Long closed!")

			# WE CLOSE SHORT POSITION
			elif (position['positionSide'] == 'SHORT'):
				print("Closing short...")
				order = client.futures_create_order(
					symbol='ETHBUSD',
					positionSide='SHORT',
					type='MARKET',
					side='BUY',
					quantity=abs(float(position['positionAmt']))
				)
				print("Short closed!")

if __name__=="__main__":
	print('Started at: ', time.strftime("%b %d %Y %H:%M:%S", time.localtime()) )
	balance = GetBalance('BUSD')
	print('Starting balance: ', balance)

	openedOrders = client.futures_get_open_orders()

	if (len(openedOrders) >= 2):
		# WE HAVE OPENED POSITION
		order1 = openedOrders[0]
		order2 = openedOrders[1]

		if (order1['positionSide'] == 'LONG'):
			# LONG POSITION WAS OPENED
			print("LONG position already opened!")
			priceTP = max(float(order1['stopPrice']), float(order2['stopPrice']))
			priceSL = min(float(order1['stopPrice']), float(order2['stopPrice']))

			priceTP = round(priceTP, 2)
			priceSL = round(priceSL, 2)

			print("TP price: ", priceTP)
			print("SL price: ", priceSL)
			longOpened = True
			shortOpened = False

		else:
			# SHORT POSITION WAS OPENED
			print("SHORT position already opened!")
			priceTP = min(float(order1['stopPrice']), float(order2['stopPrice']))
			priceSL = max(float(order1['stopPrice']), float(order2['stopPrice']))

			priceTP = round(priceTP, 2)
			priceSL = round(priceSL, 2)

			print("TP price: ", priceTP)
			print("SL price: ", priceSL)
			longOpened = False
			shortOpened = True

	else:
		# WE CLOSE OPENED POSITIONS AND ORDERS
		CloseAllPositions()

		# WE READ LAST X RSI AND SMA VALUES

		klines = client.get_historical_klines('ETHBUSD', Client.KLINE_INTERVAL_5MINUTE, "24 hour ago UTC")

		ohlc = OHLC(klines)

		rsi = RSI(ohlc)

		smaLowValues = SMA(20, ohlc)
		smaHighValues = SMA(100, ohlc)

		currentPrice = int(ohlc['close'][len(ohlc['close']) - 1])
		currentRsi = rsi[len(rsi) - 1]
		currentSmaHigh = smaHighValues[-1]
		currentSmaLow = smaLowValues[-1]

		if (currentSmaLow < currentSmaHigh):
			#BEAR
			rsiBullMax = 0
			for i in range(len(rsi) - 10, len(rsi) - 1):
				rsiBearMin = min(rsiBearMin, rsi[i])

			print("RSI min: ", rsiBearMin)

		else:
			#BULL
			rsiBearMin = 100
			for i in range(len(rsi) - 10, len(rsi) - 1):
				rsiBullMax = max(rsiBullMax, rsi[i])

			print("RSI max: ", rsiBullMax)


	TrackLive('ETHBUSD')


