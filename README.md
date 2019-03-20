# Bot Trading

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
Only one controlling connection (i.e. connection allowed to make trades) with a single username can be done. 
The toolkit supports several execution modes.

#### Manual mode 
- launched by `python -m bot_trading.run_manual_bot_in_real my@username.cz`
- opens local web trading client that can be accessed on `127.0.0.1:5522`
- the trades issued are registered by the remote trading server

#### Sandbox mode
- launched by `python -m bot_trading.run_bot_in_sandbox my@username.cz [peek|history]`
- all trades done by the bot are sandboxed (not registered by the remote trading server)
- if `peek` is provided, runs bot on the most recent trading data
- if `history` is provided, runs bot on historical data from the specified point

#### Real mode
- launched by `python -m bot_trading.run_bot_in_sandbox my@username.cz`
- all trades issued are registered by the remote trading server
- runs bot on the most recent trading data

## Configuration
- `bot-trading/bot_trading/configuration.py`
- allows to configure some apects of the toolkit
- logging verboseness can be configured here 