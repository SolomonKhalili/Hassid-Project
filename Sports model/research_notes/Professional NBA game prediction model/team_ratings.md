# Team-strength rating systems for predicting NBA game margin and winner

Compiled 19 November 2026 (2026-27 season under way). NBA only. Every number carries the seasons it was measured on. Conventions used below:

- **"Snippet-only"** means the figure came from a search-engine summary because the page itself could not be opened (HTTP 403, paywall, or a retired site). Treat these as lower confidence.
- **"Researcher's calculation"** means I computed the figure from the cited table; the arithmetic is mine, the inputs are the source's.
- FiveThirtyEight's site now redirects to abcnews.com (observed 19 Nov 2026), and the Wayback Machine could not be reached, so FiveThirtyEight's method is cited through mirrors. Its RAPTOR-era methodology page could not be read at all.
- Several of the best recent out-of-sample numbers come from open GitHub projects with walk-forward tests, not peer-reviewed papers. They are labelled as such.
- The web-search budget ran out near the end of the research, so a few follow-up look-ups (noted under Gaps) were not possible.

## 1. How do the main rating methods work, and how do they compare?

### Takeaway
Every mainstream method solves the same equation — margin = home edge + (home strength − away strength) + noise of roughly 11.5–13.5 points SD — and they differ only in how they weight old games, how they shrink toward a prior, and whether they damp blowouts. FiveThirtyEight's Elo (K = 20, 100-Elo home bonus, 75% carry-over, margin multiplier) is the simplest and is insensitive to its parameters; SRS/Massey and ridge-regressed offensive/defensive efficiency are batch versions of the same idea; Kalman, Glicko and Bayesian versions add explicit uncertainty, which mainly matters in the first 10–20 games of a season.

### Cited Findings

#### FiveThirtyEight NBA Elo (published 2015; site retired, so possibly out of date)
- K-factor is 20: "We found the optimal K for the NBA to be 20", chosen to minimise autocorrelation in rating changes. — [FiveThirtyEight, "How We Calculate NBA Elo Ratings" (Goodreads mirror)](https://www.goodreads.com/author_blog_posts/8399806-how-we-calculate-nba-elo-ratings?tab=author)
- Home court is a constant 100 Elo points, which the article equates to "about 3.5 NBA points" (so about 28.6 Elo per point). A home-court value that varied over time was tested and "made almost no difference". — [FiveThirtyEight Elo article (mirror)](https://www.goodreads.com/author_blog_posts/8399806-how-we-calculate-nba-elo-ratings?tab=author)
- Season carry-over: a team keeps three-quarters of its rating and reverts one-quarter toward 1505 (worked example: 0.75 × 1754 + 0.25 × 1505 = 1692). The long-run mean is 1500; a new franchise starts at 1300. — [FiveThirtyEight Elo article (mirror)](https://www.goodreads.com/author_blog_posts/8399806-how-we-calculate-nba-elo-ratings?tab=author)
- Update rule and margin-of-victory multiplier, as replicated by a third party: `R_new = R_old + K_eff × (S − E)`, `E = 1 / (1 + 10^((R_opp − R_team)/400))` with 100 added to the home team, and `K_eff = 20 × (MOV + 3)^0.8 / (7.5 + 0.006 × EloDiff)`. — [Luke Lite, "How to build an NBA Elo rating system"](https://luke-lite.github.io/blog/how-to-build-an-NBA-Elo-rating-system)
- FiveThirtyEight's own WNBA page gives the same multiplier in words (winner's margin + 3, to the power 0.8, divided by 7.5 + 0.006 × EloDiff, with EloDiff adjusted for home court) and states "84 Elo points are worth 3 WNBA points", i.e. 28 Elo per point. That page is WNBA (K = 28, home = 80, 50% carry-over), so only the formula shape and the 28-per-point conversion transfer. — [FiveThirtyEight, "How Our WNBA Predictions Work" (Goodreads mirror, 12 May 2021)](https://www.goodreads.com/author_blog_posts/21295138-how-our-wnba-predictions-work?tab=book)
- Win-probability scale: +100 Elo ≈ 64%, +200 ≈ 75%, +400 ≈ 91%. — [nicidob, "FiveThirtyEight's Elo Ratings and Logistic Regression" (5 Jul 2019)](https://nicidob.github.io/nba_elo)
- Later FiveThirtyEight versions (snippet-only; pages retired): the 2015-16 "CARM-Elo" model used a home bonus of about 92 points, an extra altitude bonus (about 47 points for Denver) and a travel penalty that scaled linearly with distance (about 16 points, roughly 2 percentage points of win probability, for Boston to Los Angeles). — [FiveThirtyEight, "How Our 2015-16 NBA Predictions Work"](https://fivethirtyeight.com/features/how-our-2015-16-nba-predictions-work)
- For 2020-21 FiveThirtyEight cut its home-court adjustment to 75% of its usual level while crowds were restricted, and restored the full value for 2021-22 (snippet-only). — [FiveThirtyEight, "What To Watch For In The 2020-21 NBA Season"](https://fivethirtyeight.com/features/what-to-watch-for-in-the-2020-21-nba-season)
- Elo is insensitive to its settings: K of 20, 35 or 50 all gave sensible results; carry-over of 50%, 75% or 95% all worked; any home bonus from 50 to 150 was fine ("Elo didn't really care"). The author notes Elo has the same form as a logistic regression with one coefficient per team plus a home term, and suggests a home bonus near 70 when home teams win about 60%. — [nicidob (2019)](https://nicidob.github.io/nba_elo)
- An independent retune on 2008-09 to 2011-12 (by log loss) chose K = 20, home = 80 Elo, 25% reversion between seasons, and a margin SD of 11.6 points for converting to spreads. — [DuyThucCao, nba-win-probability-markets (GitHub)](https://github.com/DuyThucCao/nba-win-probability-markets)
- Conflict to ignore: an unsourced third-party page lists a different multiplier, `K × (1 + 0.5·ln(1 + |margin|)) / (1 + 0.5·ln 11)`, and K = 24 for playoffs. It does not match FiveThirtyEight's own pages. — [sports-models-kb](https://sports-models-kb.pages.dev/elo-rating-system-fivethirtyeight)

#### Simple Rating System (SRS)
- Basketball Reference defines SRS as "a rating that takes into account average point differential and strength of schedule", "denominated in points above/below average, where zero is average". — [Basketball Reference glossary](https://www.basketball-reference.com/about/glossary.html)
- SRS = average margin + strength of schedule (2006-07 Spurs: 8.43 margin, −0.08 schedule, SRS 8.35). For the NBA there is no home-court adjustment, no cap on margin, and overtime gets no special treatment. Doug Drinen's stated weaknesses: it weights all games and all points equally and is "easily impressed by blowout victories". — [Sports Reference blog, "SRS Calculation Details" (Mar 2015)](https://www.sports-reference.com/blog/2015/03/srs-calculation-details/)
- Buildable from final scores alone.

#### Massey / least-squares ratings
- Each game gives one equation `r_i − r_j = margin`; stacked as `X r = y` and solved by least squares through `M r = p`, where `M = XᵀX` has games played on the diagonal and minus the number of meetings off the diagonal, and `p` is each team's total point differential. `M` is singular, so one row is replaced by ones (ratings sum to zero). — ["The Massey's method for sport rating: a network science perspective" (arXiv 1701.03363)](https://ar5iv.labs.arxiv.org/html/1701.03363)
- Offence/defence split: with `f` = points scored, `a` = points allowed, `D` = diagonal games matrix and `A` = meetings matrix, solve `(D + A) d = D r − f`, then `o = r − d`. The classical form has no home-advantage term. — [arXiv 1701.03363](https://ar5iv.labs.arxiv.org/html/1701.03363)
- The benchmark academic model adds home court and back-to-back terms: `margin = home + b2b × (B_home − B_away) + θ_home − θ_away + error`, fitted by ordinary least squares with one team's strength fixed at zero. — [Manner, "Modeling and forecasting the outcomes of NBA basketball games" (2015 working paper, later JQAS)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)

#### Opponent-adjusted offensive and defensive efficiency ("adjusted net rating")
- Basketball Reference's schedule-adjusted ratings (Neil Paine, early 2010-11) fit every game with `Home ORtg = LgAvg + 0.5·HCA + HomeOffence + AwayDefence` and `Home DRtg = LgAvg − 0.5·HCA + AwayOffence + HomeDefence`, choosing the values with the lowest squared error. At that date HCA = 4.15 points per 100 possessions and league average = 106.35. No shrinkage or recency weights. — [Basketball Reference blog, "BBR Rankings: 2011 Offense and Defense Ratings, Adjusted for Schedule"](https://www.basketball-reference.com/blog/index6aa2.html?p=8070)
- A 2025-26 open implementation with stated parameters: ridge regression on each game's points per 100 possessions, with a term for each offence, each defence and home court; each team is pulled toward league average "as if it had played 7 average games"; refit for every game date using only earlier games; projected margin = (home net − road net + home court) × expected possessions / 100; a team on a back-to-back loses 1.5 points; home court starts at 2 points and margin SD at 12, both drifting toward the season's values with a weight of 100 games. — [philay3, nba-daily pull request #5 (GitHub)](https://github.com/philay3/nba-daily/pull/5)
- In that project's sweep on 2025-26, shrinkage worth 4 to 7 games gave the lowest average miss (11.4 points); shrinkage worth 30 games gave 11.7. — [philay3, nba-daily PR #5](https://github.com/philay3/nba-daily/pull/5)
- Neil Paine's 2023-24 forecast model kept "schedule-adjusted ratings" from offence and defence per 100 possessions, game location and opponent quality; the regular-season rating was "based on a team's most recent 50 games — including the end of the previous season, in the case of early season ratings — and is regressed to the mean by 15 games". — [Neil Paine, "2023-24 NBA Forecast" (Substack, 18 Jun 2024)](https://neilpaine.substack.com/p/the-messengers-2023-24-nba-forecast)
- Dunks & Threes uses "each team's opponent-adjusted net rating going into the game", started from a preseason projection that fades, as the baseline its own model must beat. — [Dunks & Threes, About](https://dunksandthrees.com/about)
- Needs box scores (possessions are estimated from field-goal attempts, free-throw attempts, offensive rebounds and turnovers). — [Basketball Reference glossary](https://www.basketball-reference.com/about/glossary.html)

#### Kalman-filter / state-space ratings
- Model: `margin = home + b2b·(B_i − B_j) + θ_i,k − θ_j,k + e`, `e ~ N(0, σ²)`; each team's strength follows `θ_k = μ + ρ·θ_(k−1) + η`, `η ~ N(0, σ_η²)`, stepping game to game (not in calendar time), with extra variance `σ_FG²` added at each team's first game of a season. — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- Kalman recursion from the paper's appendix: predicted variance `P⁻ = ρ²·P + σ_η²`; forecast variance `V = P_i⁻ + P_j⁻ + σ²`; update `θ_i ← θ_i⁻ + (P_i⁻/V)·error`, `θ_j ← θ_j⁻ − (P_j⁻/V)·error`; `P_i ← P_i⁻ − (P_i⁻)²/V`. — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- Fitted values, pooled 2006-07 to 2013-14: ρ = 0.9942 per game (SE 0.0012), game noise variance σ² = 129.86 (SD 11.4 points), per-game strength innovation variance 0.0966 (SD 0.31 points), first-game-of-season extra variance 11.38 (SD 3.37 points). Home court 2.70 points (SE 0.12) and back-to-back −1.87 points (SE 0.23); for 2013-14 alone, 2.29 and −1.85. — [Manner (2015), Table 1 and section 3.1.2](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- Within a single season the dynamic model's likelihood was "basically identical" to the static one and the persistence estimate was near zero; a pure random walk had its innovation variance "estimated at zero"; splitting offence and defence "did not yield improvements in fit"; residuals were normal within seasons, so the paper argues a blowout correction is unnecessary. — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- A Bayesian state-space model fitted to the logit of moneyline-implied win probabilities (2006–2016, 11 seasons) estimated NBA team strength persistence of 0.977 week to week and 0.618 season to season. — [Lopez, Matthews & Baumer, "How often does the best team win?" (arXiv 1701.05976)](https://ar5iv.labs.arxiv.org/html/1701.05976)

#### Glicko, TrueSkill and margin-aware Elo variants
- "MOVDA" adds a second term to the Elo update: `R' = R + K·(S − E) + λ·(actual MOV − expected MOV)`, with `expected MOV = α·tanh(β·ΔR) + γ + δ·home`. Fitted values of α, β, γ, δ, λ and K are not reported. — [Beyond Winning: Margin of Victory Relative to Expectation (arXiv 2506.00348)](https://arxiv.org/html/2506.00348v1)
- On 13,619 NBA regular-season games (2013–2023, chronological 70/20/10 split), out-of-sample accuracy and Brier were: standard Elo 62.77% / 0.2274; linear-MOV Elo 63.18% / 0.2282; Glicko-2 63.18% / 0.2264; TrueSkill 62.66% / 0.2294; MOVDA 63.32% / 0.2258. No significance tests; the paper's text and tables disagree slightly. — [arXiv 2506.00348, Table I](https://arxiv.org/html/2506.00348v1)

#### Bayesian hierarchical models
- Attard, Suda & Sammut (2023) fit hierarchical models with separate offensive and defensive abilities for free throws, twos and threes on the 2008-09 season; a negative-binomial scoring model beat Poisson, and a scoring model predicted outcomes better than a direct win-probability model. Results are in-sample, with MCMC convergence problems reported (snippet-only). — [Attard, Suda & Sammut, icSPORTS 2023](https://doi.org/10.5220/0012159100003587)
- The Lopez–Matthews–Baumer model above is the best-documented Bayesian hierarchical/state-space NBA model, but it rates teams from betting prices, not from results. — [arXiv 1701.05976](https://ar5iv.labs.arxiv.org/html/1701.05976)

### Inferences
- SRS and Massey are the same thing: dividing row i of `M r = p` by games played gives `r_i = average margin_i + average opponent rating`, which is the SRS definition. Adding a home-court column and a ridge penalty turns either into the "adjusted net rating" regression. So the designer needs one regression engine, not three.
- From Manner's fitted values I computed the steady-state Kalman gain: about 0.022 rating points per point of forecast error for each team (an effective memory of about 46 games). At a team's first game of the season the gain is about 0.090, falling to 0.051 by game 10, 0.036 by game 20 and 0.026 by game 41. That is the quantitative case for a filter with explicit uncertainty: it moves four times faster in week one than in March, which fixed-K Elo cannot do.
- For comparison, FiveThirtyEight's update moves each of two equal teams about 10.4 Elo (0.37 points at 28 Elo per point) after a 10-point result, versus about 0.22 points for the steady-state Kalman filter and about 0.90 points for the filter in a season opener. Fixed K = 20 is therefore a compromise: too slow in October, somewhat fast in spring.
- FiveThirtyEight's two conversions do not agree with each other or with betting history. Its win formula says a 100-Elo edge wins 64%; its points conversion says 100 Elo is 3.5 points; but 3.5-point closing favourites have won 60.4% since 2003 and it takes about a 4.5-point favourite to win 64.7% (see section 2). If Elo is used, fit the Elo-to-points slope and the points-to-probability link on your own backtest instead of assuming 28 Elo per point.
- A sensible build order for one person: (1) fixed-K Elo as a sanity baseline; (2) ridge regression of per-100 offence and defence with home court, recency weights and a prior as the production rating; (3) only then consider a Kalman filter, since Manner found it forecast no better than the static regression once half a season was available.

### Gaps
- FiveThirtyEight's RAPTOR-era methodology page (home court, back-to-back, travel and altitude values, and the Elo/RAPTOR blend) could not be opened; only the 2015 Elo article and search snippets of older pages were available.
- Neil Paine's current (2025-26) Elo does not publish K, home-court value, margin formula or regression fraction; the detail sits behind a paywall.
- No NBA-specific published fit of Glicko rating-deviation or volatility settings was found. The Glicko documents themselves (glicko.net PDFs) were not read.
- I found no out-of-sample test of a fully Bayesian hierarchical results-based NBA model against a closing line.
- Massey's own site (current method, home-advantage and game-outcome function) returned HTTP 403.
- A University of Helsinki thesis (Poropudas 2011) applies a Kalman filter to 2005–2010 NBA seasons; its results section was not read. — [core.ac.uk](https://core.ac.uk/download/14921159.pdf)

## 2. What out-of-sample accuracy is published for each method, and for the sportsbook closing line?

### Takeaway
Across 2012-13 to 2025-26 the closing line picks about 67.8–68.1% of winners with a Brier score of 0.204–0.207 and log loss of 0.592–0.600, while results-only team ratings land at 65–67%, Brier 0.208–0.217, log loss 0.603–0.624; no public rating has been shown to add information to the close. Margin error has grown with the 3-point era: the line missed by about 9.2 points on average in 2006–2014 but about 10.8 in 2025-26 (SD about 11.7 then, about 12.9–13.5 now), and the best public team-level rating is 0.2–0.6 points worse than the line.

### Cited Findings

#### Winner and probability metrics (all out of sample)

| System | Test seasons | Games | Winners | Brier | Log loss | Source |
|---|---|---|---|---|---|---|
| Closing moneyline, vig removed | 2012-13 to Jan 2023 | 13,486 | 67.8% | 0.2055 | 0.5965 | [DuyThucCao (GitHub)](https://github.com/DuyThucCao/nba-win-probability-markets) |
| Elo (K 20, home 80, 25% reversion, margin multiplier) | same | 13,486 | 65.5% | 0.2146 | 0.6177 | [DuyThucCao](https://github.com/DuyThucCao/nba-win-probability-markets) |
| Logistic (Elo + form + rest) | same | 13,486 | 65.7% | 0.2141 | 0.6166 | [DuyThucCao](https://github.com/DuyThucCao/nba-win-probability-markets) |
| Market + model, stacked | same | 13,486 | 67.7% | 0.2056 | 0.5968 | [DuyThucCao](https://github.com/DuyThucCao/nba-win-probability-markets) |
| Market close | 2020-21 to 2025-26 | 7,764 | 67.8% | 0.2067 | 0.5995 | [julianhr-ops, alttez-predictive (GitHub)](https://github.com/julianhr-ops/alttez-predictive) |
| Margin-of-victory Elo | same | 7,764 | 65.1% | 0.2174 | 0.6240 | [julianhr-ops](https://github.com/julianhr-ops/alttez-predictive) |
| Vanilla Elo (win/loss only) | same | 7,764 | 64.6% | 0.2199 | 0.6295 | [julianhr-ops](https://github.com/julianhr-ops/alttez-predictive) |
| Elo + market blend | same | 7,764 | 67.9% | 0.2070 | 0.6004 | [julianhr-ops](https://github.com/julianhr-ops/alttez-predictive) |
| Constant home-win rate | same | 7,764 | 55.4% | 0.2473 | 0.6878 | [julianhr-ops](https://github.com/julianhr-ops/alttez-predictive) |
| Vegas closing line | 2012-13 to 2025-26 | not stated | 68.1% | 0.2035 | 0.5918 | [nhorto, NBA (GitHub)](https://github.com/nhorto/NBA) |
| Elo + schedule | same | not stated | 66.1% | 0.2126 | 0.6131 | [nhorto](https://github.com/nhorto/NBA) |
| Player-based team strength | same | not stated | 67.0% | 0.2081 | 0.6029 | [nhorto](https://github.com/nhorto/NBA) |
| Gradient boosting with market input | same | not stated | 68.1% | 0.2041 | 0.5933 | [nhorto](https://github.com/nhorto/NBA) |
| Logistic on Elo difference only | 2023-24 to 2025-26, each team's first 10 games excluded | 3,212 | 66.8% | 0.2104 | 0.6082 | [OrenSegal, nba-winning-factors (GitHub)](https://github.com/OrenSegal/nba-winning-factors) |
| Team strength only (Elo, net rating, win %, era) | same | 3,212 | 67.2% | 0.2081 | 0.6029 | [OrenSegal](https://github.com/OrenSegal/nba-winning-factors) |
| Logistic on win % difference only | same | 3,212 | 65.9% | 0.2138 | 0.6154 | [OrenSegal](https://github.com/OrenSegal/nba-winning-factors) |
| Team with better record wins | same | 3,212 | 65.8% | n/a | n/a | [OrenSegal](https://github.com/OrenSegal/nba-winning-factors) |
| Home team always wins | same | 3,212 | 54.3% | 0.2503 | 0.6939 | [OrenSegal](https://github.com/OrenSegal/nba-winning-factors) |
| Gradient boosting / XGBoost, all features | same | 3,212 | 66.3% / 66.1% | 0.2108 / 0.2109 | 0.6098 / 0.6103 | [OrenSegal](https://github.com/OrenSegal/nba-winning-factors) |
| Elo (K 20, home 100, 25% reversion, no margin term) | 2010 to 2015 | 7,641 | 67.2% | 0.208 | 0.603 | [gakoduah, NBA-Game-Prediction-Elo (GitHub)](https://github.com/gakoduah/NBA-Game-Prediction-Elo) |
| FiveThirtyEight Elo forecast | 2010 to 2015 | 7,641 | 67.3% | 0.206 | 0.598 | [gakoduah](https://github.com/gakoduah/NBA-Game-Prediction-Elo) |
| Standard Elo / Glicko-2 / TrueSkill / MOVDA | 2013 to 2023, chronological 70/20/10 split of 13,619 games (which held-out slice is scored is not clearly stated) | not stated | 62.8% / 63.2% / 62.7% / 63.3% | 0.2274 / 0.2264 / 0.2294 / 0.2258 | n/a | [arXiv 2506.00348](https://arxiv.org/html/2506.00348v1) |

- The closing line had a lower Brier score than the Elo/logistic model "in every test season" (2012-13 to 2022-23). A forecast-encompassing regression put a weight of 0.97 (SE 0.045) on the market and −0.001 (SE 0.047, p = 0.98) on the model. — [DuyThucCao](https://github.com/DuyThucCao/nba-win-probability-markets)
- 2020-21 to 2025-26: "NBA Elo does not beat the market close in any test season"; in the blend the Elo coefficient is about 0 and the market coefficient about 1.03. Margin-of-victory Elo beat win/loss Elo by 0.0055 log loss (95% interval 0.0032 to 0.0078) and trailed the close by 0.0245 (0.0202 to 0.0288). — [julianhr-ops](https://github.com/julianhr-ops/alttez-predictive)
- Accuracy "tops out near 66 to 67%" for models built without betting lines (2023-24 to 2025-26), and differences under about 1.5 percentage points cannot be separated from noise on 3,212 games. Tree models did not beat logistic regression. — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors)
- A FiveThirtyEight-style Elo replication (K 20, home 100, 75% carry-over, margin multiplier) picked 65.3% of regular-season winners "over the past 10 seasons" (exact seasons not given). — [Luke Lite](https://luke-lite.github.io/blog/how-to-build-an-NBA-Elo-rating-system)
- Elo variants scored 66.4–68% on games since 2010, with a rolling logistic regression (fixed home edge of 75 Elo, 30-game window) at 66.8% against 66.4% for FiveThirtyEight's Elo on the same games. — [nicidob (2019)](https://nicidob.github.io/nba_elo)
- A regularised logistic regression on roster archetypes, trailing 90-day win % and rest/travel picked 65.8% of 2015-16 games from 20 Nov 2015 (AUROC 0.744). — [Stitch Fix, "Elastic NBA Rankings" (2016)](https://multithreaded.stitchfix.com/blog/2016/11/22/nba-rankings)
- ESPN claimed in 2015 that BPI favourites "have won over 72 percent of NBA games"; no sample or seasons are given. Possibly out of date and not independently checked. — [ESPN, "What is ESPN's NBA Basketball Power Index?" (27 Oct 2015)](https://www.espn.ph/nba/story/_/id/13984129/what-espn-nba-basketball-power-index)
- Conflict: one hobby site quotes "Vegas closing lines sit around 73% / 0.195 Brier" and "FiveThirtyEight's Elo ~67% / 0.210". The 73% figure is not supported by any of the measured datasets above (67.8–68.1%). — [seanrmoran.com](https://www.seanrmoran.com/nbaplayoffpredictor/)
- Other favourite win rates (snippet-only): favourites won 68% of regular-season games "over the last 10 seasons" per a BetMGM article, and closing favourites won about 68.7% in 2025-26 per a Kaggle dataset description. — [BetMGM blog](https://sports.betmgm.com/en/blog/nba/nba-picks-today-betting-predictions-spreads-over-under-totals-prop-bets-bm16/); [Kaggle, NBA 2025-26 Closing Lines](https://www.kaggle.com/datasets/minmaxer/nba-closing-lines-ats-2025-26)
- A 2026 peer-reviewed paper that feeds closing odds into its model reports accuracy 0.688, Brier 0.199 and log loss 0.583 on its 2024 test set (snippet-only). — [MDPI Information 17(1):56](https://doi.org/10.3390/info17010056)

#### Margin metrics (all out of sample)

| System | Test seasons | Games | Mean absolute error | RMSE | Winners | Source |
|---|---|---|---|---|---|---|
| Las Vegas opening spread | 2006-07 to 2013-14, second half of each regular season | about 4,800 (my count: 615 per normal season, 495 in 2011-12) | 9.17 | 11.73 (MSE 137.49) | 69.2% | [Manner (2015), Table 3](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf) |
| Least-squares team strength + home + back-to-back | same | same | 9.36 | 11.93 (MSE 142.21) | 68.2% | [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf) |
| Same with team-specific variances | same | same | 9.36 | 11.93 (MSE 142.25) | 68.1% | [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf) |
| Kalman state-space model | same | same | 9.38 | 11.96 (MSE 143.13) | 68.4% | [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf) |
| 50/50 average of least-squares model and spread | same | same | 9.20 | 11.74 (MSE 137.93) | 69.3% | [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf) |
| Opening spread, playoffs | 2006-07 to 2013-14 | not stated | 9.50 | 12.20 (MSE 148.96) | 68.0% | [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf) |
| Kalman model, playoffs | same | not stated | 9.68 | 12.28 (MSE 150.85) | 68.6% | [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf) |
| Dunks & Threes model (player EPM × minutes, injuries), live | 2024-25 to 2025-26 | 2,643 | 11.0 | n/a | 68.4% | [Dunks & Threes, About](https://dunksandthrees.com/about) |
| Baseline: opponent-adjusted net rating with fading preseason prior, live | same | 2,643 | 11.4 | n/a | 67.5% | [Dunks & Threes](https://dunksandthrees.com/about) |
| Dunks & Threes model, backtest | 2005-06 to 2023-24 | 24,425 | 9.6 | n/a | 67.8% | [Dunks & Threes](https://dunksandthrees.com/about) |
| Baseline, backtest | same | 24,425 | 9.9 | n/a | 66.3% | [Dunks & Threes](https://dunksandthrees.com/about) |
| ESPN pregame spread (not confirmed as the closing number) | 2025-26 | not stated | 10.8 | n/a | n/a | [philay3, nba-daily PR #5](https://github.com/philay3/nba-daily/pull/5) |
| Ridge offence/defence per-100 rating, 7-game shrinkage | 2025-26 | not stated | 11.4 | n/a | 580-638-12 against the spread | [philay3](https://github.com/philay3/nba-daily/pull/5) |

- RMSE values in the Manner rows are my square roots of the paper's reported mean squared errors (researcher's calculation). Manner's model rows are significantly worse than the spread (excluded from the 95% model confidence set); the 50/50 combinations are not. — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- "Errors are larger in recent seasons because single games have become harder to predict." — [Dunks & Threes](https://dunksandthrees.com/about)
- Estimates of the SD of final margin around the forecast: 11.6 points fitted on 2008-09 to 2011-12 — [DuyThucCao](https://github.com/DuyThucCao/nba-win-probability-markets); in-sample residual variance of about 130 (SD 11.4) for 2006–2014 — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf); "near 12 points" around the point spread — [Wayne Winston (4 Mar 2018)](https://www.goodreads.com/author_blog_posts/16483561-why-is-standard-deviation-of-nba-scores-about-point-spread-12-points); 13.47 in a 2015 power-rating fit — [Probabilis blog (Jul 2015)](https://probabilis.blogspot.com/2015/07/home-field-advantage-and-standard.html); and 12.9 as the scale that maps sportsbooks' own moneylines to their spreads in 2024-25 and 2025-26 (ESPN BET and DraftKings) — [Dave356w, nba-matchups PR #59 (GitHub)](https://github.com/Dave356w/nba-matchups/pull/59).
- Against the spread: FiveThirtyEight's CARM-Elo spreads went 559-560-17 against Las Vegas in 2016-17 (1,136 games where the two differed), "indistinguishable from… flipping a coin". — [Stanford Sports Analytics (Jun 2017)](https://stanfordsportsanalytics.wordpress.com/2017/06/18/in-search-of-a-winning-strategy-comparing-fivethirtyeight-coms-carm-elo-predictions-to-las-vegas-point-spreads/)
- A 2024-25 and 2025-26 backtest found the line moves 0.65 ± 0.13 and 0.56 ± 0.14 points toward the model's side between open and close (about a quarter of the opening edge); the model's side covered 53.0% / 52.3% at the opening number but 48.2% / 49.3% at the close. — [Dave356w, nba-matchups PR #59](https://github.com/Dave356w/nba-matchups/pull/59)
- An old forum measurement put closing-spread mean absolute error at about 9.29 points against 9.32 for openers (late 2000s, amateur, snippet-only). — [Sportsbook Review forum](https://www.sportsbookreview.com/forum/handicapper-think-tank/566389-nba-modeling)

#### Straight-up record of favourites by closing spread ("since 2003")

| Closing spread | Games | Favourite's record | Win % |
|---|---|---|---|
| −1 | 1,239 | 629-610 | 50.8% |
| −2 | 1,486 | 802-684 | 54.0% |
| −3 | 1,525 | 868-657 | 56.9% |
| −3.5 | 1,733 | 1046-687 | 60.4% |
| −4.5 | 1,780 | 1151-629 | 64.7% |
| −5.5 | 1,580 | 1038-542 | 65.7% |
| −6.5 | 1,578 | 1124-454 | 71.2% |
| −7.5 | 1,329 | 971-358 | 73.1% |
| −8.5 | 1,095 | 859-236 | 78.4% |
| −9.5 | 903 | 717-186 | 79.4% |
| −10.5 | 672 | 569-103 | 84.7% |
| −12.5 | 383 | 339-44 | 88.5% |
| −14.5 | 199 | 180-19 | 90.5% |

- Source for the table: [TeamRankings/BetIQ, NBA win-loss records by closing spread](https://betiq.teamrankings.com/nba/betting-trends/by-closing-line/win-loss-and-spread-records/). The page's filter reads "Since 2003"; exact end date not shown.

### Inferences
- Realistic targets for a one-person, results-and-box-score model in the current era: 66–67.5% winners, Brier 0.208–0.212, log loss 0.603–0.612, and a mean absolute margin error of about 11.2–11.5 points, against about 68%, 0.204–0.207, 0.592–0.600 and about 10.8 for the closing line. The best public player-based model (11.0 over 2024-25 and 2025-26) appears to sit only a few tenths of a point behind the line (10.8 in 2025-26), although the two samples are not the same games.
- Under a normal distribution, mean absolute error = 0.80 × SD. That turns the 9.17 (2006–14) and 10.8 (2025-26) line errors into SDs of about 11.5 and 13.5, consistent with the independent SD estimates (11.6 in 2008–12; 12.9 in 2024–26). Use an SD of about 13, not the textbook 12, when converting a 2026-27 margin into a win probability or pricing alternate spreads, and re-estimate it every season.
- Old accuracy figures flatter today's models: 67% in 2010–2015 was earned when the home team won 59.5% of the time; with home teams at 54–55% the same method scores 65–66%. Compare only within the same seasons.
- Margin-based updates are worth about 0.5 percentage points of accuracy and 0.005 log loss over win/loss-only Elo; adding net rating and win % to Elo is worth about another 0.005 log loss; adding the market is worth a further 0.01–0.025. The remaining gap to the close is mostly injury and line-up information that team-level ratings do not see (the player-based Dunks & Threes model beats the team-level baseline by 0.3–0.4 points and about 1 percentage point).
- The closing-spread table suggests a single-SD normal link is imperfect: against Φ(spread/12), favourites of 1–4 points have won about 1–4 percentage points less often and favourites of 9 or more points about 1–4 points more often. Each row carries about ±1.2–2.5 points of sampling error and the data pool 2003 onward, so this needs checking on recent seasons, but it argues for fitting the spread-to-win-probability link empirically (for example a logistic or spline on your own predicted margins) before pricing moneylines.

### Gaps
- I found no published season-by-season mean absolute error or RMSE of the closing spread for 2018-19 onward. The best recent figures are one season from one hobby project (10.8, ESPN pregame spread, 2025-26) and the moneyline-to-spread scale of 12.9. This should be computed directly from a free closing-line archive (the hoopR-nba-data repository carries ESPN-relayed closing lines; the Sportsbook Reviews Online archive covers 2007-08 to January 2023, both as used by the GitHub projects above).
- ThePredictionTracker (which scores Sagarin, Massey and others against the line) and Massey's site both returned HTTP 403, so there are no like-for-like numbers for Massey or Sagarin.
- No out-of-sample margin error was found for SRS as such; the Manner least-squares rows are the closest equivalent (SRS plus home court and back-to-back).
- FiveThirtyEight's own published Brier scores for its RAPTOR-era NBA forecasts could not be retrieved.
- Season-by-season favourite win rates were not found; the search budget ran out before a planned look-up.

## 3. Best practice for recency weighting, regression to the mean between seasons, and preseason priors. How many games before this season's results outweigh the prior?

### Takeaway
Independent sources converge on an effective memory of roughly 45–50 games within a season (a 30-game half-life, a Kalman gain near 2% per game, Neil Paine's 50-game window), a carry-over of 62–75% of last season's rating, and betting-market win totals as the best preseason prior. This season's results outweigh the prior after about 7–15 games if the prior is league average or last season's rating, but not until about game 18 (point differential) or game 25 (win-loss record) if the prior is the Vegas win total.

### Cited Findings

#### Recency weighting inside a season
- In a 26-season screen (2000-01 to 2025-26), the best half-life for a recency-weighted net rating was "about 30 games" (leave-one-season-out log loss 0.6096); remembering only 2–3 games gave 0.639; Elo with carry-over across seasons was the best memory model at 0.6074. — [OrenSegal, nba-winning-factors (GitHub)](https://github.com/OrenSegal/nba-winning-factors)
- Neil Paine's 2023-24 model: regular-season rating from "a team's most recent 50 games — including the end of the previous season… regressed to the mean by 15 games"; playoff rating from the most recent 110 games with "no regression-to-the-mean factor, though postseason games receive triple weight". — [Neil Paine (18 Jun 2024)](https://neilpaine.substack.com/p/the-messengers-2023-24-nba-forecast)
- Neil Paine's 2025-26 model runs two Elo tracks: the regular-season track "react[s] a bit more quickly" and gives extra weight to recent games; the playoff track "updates more heavily from postseason games and moves more slowly during the regular season". No parameter values are published. — [Neil Paine, "2025-26 NBA Elo Forecast and Player Ratings" (14 Jun 2026)](https://neilpaine.substack.com/p/2025-26-nba-elo-forecast-and-player)
- Team strength barely drifts inside a season: fitted per-game persistence 0.9942 and per-game innovation SD 0.31 points (2006-07 to 2013-14); a test for autocorrelation in the static model's residuals was not rejected in any season, which the paper reads as no "hot hand" for teams. — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- Week-to-week persistence of market-implied team strength is 0.977 (2006–2016). — [Lopez, Matthews & Baumer (arXiv 1701.05976)](https://ar5iv.labs.arxiv.org/html/1701.05976)
- When rating teams from point spreads, Inpredictable weights each past game by `1 / (games ago + 1.5)` (most recent game 2/3, the one before 2/5), a constant chosen to minimise the error in predicting future spreads; its "credibility coefficient" for the NBA is 20%, meaning the market's next spread moves by about 20% of a game's deviation from the previous spread. — [Inpredictable, Methodology](https://www.inpredictable.com/p/methodology.html)
- FiveThirtyEight chose K = 20 to minimise autocorrelation in rating changes. — [FiveThirtyEight Elo article (mirror)](https://www.goodreads.com/author_blog_posts/8399806-how-we-calculate-nba-elo-ratings?tab=author)
- One industry model discounts prior-season games "by a factor of 4" before fitting. — [Stitch Fix (2016)](https://multithreaded.stitchfix.com/blog/2016/11/22/nba-rankings)

#### Regression to the mean between seasons
- FiveThirtyEight: keep 75%, revert 25% toward 1505. — [FiveThirtyEight Elo article (mirror)](https://www.goodreads.com/author_blog_posts/8399806-how-we-calculate-nba-elo-ratings?tab=author)
- 25% reversion again in an independent Elo tuned on 2008-09 to 2011-12; 50%, 75% and 95% retention all "worked" in another test. — [DuyThucCao](https://github.com/DuyThucCao/nba-win-probability-markets); [nicidob (2019)](https://nicidob.github.io/nba_elo)
- Season-to-season persistence of market-implied strength: 0.618 (SD 0.04), 2006–2016. — [Lopez, Matthews & Baumer](https://ar5iv.labs.arxiv.org/html/1701.05976)
- State-space fit: an extra variance of 11.38 (SD 3.37 points) is added to each team's strength at its first game of a new season, on top of the per-game persistence of 0.9942 (2006-07 to 2013-14). — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- Using multi-season data in the dynamic model "lead to significantly worse results" for forecasting the second half of a season than using that season alone. — [Manner (2015), section 3.2](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf)
- In a classifier on games since 2010, standardised weights were 0.42 on season net-rating difference, 0.29 on previous-year win % difference, 0.13 on recent net-rating difference and 0.03 on current win % difference, so last season's record keeps real weight all year. — [nicidob (2019)](https://nicidob.github.io/nba_elo)
- Paine: "Each offseason, ratings are partially regressed toward the league average before the new season begins" (fraction not stated). — [Neil Paine (14 Jun 2026)](https://neilpaine.substack.com/p/2025-26-nba-elo-forecast-and-player)

#### Preseason priors and when the season overtakes them
- "Vegas projections alone could predict 56 percent of teams' final records" (R-squared). "After 10 games, a team's record offers 37 percent predictiveness for its performance over the rest of the regular season" against 54 percent for the Vegas projection. "Point differential catches up to Vegas projections by Game 17" and overtakes "by Game 18"; "by Game 25, a team's actual early-season record becomes more predictive than its Vegas projection going forward." Sample: all 82-game seasons this century, 565 team-seasons. — [The Ringer (10 Nov 2021)](https://www.theringer.com/2021/11/10/nba/early-nba-standings-wizards-warriors-cavaliers)
- Reverse-engineering betting lines, Andrew Gelman's blog finds that after 30 games the market's estimate is about 0.65 × preseason line + 0.35 × observed record, making the preseason line worth about 56 games of win-loss information (snippet-only; page returned 403). — [Statistical Modeling blog (26 Dec 2025)](https://statmodeling.stat.columbia.edu/2025/12/26/how-much-of-an-nba-teams-won-loss-record-is-from-skill-and-how-much-is-luck/)
- TeamRankings builds NBA preseason ratings by regressing "what blend of those win totals has historically best predicted the actual number of wins" across betting markets, major media sites and the APBR forum contest, then back-solving team ratings until projected wins match. Its earlier team-level statistical projections "were less accurate than the betting market alone". Possibly out of date (article dated 12 Oct 2022). — [TeamRankings/BetIQ, "How TeamRankings Makes NBA Preseason Rankings"](https://betiq.teamrankings.com/articles/preseason-rankings-ratings-explain/)
- TeamRankings says using preseason ratings improves accuracy and that "the impact of a team's preseason rating decreases over time"; no schedule is given (snippet-only). — [TeamRankings NBA team rankings pages](https://www.teamrankings.com/nba/team/oklahoma-city-thunder/rankings)
- ESPN BPI "incorporates preseason expectations" from Vegas expected win totals and the prior year's performance. Possibly out of date (2015). — [ESPN (27 Oct 2015)](https://www.espn.ph/nba/story/_/id/13984129/what-espn-nba-basketball-power-index)
- Neil Paine blends in Elo values converted from preseason odds: "over/unders for regular-season Elo; title odds for the playoffs". — [Neil Paine (14 Jun 2026)](https://neilpaine.substack.com/p/2025-26-nba-elo-forecast-and-player)
- Dunks & Threes' team-level baseline "starts from a preseason projection that fades as the season's results come in". — [Dunks & Threes, About](https://dunksandthrees.com/about)
- Ridge shrinkage worth 4–7 games of league-average play minimised margin error in 2025-26 (11.4 points); 30 games was worse (11.7). — [philay3, nba-daily PR #5](https://github.com/philay3/nba-daily/pull/5)
- Roster-continuity style prior (snippet-only): a public 2026-27 win-total projection starts from last season's point differential and adjusts for roster turnover and age, with weights chosen on 2015-16 to 2020-21 and backtested over five seasons. — [mcgahranjt, 2026-27 NBA Win Projections (GitHub)](https://github.com/mcgahranjt/2026-27-NBA-Win-Projections)
- Evaluation studies often sidestep the cold-start problem by dropping each team's first 10 games. — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors)
- Spread of team strength, for sizing a prior: the SD across the 30 teams of season scoring margin was 4.8 (2018-19), 5.0 (2019-20 to 11 Mar), 4.9 (2020-21), 4.8 (2021-22), 3.9 (2022-23), 5.5 (2023-24), 5.9 (2024-25) and 6.1 (2025-26) points per game (researcher's calculation). — [TeamRankings, average scoring margin (table for 2025-26; other seasons via the date parameter)](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2026-04-13)
- Converting wins to points: Basketball Reference's Pythagorean formula uses an exponent of 14, `W = G × PTS^14 / (PTS^14 + OppPTS^14)`, and notes 16.5 as "a common choice" with an RMSE of 3.48 wins. — [Basketball Reference glossary](https://www.basketball-reference.com/about/glossary.html)

### Inferences
- Three independent estimates of in-season memory agree: a 30-game half-life is an e-folding length of 43 games; Manner's parameters give a steady-state Kalman gain of 0.0216, i.e. about 46 games; Paine uses a hard 50-game window. An exponential weight of about 0.977 per game (half-life 30 games) is a defensible default. Much shorter memories are clearly worse.
- Two independent estimates of year-to-year carry-over agree as well: 0.9942 per game compounds to 0.62 over 82 games, the same as the 0.618 season-to-season persistence of market-implied strength. FiveThirtyEight's 0.75 is on the high side. A reasonable prior for a team's new-season rating is 0.62–0.75 × last season's final rating with an SD of about 3.4–3.8 points (Manner's first-game variance; also what a 5-point spread of true strength and a 0.65 correlation would imply).
- "How many games until the season outweighs the prior" depends on the prior. (a) League-average prior: 7 games (ridge sweep, 2025-26) to 15 games (Paine). (b) Last season's carried-over rating: about 10 games, from Manner's parameters (the posterior variance falls to half its opening value after 10–11 games). (c) Vegas win total: about 18 games for point differential and 25 for win-loss record (The Ringer); Gelman's 56 games is for win-loss record only and is unverified. A practical rule: treat a market-based preseason rating as worth about 18 games of this season's opponent-adjusted margin, so the season's own data get weight n / (n + 18): 36% after 10 games, 53% after 20, 69% after 41.
- Converting a win total to a rating: differentiating the Pythagorean formula gives wins per point of margin = 82 × exponent / (4 × points per game). At roughly 115 points per team per game that is 2.5 wins per point with exponent 14 and 2.9 with 16.5, so rating ≈ (win total − 41) / 2.5 to 2.9. (The 115 figure is my assumption for the current scoring level, not a sourced number.)
- A team-level rating cannot see roster change, which is why every strong public system now takes its preseason prior from the market or from player projections. For a free-data project, the market win total is the cheapest high-quality prior; last season's rating regressed 25–38% is the fallback.

### Gaps
- No public study reports the optimal half-life or shrinkage separately for 2018-19 onward; the 30-game half-life pools 26 seasons and the 4–7 game shrinkage is one season of one hobby project.
- No source publishes measured weights for a roster-continuity adjustment (for example returning-minutes share) in the NBA; the one project found was seen as a snippet only.
- Gelman's figures could not be verified because the page blocked automated reading.
- Neither Paine nor TeamRankings nor ESPN publishes how fast their preseason prior decays.

## 4. What is home-court advantage worth in the 2020s NBA, and how should neutral sites and team-specific effects be treated?

### Takeaway
League-average home advantage fell from about +2.7 points and 59% wins in 2018-19 to about +1.6 to +2.1 points and 54–55.5% in 2023-24 through 2025-26, with a COVID low of +0.9 in 2020-21 and a one-season rebound to +2.5 (58%) in 2022-23. A starting value of about +1.8 to +2.0 points for 2026-27, zero at neutral sites, and no more than about +1 extra for Denver and Utah fits the evidence; single-season team-specific values are mostly noise.

### Cited Findings

#### Season-by-season league home advantage (researcher's calculation from TeamRankings team tables)

| Season | Home scoring margin, points per game | Home win % | Note |
|---|---|---|---|
| 2018-19 | +2.72 | 59.2% | |
| 2019-20, through 11 Mar 2020 (pre-bubble) | +2.28 | 55.6% | unweighted team average; teams had unequal home games |
| 2020-21 | +0.94 | 54.3% | 72-game season, empty or restricted arenas |
| 2021-22 | +1.73 | 54.4% | |
| 2022-23 | +2.54 | 58.1% | |
| 2023-24 | +2.12 | 54.3% | |
| 2024-25 | +1.61 | 54.3% | |
| 2025-26 | +1.74 | 55.5% | |
| 2026-27, through about 18 Nov 2026 | about +1.0 to +1.3 | not computed | roughly 225 games; standard error near 0.9 points; do not rely on it |

- Method: simple mean of the 30 teams' "Home" column (and, as a cross-check, minus the mean of the "Away" column, which matched to within 0.1) in TeamRankings' average-scoring-margin and win-percentage tables dated at the end of each regular season. The tables may count in-season-tournament and neutral-site games under the designated home team. — [TeamRankings, average scoring margin, 2018-19](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2019-04-11); [2019-20](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2020-03-12); [2020-21](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2021-05-17); [2021-22](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2022-04-11); [2022-23](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2023-04-10); [2023-24](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2024-04-15); [2024-25](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2025-04-14); [2025-26](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2026-04-13); [2026-27 to date](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2026-11-19); [win percentage tables, same dates](https://www.teamrankings.com/nba/stat/win-pct-all-games?date=2026-04-13)
- Independent checks on the win rates: home teams went 668-562 (54.3%) in 2023-24, "the worst home-court mark in league history". — [AP via News4Jax (14 Apr 2024)](https://www.news4jax.com/sports/2024/04/14/inside-the-nba-numbers-lots-of-comebacks-no-home-court-edge-3s-went-up-scoring-went-down/)
- The home team "won 60% of its regular-season games from 2000-13", about 58% from 2014 to the end of the decade, a low of 54% in 2020-21, a "spike" to 58% in 2022-23, and 54% otherwise through early 2024-25. — [Yahoo Sports, Ben Rohrbach (8 Nov 2024)](https://sports.yahoo.com/fact-or-fiction-is-home-court-advantage-in-the-nbas-regular-season-dead-194958543.html)
- Era averages from 52,349 games (stats.nba.com via nba_api): 1983–92 65.8% and +4.9 points; 1992–98 59.9%, +3.3; 1999–04 61.0%, +3.5; 2005–13 60.1%, +3.1; 2014–19 58.3%, +2.6; 2020–26 55.1%, +1.8. Pre-shutdown 2019-20 was 55.1%; 2020-21 54.4%; 2024-25 54.4%. — [Sparkle Technologies blog (16 Apr 2026)](https://sparkletechnologies.com/blog/nba-disappearing-home-court-advantage)
- That analysis attributes the decline mainly to 3-point volume (correlation of −0.88 between league 3-point attempts and home win rate), puts load management and back-to-backs at about 15–20% of it, and rules out travel distance, time zones and pace; it notes the home win rate was already about 55% before COVID. Blog analysis, not peer reviewed. — [Sparkle Technologies blog](https://sparkletechnologies.com/blog/nba-disappearing-home-court-advantage)
- Pooled 2020-21 to 2025-26, a constant home-win forecast is right 55.4% of the time; pooled 2023-24 to 2025-26, 54.3%. Home win rate was "about 60% through 2018-19 and 54 to 58% from 2019-20 on". — [julianhr-ops](https://github.com/julianhr-ops/alttez-predictive); [OrenSegal](https://github.com/OrenSegal/nba-winning-factors)

#### What ratings and the market use
- Schedule- and injury-adjusted study of 2022-23 through 11 Feb 2025: league home advantage 2.08 points; "the average closing line implies about 2.05 points"; Sagarin's ratings put it at "about 3.0"; the author uses 2.1. — [VSiN, Steve Makinen (12 Feb 2025)](https://vsin.com/nba/nba-true-home-and-road-court-advantage/)
- Betting lines: "since 1995 the average home team has been favored by 3.1 points", at least 2.2 in each of the previous 25 seasons, but "just 1.6 points on average" over the first five weeks of a season played largely without fans (apparently 2020-21; the article does not name the season), when home teams were 122-115 straight up and 106-127-4 against the spread. — [theScore](https://www.thescore.com/news/2099499)
- Fitted home terms in rating models: 2.70 points for 2006-07 to 2013-14 and 2.29 for 2013-14 alone — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf); 2.41 in a 2015 power-rating fit — [Probabilis blog](https://probabilis.blogspot.com/2015/07/home-field-advantage-and-standard.html); 2.7 on average over 2000-01 to 2025-26 after controlling for Elo — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors); 4.15 points per 100 possessions early in 2010-11 — [Basketball Reference blog](https://www.basketball-reference.com/blog/index6aa2.html?p=8070).
- FiveThirtyEight used a constant 100 Elo (about 3.5 points) in 2015, about 92 in 2015-16, and 75% of its usual value in 2020-21 (the last two snippet-only). Out of date. — [FiveThirtyEight Elo article (mirror)](https://www.goodreads.com/author_blog_posts/8399806-how-we-calculate-nba-elo-ratings?tab=author); [FiveThirtyEight 2015-16](https://fivethirtyeight.com/features/how-our-2015-16-nba-predictions-work); [FiveThirtyEight 2020-21](https://fivethirtyeight.com/features/what-to-watch-for-in-the-2020-21-nba-season)
- An open 2025-26 model starts home court at 2 points and lets it drift toward the season's observed value "with a weight of 100 games". — [philay3, nba-daily PR #5](https://github.com/philay3/nba-daily/pull/5)
- Modelling the change in home advantage across eras was one of only two feature families that clearly improved out-of-sample log loss (by 0.0019, interval 0.0008–0.0030, when removed); a single home intercept fitted on older seasons "overstates recent home advantage". — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors)
- Fans: a 2024 study covering 2014-15 to 2021-22 found games with fans raise the home team's score by 1.69 points relative to games without (snippet-only, via a systematic review). — [MDPI systematic review of home-court advantage](https://www.mdpi.com/2411-5142/9/4/192)

#### Team-specific home advantage and altitude
- By franchise, in points after controlling for Elo, 2000-01 to 2025-26 (league average 2.7, standard error about 0.4 each): Denver +4.0, Utah +3.7, Golden State +3.7, Brooklyn +1.7. — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors)
- Yet in the same project "travel, time zones, altitude, road trips" were "indistinguishable from zero out of sample", and altitude "clears the in-sample Bonferroni bar but adds nothing on unseen seasons". — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors)
- Market-based estimate, 2006–2016: a league-average team has a 62.0% chance at home against a like-calibre opponent; Denver is highest at 66.1% (worth 1.68 extra wins a season against a league-average home edge), Utah second, Brooklyn lowest at 60%. Out of date for levels, still informative for ordering. — [Lopez, Matthews & Baumer](https://ar5iv.labs.arxiv.org/html/1701.05976)
- Schedule-adjusted home ratings for 2022-23 to 11 Feb 2025: Oklahoma City +7.0, Denver +4.6, Memphis +4.0, Orlando +3.9, Boston +3.8; lowest Miami −0.2, Sacramento and Washington +0.3; Denver's road rating was −4.9 (tied worst). No Utah figure given. — [VSiN (12 Feb 2025)](https://vsin.com/nba/nba-true-home-and-road-court-advantage/)
- Half the gap between a team's home and away scoring margin, by season from 2018-19 to 2025-26 (researcher's calculation): Denver 6.6, 3.1, 1.6, 0.1, 6.5, 4.6, 1.8, 0.5 (mean 3.1); Utah 2.6, 1.2, 4.0, 3.9, 2.1, 6.6, 0.5, 3.2 (mean 3.0); league 2.7, 2.2, 0.9, 1.7, 2.5, 2.1, 1.6, 1.7 (mean 1.95). The SD of this quantity across the 30 teams in a single season was 1.2–2.1 points. — [TeamRankings, average scoring margin tables (date parameter as above)](https://www.teamrankings.com/nba/stat/average-scoring-margin?date=2025-04-14)
- Per-team home advantage estimated from rolling logistic regressions was "highly variable", which led that author to fix a single league value. — [nicidob (2019)](https://nicidob.github.io/nba_elo)
- FiveThirtyEight's 2015-16 model gave Denver roughly 47 extra Elo points for altitude (snippet-only). — [FiveThirtyEight 2015-16](https://fivethirtyeight.com/features/how-our-2015-16-nba-predictions-work)

#### Neutral sites and rest
- Practice in the sources: one large study simply drops neutral-site games (31,245 games remain for 2000-01 to 2025-26); TeamRankings defines its rating as the expected margin against an average opponent "on a neutral court"; Sports Reference's NBA SRS makes "no adjustments" for home court at all. — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors); [TeamRankings/BetIQ](https://betiq.teamrankings.com/articles/preseason-rankings-ratings-explain/); [Sports Reference blog](https://www.sports-reference.com/blog/2015/03/srs-calculation-details/)
- Rest effects sit alongside home court: a back-to-back costs 1.87 points (2006-07 to 2013-14) — [Manner (2015)](https://static.uni-graz.at/fileadmin/_Persoenliche_Webseite/manner_hans/Publikationen/NBA_revision2.pdf); 1.5 points in a 2025-26 open model — [philay3](https://github.com/philay3/nba-daily/pull/5); and "rest and schedule load" was the other feature family that clearly helped out of sample (0.0032 log loss, interval 0.0010–0.0055) — [OrenSegal](https://github.com/OrenSegal/nba-winning-factors).

### Inferences
- Starting value for 2026-27: the five post-COVID seasons (2021-22 to 2025-26) average +1.95 points and the last three +1.82. One season's league figure carries a standard error of about 0.4 points (about 13–14 points of game SD over 1,230 games), so 2022-23's +2.54 is not strong evidence of a real rebound. Use about +1.8 to +2.0 and let it update slowly; do not use the 2026-27 figure to date.
- In Elo units, 2.0 points is about 56 Elo at 28 Elo per point, a little over half of FiveThirtyEight's 100. Using 100 today would overstate home teams by about 1.5 points.
- Fit home advantage as its own time-varying parameter (per season, or a rolling multi-season average) rather than one constant over the whole history; the one out-of-sample test available says this matters.
- Team-specific values: with about 41 home and 41 away games, the sampling error of a single-season home/away half-gap is about 1.4 points, roughly the size of the observed spread across teams (1.2–2.1), so one season says almost nothing. Over long samples Denver sits about +1.1 to +1.3 and Utah about +1.0 above the league. A fixed +1.0 for both (so about +2.8 to +3.0 total in 2026-27) and zero for everyone else is the defensible choice; Oklahoma City's +7.0 in VSiN's 2.5-season sample is far more likely to be mostly noise and team quality than a durable edge.
- Neutral sites: set the home term to zero for NBA Cup semi-finals and final, international games and the 2020 bubble. When fitting history, give 2020-21 its own low home value (about +0.9) rather than letting it drag down or be distorted by neighbouring seasons.
- Home win rate and margin are consistent with each other: +1.6 to +2.1 points on a 13-point SD implies 55–56% home wins, close to the observed 54.3–55.5%.

### Gaps
- No published 2026-27 estimate exists yet; my to-date figure is unweighted and too noisy to use.
- I found no out-of-sample test from the 2020s showing that team-specific home advantage (beyond a league value) improves margin prediction; the only test found says altitude features add nothing on unseen seasons.
- No source quantified how the designated "home" team performs in NBA Cup neutral-site games or international games.
- Betting-market-implied home advantage by season (average closing spread of home teams) was found only for two windows (about 1.6 early in 2020-21; about 2.05 for 2022-23 to February 2025).

