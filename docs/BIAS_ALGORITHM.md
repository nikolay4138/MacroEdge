# Bias Scoring Algorithm — Mathematical Specification

## 1. Objective

Produce a **Daily Bias Score** \( S \in [-100, +100] \) per index (S&P 500, NASDAQ 100, DAX 40, Nikkei 225), with:

- **Market Regime** classification
- **Confidence** \( C \in [0, 100]\% \)
- **Risk Flag** ∈ {Low, Medium, High}

---

## 2. Notation

| Symbol                  | Meaning                                                                            |
| ----------------------- | ---------------------------------------------------------------------------------- |
| \( I \)                 | Set of macro indicators (CPI, PMI, NFP, etc.)                                      |
| \( i \)                 | Single indicator, \( i \in I \)                                                    |
| \( j \)                 | Index (e.g. SPX, NDX, DAX, NKY)                                                    |
| \( w\_{i,j} \)          | Base weight of indicator \( i \) for index \( j \) (from `index_indicator_weight`) |
| \( r \)                 | Current market regime (risk_on, risk_off, inflationary, recessionary, neutral)     |
| \( w\_{i,j}(r) \)       | Regime-adjusted weight for \( i \) on \( j \)                                      |
| \( \sigma_i \)          | Surprise (actual − forecast) for indicator \( i \)                                 |
| \( \tilde{\sigma}\_i \) | Normalized surprise (see below)                                                    |
| \( \nu \)               | Volatility filter factor \( \in [0,1] \)                                           |
| \( y \)                 | Yield curve component (e.g. 2Y–10Y spread)                                         |

---

## 3. Surprise Normalization

For each indicator \( i \) with release at time \( t \):

\[
\sigma_i = \text{Actual}\_i - \text{Forecast}\_i
\]

To make surprises comparable across indicators (different units and scales):

\[
\tilde{\sigma}_i = \frac{\sigma_i - \mu_{\sigma*i}}{\max(\epsilon, \text{std}*{\sigma_i})}
\]

- \( \mu*{\sigma_i}, \text{std}*{\sigma_i} \) over a rolling window (e.g. 12–24 months).
- \( \epsilon \) small constant to avoid division by zero.
- Optional: cap \( \tilde{\sigma}\_i \in [-3, +3] \) to limit outliers.

**Direction:** For “good for risk” indicators (e.g. GDP↑, PMI↑, NFP↑), positive \( \tilde{\sigma}\_i \) → positive contribution to bias. For “bad for risk” (e.g. CPI↑, Unemployment↑), positive \( \tilde{\sigma}\_i \) → negative contribution. So define:

\[
s_i = \text{sign}\_i \cdot \tilde{\sigma}\_i
\]

where \( \text{sign}\_i \in \{-1, +1\} \) is configured per indicator (e.g. CPI: +1 → bearish → negative sign).

---

## 4. Regime-Adjusted Weights

Base weight \( w*{i,j} \in [0,1] \), \( \sum_i w*{i,j} = 1 \) per \( j \).

Regime multiplier \( m\_{i,j}(r) \) from `index_indicator_weight.regime_weights` (e.g. 1.2 in risk_on, 0.8 in risk_off):

\[
w*{i,j}(r) = \frac{w*{i,j} \cdot m*{i,j}(r)}{\sum_k w*{k,j} \cdot m\_{k,j}(r)}
\]

So weights remain normalized per index and regime.

---

## 5. Raw Score (Indicator Contribution)

\[
S*{\text{raw},j} = \sum*{i \in I} w\_{i,j}(r) \cdot s_i
\]

- \( S\_{\text{raw},j} \) is on an unbounded scale; we map it to \( [-100, +100] \).

---

## 6. Mapping to \( [-100, +100] \)

Use a bounded transform (e.g. tanh) so that extreme raw scores do not dominate:

\[
S*j = 100 \cdot \tanh\left( \frac{S*{\text{raw},j}}{\lambda_j} \right)
\]

- \( \lambda*j > 0 \) is a scale parameter (e.g. chosen so that “typical” \( |S*{\text{raw},j}| \) gives \( |S_j| \) in a desired range, e.g. 20–60). Can be calibrated per index.

Alternative (linear clip):

\[
S*j = \text{clip}\left( \kappa_j \cdot S*{\text{raw},j}, \, -100, \, +100 \right)
\]

with \( \kappa*j \) chosen from historical distribution of \( S*{\text{raw},j} \).

---

## 7. Volatility Filter

Let VIX (or MOVE) at time \( t \) be \( V_t \). Define:

\[
\nu = 1 - \min\left(1, \, \frac{V*t - V*{\min}}{V*{\max} - V*{\min}}\right)
\]

- \( V*{\min}, V*{\max} \) from config (e.g. 10 and 40 for VIX). High VIX → \( \nu \) small.

**Use of \( \nu \):**

- **Option A:** Scale confidence: \( C' = C \cdot \nu \) (high vol → lower confidence).
- **Option B:** Blend score with neutral: \( S_j' = \nu \cdot S_j + (1-\nu) \cdot 0 \).

Recommended: use \( \nu \) in **confidence** and optionally in **risk flag**, not necessarily to pull score to zero (so that “high vol + bearish macro” still shows bearish but with lower confidence).

---

## 8. Yield Curve (Optional Adjustment)

2Y–10Y spread \( y \):

- Inversion (e.g. \( y < 0 \)) → recessionary signal → optional small downward tilt to bias or increase “recessionary” regime probability.
- Steepening → optional small upward tilt.

Example (additive adjustment, small magnitude):

\[
\Delta\_{\text{yield}} = \alpha \cdot \text{sign}(y) \cdot \min(|y|/50\,\text{bp}, 1)
\]

Then \( S*j \leftarrow S_j + \Delta*{\text{yield}} \), and clip again to \( [-100, +100] \). \( \alpha \) configurable (e.g. ±5–10 points max).

---

## 9. Regime Classification

Inputs:

- Recent macro surprises (direction and magnitude)
- VIX / MOVE level
- 2Y–10Y spread
- Optional: equity index returns (e.g. 20d)

**Rule-based (MVP):**

- **Risk-Off:** VIX above threshold and/or 2Y–10Y inverted and recent macro mostly negative.
- **Inflationary:** CPI/Core CPI surprises positive and/or rising trend; yields up.
- **Recessionary:** PMI/employment weak; 2Y–10Y inverted; macro negative.
- **Risk-On:** VIX low; macro surprises positive; curve not inverted.
- **Neutral:** Else.

**Future (ML):** Replace or blend with classifier (e.g. Random Forest / small neural net) trained on labeled regimes; output \( P(r) \). Use \( \arg\max*r P(r) \) or expected weights \( \sum_r P(r) w*{i,j}(r) \).

---

## 10. Confidence Level \( C \)

\[
C = C*{\text{data}} \cdot C*{\text{coverage}} \cdot \nu
\]

- **\( C\_{\text{data}} \):** Based on recency and quality of inputs (e.g. share of indicators with a release in last N days; no stale data).
- **\( C\_{\text{coverage}} \):** Fraction of expected indicators actually available (e.g. 12/15 → 0.8).
- **\( \nu \):** Volatility filter above.

Normalize so \( C \in [0, 100] \).

---

## 11. Risk Flag

- **Low:** \( C \geq C*{\text{high}} \), \( |S_j| \leq S*{\text{mod}} \), VIX below threshold.
- **High:** \( C \leq C\_{\text{low}} \) or VIX very high or regime “recessionary” + strong negative bias.
- **Medium:** Else.

Thresholds \( C*{\text{high}}, C*{\text{low}}, S\_{\text{mod}} \) configurable.

---

## 12. Output Summary

| Output                   | Formula / Logic                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------- | --- | --------------- |
| **Bias Score** \( S_j \) | \( 100 \cdot \tanh(S\_{\text{raw},j}/\lambda_j) \), optional yield + volatility blend |
| **Regime** \( r \)       | Rule-based (MVP) or ML (V2)                                                           |
| **Confidence** \( C \)   | \( C*{\text{data}} \cdot C*{\text{coverage}} \cdot \nu \), scaled to [0,100]          |
| **Risk Flag**            | Low / Medium / High from \( C \), \(                                                  | S_j | \), VIX, regime |

All parameters (\( \lambda_j, \kappa_j, \alpha \), thresholds, regime rules) should live in **configuration** (DB or config service) for calibration without code changes.
