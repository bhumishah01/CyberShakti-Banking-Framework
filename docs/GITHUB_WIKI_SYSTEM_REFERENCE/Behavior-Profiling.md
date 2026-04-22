# Behavior Profiling

## What Is Tracked

The local `user_profiles` table stores:

- total transaction count
- total amount
- average amount
- last transaction time
- hourly usage histogram
- rolling user risk score

## Average and Volume Computation

Each successful local transaction updates:

- `tx_count`
- `total_amount`
- `avg_amount`

## Preferred Usage Time

The `hour_hist` JSON histogram records how often the user transacts during each hour of the day.

The helper `preferred_hours(profile, top_n=3)` extracts the top hours. The fraud engine then uses that information to detect unusual timing once sufficient history exists.

## Rolling User Risk Score

The project updates user risk using an EWMA-like approach:

- first transaction -> user risk equals tx risk
- later transactions blend prior user risk and current tx risk

This prevents the score from jumping too aggressively after one event while still adapting over time.

## Admin Use of Profiles

The admin portal uses profiles for:

- high-risk user ranking
- peak hour display
- average amount reporting
- deep-dive analytics for one selected user
