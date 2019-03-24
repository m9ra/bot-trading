# Bot Trading

## Requirements
- `python > 3.6`
- `pip install jsonpickle` this is a non-standard package that is required

#### Recommended pacakges
- for using NeuralPredictor you would need those packages
- `pip install tensorflow`
- `pip install tflearn`
- `pip install numpy`

## Structure
The toolkit consists of two parts.
#### core
The first part implements remote services (as exchange scraper, history provider, web...) and corresponding connectors.
It is highly advised not to touch them.

#### trading, bots
The second part provides higher abstraction levels over the core and can be subject of customizations.

The bots package implements some basic trading strategies and serves as a showcase of the available API.

## Usage
All the scripts has to be executed from `bot-trading` directory.

Every bot must be logged in via a username. It can be either set in `bot-trading/bot_trading/configuration.py` or passed in 
as an environment variable `USERNAME`. The username must be a valid email.
Only one controlling connection (i.e. connection allowed to make trades) per username can be done. 

The toolkit supports several execution modes.


#### Real mode
- launched by `python -m bot_trading.run_bot_in_real`
- all trades issued **are** registered by the remote trading server
- runs bot on the most recent trading data

#### Manual mode 
- launched by `python -m bot_trading.run_manual_bot_in_real`
- all trades issued **are** registered by the remote trading server
- opens local web trading client that can be accessed on `http://127.0.0.1:5522/`


#### Sandbox mode
- launched by `python -m bot_trading.run_bot_in_sandbox`
- all trades done by the bot are **sandboxed** (not registered by the remote trading server)
- runs bot on the most recent trading data

#### Backtesting mode
- launched by `python -m bot_trading.run_bot_backtest`
- all trades done by the bot are **sandboxed** (not registered by the remote trading server)
- runs bot on historical data (date range can be specified in the launcher script)


## Configuration
- `bot-trading/bot_trading/configuration.py`
- permanent `USERNAME` can be specified here (so it does not need to be passed as env var)
- allows to configure some apects of the toolkit
- logging verboseness can be configured here 