# Paper Snipe Bot

A standard-library Python CLI demo that paper-trades synthetic meme-token launches. It combines mock on-chain signals (liquidity, holder growth, and buy pressure) with mock social signals (mention growth and sentiment), then adjusts its entry-score threshold based on closed simulated trades.

This is a learning prototype, not a profitable-strategy claim. Market data is generated locally and deterministically from a seed; it does not read live feeds, connect to a blockchain, use a wallet, or submit real orders.

## Run

```sh
python3 tools/paper-snipe-bot/bot.py --ticks 20 --seed 7 --balance 1000
```

Run the tests from this directory:

```sh
python3 -m unittest -v
```

The virtual strategy risks 10% of available cash per position, holds at most two positions, and exits at a 20% take-profit, a 12% stop-loss, or after five ticks. After each closed trade, it lowers its entry threshold by 0.01 for a win or raises it by 0.02 for a loss, clamped between 0.45 and 0.85.
