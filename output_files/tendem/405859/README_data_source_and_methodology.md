
Dataset: Daily Cryptocurrency Prices & Volumes (15 assets), June 2021 – June 2024

Data Source
- Primary: CryptoCompare (free tier), due to CoinGecko free API historical limits (~365 days) and CoinMarketCap key lacking historical OHLCV access.
- Customer-requested sources (CoinGecko/CMC) were attempted; documented limitations prevented full-range collection.

Symbols (15): BTC, ETH, USDT, BNB, XRP, SOL, USDC, ADA, DOGE, TRX, TON, DOT, MATIC, LTC, AVAX.

Coverage & Frequency
- Daily records from 2021-06-01 to 2024-06-30.
- June 30, 2024 was appended using the latest available values (closing price replicated for open/high/low; volume approximated with previous day’s value).

Columns
- Symbol, Name, Date (YYYY-MM-DD)
- Opening Price (USD), Closing Price (USD), High Price (USD), Low Price (USD)
- Trading Volume (USD)
- Market Cap (USD) [Derived]
- Market Cap Rank [as provided in source; final rank will be recomputed within the 15-coin universe in the next step]

Market Cap Methodology (Approximation)
- Daily Market Cap (USD) computed as: closing_price × static circulating supply.
- Static circulating supply approximations (industry-standard ballpark mid-2022/2023):
  BTC: 19,400,000
  ETH: 120,000,000
  USDT: 64,000,000,000
  BNB: 154,000,000
  XRP: 48,000,000,000
  SOL: 390,000,000
  USDC: 27,000,000,000
  ADA: 32,000,000,000
  DOGE: 130,000,000,000
  TRX: 72,000,000,000
  TON: 1,500,000,000
  DOT: 1,000,000,000
  MATIC: 10,000,000,000
  LTC: 66,000,000
  AVAX: 240,000,000

Caveats
- Market caps are approximate (static supply) and do not reflect day-by-day supply changes. This approach was approved to meet delivery timelines.
- Market cap ranks will be recomputed among these 15 assets using the derived market caps in the subsequent ranking step.
- Any deviations due to source differences are documented; if CoinGecko Pro access becomes available, the dataset can be regenerated from the requested sources.

Revision History
- 2025-10-24T12:55:00.817215 UTC: Initial delivery of updated dataset with derived market caps and June 30, 2024 appended.


Ranking Method Update (Strict Ranks)
- Daily Market Cap Rank is computed strictly within the 15-coin universe: 1..15.
- Tie-breaking rule: descending Market Cap, then ascending Symbol (alphabetical).
- Update timestamp: 2025-10-24T13:19:48.189565+00:00 UTC
