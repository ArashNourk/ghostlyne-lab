# Licensing confirmation request to CoinGecko (Amendment 4, point 5; point 4 added 2026-11-28 at the founder's request)

Submitted through CoinGecko's support form before any purchase. The data is not bought until CoinGecko replies in writing.

---

We are considering one month of the Analyst plan to download historical hourly BTC/USD OHLC data (/coins/bitcoin/ohlc/range, from February 2018). Before subscribing, we would like written confirmation of whether the Analyst licence permits the following uses. Please tell us which uses, if any, need a different plan.

1. **Statistical estimation for a price-alert product.** The downloaded candles would be used to:
   - fit a heterogeneous autoregressive (HAR) regression of future realized variance on past realized-variance measures;
   - estimate volatility with an exponentially weighted moving average (EWMA);
   - fit a monotone statistical calibration (isotonic regression) that maps model probabilities to observed outcome frequencies;
   - compute the probability that price reaches a stop or target level first, using a standard first-passage formula.

   The fitted parameters and calibration maps would be used in a commercial subscription product that alerts users when these probabilities change.
2. **Publication of aggregated results.** We would publish aggregate performance statistics computed from the data: accuracy scores (Brier score, log loss), alert hit rates, false-warning rates and counts of outcomes. These would carry attribution to CoinGecko. No CoinGecko prices, candles or time series would be published.
3. **Storage.** The data would be stored privately, never redistributed, and deleted when the subscription ends.
4. **After the subscription ends.** Please confirm:
   - whether we may keep and continue to use the fitted model parameters, calibration maps and derived performance records (the published aggregate statistics) after the Analyst subscription expires, once the raw data itself has been deleted;
   - which plan we would need for ongoing commercial operation, in which the product computes these probabilities from live hourly BTC/USD prices and shows users alert outcomes with attribution.

Thank you.
