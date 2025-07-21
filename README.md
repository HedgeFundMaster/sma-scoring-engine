The SMA Fund Scoring Engine is a dual-layer evaluation system designed to rank and tier separately managed accounts (SMAs) based on both quantitative performance and qualitative investment characteristics. It enables investors, advisors, and PMs to compare funds across asset classes with transparency, consistency, and insight.
📊 Scoring Methodology:

✅ Quantitative Metrics (from sma_scored.csv)
Weights and penalties applied to:

Alpha (Since Inception)

Historical Sharpe Ratio (3Y, 5Y)

Information Ratio (3Y, 5Y)

Max Drawdown (3Y, 5Y)

Daily VaR 5% (3Y, 5Y)

Batting Average (3Y, 5Y)

Upside/Downside Ratio (3Y, 5Y)

Higher = better for return-oriented metrics; lower = better for risk metrics.

🧠 Qualitative Metrics (from qualitative_scored.csv)
Scored subjectively across consistent dimensions such as:

Team Depth

Process Consistency

Transparency

Philosophy Clarity

Edge Relative to Peers

Risk Controls

🔀 Combined Score
Each fund is given a final score computed as:

overall_score = (qual_score * QUAL_WEIGHT) + (quant_score * QUANT_WEIGHT)
Tiered thresholds (customizable in config.yaml) rank funds into:

Tier 1 (Elite)

Tier 2 (Solid)

Tier 3 (Needs Review)





