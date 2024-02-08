# binance-crypto-scalping-bot

Crypto trading bot using SMA and RSI indicators. It connects to the binance via API keys and tracks live data and decides when to place and close orders.

# Requirements

Module  | Version
------------- | -------------
requests  | 2.25.1
numpy  | 1.21.0
pandas  | 1.2.5
python-binance  | 0.7.9

# Instructions

Make new SECRET_KEY and API_KEY in your binance dashboard. Give them appropriate permissions if asked. Place these keys at the beginning of the *server.py* script.
Adjust the parameters according to your preferences and change crypto pair on which you would like to trade. 
Run *server.py* and live trading should start.

Parameters that can be adjusted: smaLow, smaHigh, perTP, perSL, rsiBullMax, rsiBearMin, leverage.
