# Backtest

2,865 games scored, 22 Oct 2024 to 18 Nov 2026. Every prediction used only earlier games.

## 1. How close are the predictions?

Average miss in points (lower is better). 'Line' is the sportsbook's closing number.

| Season | Games | Margin: model | Margin: line | Total: model | Total: line | Winner: model | Winner: line |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024-25 | 1,317 | 10.87 | 10.61 | 14.47 | 14.14 | 67.3% | 69.0% |
| 2025-26 | 1,322 | 11.20 | 11.00 | 14.88 | 14.51 | 68.7% | 68.4% |
| 2026-27 | 222 | 11.61 | 11.32 | 14.30 | 13.97 | 68.5% | 70.7% |
| All | 2,861 | 11.08 | 10.85 | 14.64 | 14.30 | 68.0% | 68.9% |

What each layer adds (all scored seasons, average miss):

| Version | Margin | Total |
| --- | ---: | ---: |
| Team ratings only | 11.25 | 14.66 |
| + absences guessed the day before | 11.21 | 14.66 |
| + lineups known | 11.08 | 14.64 |
| Sportsbook closing line | 10.85 | 14.30 |
| Sportsbook opening line | 11.10 | 14.59 |

Win chances (lower is better): model log-loss 0.5890 vs line 0.5783; Brier 0.2022 vs 0.1983.

## 2. Does the model know anything the line doesn't?

Best blend = line + w x (model - line). w = 0 means the model adds nothing; w is only real if it is about 2 standard errors above zero.

| Test | Games | w | Std. error | Verdict |
| --- | ---: | ---: | ---: | --- |
| Margin vs closing line (lineups known) | 2,863 | -0.06 | 0.10 | nothing proven |
| Total vs closing line (lineups known) | 2,862 | -0.09 | 0.10 | nothing proven |
| Margin vs opening line (day before) | 2,779 | +0.21 | 0.09 | adds information |
| Total vs opening line (day before) | 2,731 | +0.38 | 0.10 | adds information |

## 3. Betting the disagreements

One unit on the model's side at the price stored for that line. Break-even at -110 is 52.4%. 'Line moved our way' is the average number of points the closing line ended up on our side of the opening line we took.

**Spreads at the OPENING line (day-before model)**

| Model vs line | Bets | Record | Win % | Return per bet | Line moved our way |
| --- | ---: | --- | ---: | ---: | ---: |
| 0+ pts | 2,779 | 1425-1354-0 | 51.3% ± 1.9 | -2.2% ± 3.5 | +0.37 |
| 1+ pts | 1,994 | 1021-973-0 | 51.2% ± 2.2 | -2.4% ± 4.2 | +0.52 |
| 2+ pts | 1,342 | 697-645-0 | 51.9% ± 2.7 | -1.0% ± 5.1 | +0.68 |
| 3+ pts | 807 | 425-382-0 | 52.7% ± 3.4 | +0.3% ± 6.6 | +0.83 |
| 4+ pts | 462 | 252-210-0 | 54.5% ± 4.5 | +3.7% ± 8.6 | +1.03 |
| 6+ pts | 141 | 75-66-0 | 53.2% ± 8.2 | +0.7% ± 15.7 | +1.41 |

**Totals at the OPENING line (day-before model)**

| Model vs line | Bets | Record | Win % | Return per bet | Line moved our way |
| --- | ---: | --- | ---: | ---: | ---: |
| 0+ pts | 2,731 | 1414-1317-0 | 51.8% ± 1.9 | -1.2% ± 3.6 | +0.96 |
| 1+ pts | 2,060 | 1094-966-0 | 53.1% ± 2.2 | +1.2% ± 4.1 | +1.17 |
| 2+ pts | 1,495 | 810-685-0 | 54.2% ± 2.5 | +3.3% ± 4.8 | +1.49 |
| 3+ pts | 981 | 506-475-0 | 51.6% ± 3.1 | -1.7% ± 6.0 | +1.91 |
| 4+ pts | 639 | 329-310-0 | 51.5% ± 3.9 | -1.9% ± 7.4 | +2.27 |
| 6+ pts | 219 | 132-87-0 | 60.3% ± 6.5 | +14.7% ± 12.4 | +3.44 |

**Spreads at the CLOSING line (lineups known)**

| Model vs line | Bets | Record | Win % | Return per bet | Line moved our way |
| --- | ---: | --- | ---: | ---: | ---: |
| 0+ pts | 2,863 | 1403-1460-0 | 49.0% ± 1.8 | -6.6% ± 3.5 | - |
| 1+ pts | 1,962 | 956-1006-0 | 48.7% ± 2.2 | -7.1% ± 4.2 | - |
| 2+ pts | 1,224 | 591-633-0 | 48.3% ± 2.8 | -8.1% ± 5.3 | - |
| 3+ pts | 646 | 307-339-0 | 47.5% ± 3.9 | -9.4% ± 7.3 | - |
| 4+ pts | 322 | 153-169-0 | 47.5% ± 5.5 | -9.5% ± 10.4 | - |
| 6+ pts | 63 | 32-31-0 | 50.8% ± 12.3 | -2.6% ± 23.9 | - |

**Totals at the CLOSING line (lineups known)**

| Model vs line | Bets | Record | Win % | Return per bet | Line moved our way |
| --- | ---: | --- | ---: | ---: | ---: |
| 0+ pts | 2,862 | 1426-1436-0 | 49.8% ± 1.8 | -4.9% ± 3.5 | - |
| 1+ pts | 2,204 | 1081-1123-0 | 49.0% ± 2.1 | -6.4% ± 4.0 | - |
| 2+ pts | 1,619 | 774-845-0 | 47.8% ± 2.4 | -8.9% ± 4.6 | - |
| 3+ pts | 1,109 | 531-578-0 | 47.9% ± 2.9 | -8.7% ± 5.6 | - |
| 4+ pts | 702 | 329-373-0 | 46.9% ± 3.7 | -10.7% ± 7.0 | - |
| 6+ pts | 240 | 116-124-0 | 48.3% ± 6.3 | -7.8% ± 12.1 | - |

Moneylines at the closing price when the model's chance beat the break-even by 3+ points: 1,343 bets, 482 won, return per bet -3.7% ± 7.9.

## 4. When the model says 60%, does it happen 60% of the time?

| Model said home wins | Games | Average said | Home actually won |
| --- | ---: | ---: | ---: |
| 0%-20% | 121 | 15.0% | 7.4% ± 4.7 |
| 20%-30% | 228 | 25.5% | 20.6% ± 5.3 |
| 30%-40% | 364 | 35.3% | 33.2% ± 4.8 |
| 40%-50% | 457 | 45.1% | 47.5% ± 4.6 |
| 50%-60% | 510 | 55.1% | 56.9% ± 4.3 |
| 60%-70% | 477 | 64.9% | 66.9% ± 4.2 |
| 70%-80% | 412 | 74.7% | 74.3% ± 4.2 |
| 80%-100% | 296 | 85.6% | 86.5% ± 3.9 |

Spread of misses: margin 14.2 points (the model assumed 14.0), total 18.3 (assumed 18.1). Average lean: margin -0.02, total +0.52.

