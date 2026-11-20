# Player-impact metrics and lineup / injury adjustment for NBA game prediction

_Research notes. All live-site checks were made on 19 November 2026 (2026-27 season under way). Ratings are in points per 100 possessions relative to an average player unless stated. Items marked **[own calculation]** were computed for these notes from the linked public data files; they are not published figures and should be re-derived before being relied on. Web search capacity ran out late in the work, so a few items listed under "Gaps" could not be chased further._

## 1. How are the leading player-impact metrics built, how well do they predict, and which are free in November 2026?

### Takeaway
Almost every modern metric is the same recipe: a box-score (plus tracking) regression trained on multi-year RAPM, blended with or used as the prior for on/off or RAPM information; they differ in inputs, time-weighting and whether they describe a season or forecast the next game. On 19 November 2026 the free, daily-updated choices are DARKO DPM, xRAPM/RAPM (xrapm.com, nbarapm.com), Basketball-Reference BPM and the open-data projects OpenRAPM and LUMA; EPM bulk data costs $24.95 to $250 a year, RAPTOR and PIPM are dead, and free bulk access to LEBRON and DRIP could not be confirmed.

### Cited Findings

**Shared building blocks**
- RAPM is a ridge regression that solves for each player's offensive and defensive value from who was on the floor: about 50,000 distinct ten-man lineup "equations" a season, two unknowns per player. Joe Sill's 2010 regularised version was reported as nearly doubling the accuracy of plain adjusted plus-minus. — [Dunks & Threes, About EPM (archived early-2023 version)](https://web.archive.org/web/2023/https://dunksandthrees.com/about/epm)
- Jeremias Engelmann (creator of ESPN's RPM): RAPM is fit on about 200 possessions a game, the shrinkage penalty is chosen by cross-validation, single-season RAPM is noisy, and the version that predicts best uses two to three seasons with the latest weighted most. — [Engelmann on Royce Webb's 5x5, 20 Jan 2026](https://www.roycewebb.com/p/adjusted-plus-minus-explained)
- Published ridge penalties: 10,000 for the plain single-season reference RAPM in Hoop Impact Bench (possessions counted from the box score) — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench); 40,000 for OpenRAPM's multi-season "label" and 13,037 for its in-season rating that is pulled toward a box-score prior instead of zero — [OpenRAPM README](https://github.com/bbstats/openrapm)
- RAPM uncertainty is large even over long windows: Wembanyama's 30-year defensive RAPM is quoted as +5.2 with a standard error of 1.1, and low-minute players have the widest intervals; the same article says nobody publishes standard errors for box-score-based metrics (BPM, EPM, LEBRON, DARKO). — [Engelmann on 5x5, 13 Jun 2026](https://www.roycewebb.com/p/an-nba-first-introducing-standard)
- Why a box-score model is layered on top: RAPM "can be very noisy, taking several seasons to stabilize", so stats that stabilise faster are used to approximate long-term RAPM. — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)

**Box Plus/Minus 2.0 (Daniel Myers, Basketball-Reference): fully published formula, box score only**
- Trained on four five-year RAPM samples covering 1996-97 to 2015-16 (Bayesian RAPM with a prior from team quality and minutes per game). Inputs are per 100 team possessions; coefficients are interpolated linearly between position 1 (PG) and 5 (C), and for shot attempts between offensive role 1 (creator) and 5 (receiver). — [Basketball-Reference, About BPM 2.0](https://www.basketball-reference.com/about/bpm2.html)
- Total-BPM coefficients (position 1 → position 5): team-adjusted points 0.860; 3PM 0.389; AST 0.580 → 1.034; TOV −0.964; ORB 0.613 → 0.181; DRB 0.116 → 0.181; STL 1.369 → 1.008; BLK 1.327 → 0.703; PF −0.367; FGA −0.560 (role 1) → −0.780 (role 5); FTA −0.246 (role 1) → −0.343 (role 5). Position constant −0.818 at PG rising to 0 at position 3 and above; role constant −2.774 at role 1, 0 at role 3, +2.774 at role 5. — [Basketball-Reference, About BPM 2.0](https://www.basketball-reference.com/about/bpm2.html)
- Position estimate = 2.130 + 8.668·%TRB − 2.486·%STL + 0.992·%PF − 3.536·%AST + 1.667·%BLK; offensive role = 6.00 − 6.642·%AST − 8.544·%(threshold points); both clipped to 1–5 and shifted so the team's minutes-weighted average is 3.0; small samples are padded with 50 minutes of the listed position (or role 4.0). — [Basketball-Reference, About BPM 2.0](https://www.basketball-reference.com/about/bpm2.html)
- Team adjustment: a single constant (typically about −8) is added to every player's raw BPM so the minutes-weighted sum equals the team's adjusted rating; the adjusted rating adds 0.35/2 points per point of average lead (2016-17 Cavaliers: +3.0 becomes +3.24). OBPM has its own coefficient set; DBPM = BPM − OBPM. — [Basketball-Reference, About BPM 2.0](https://www.basketball-reference.com/about/bpm2.html)
- Replacement level is −2.0; VORP = (BPM + 2.0) × share of team possessions played × team games/82; wins above replacement ≈ VORP × 2.7. The page publishes no RMSE or out-of-sample test and says BPM is good at offense and weaker on defense. — [Basketball-Reference, About BPM 2.0](https://www.basketball-reference.com/about/bpm2.html)

**RAPTOR (FiveThirtyEight, 2019–2023, discontinued)**
- Two components fitted to a six-year RAPM sample (2013-14 to 2018-19) supplied by Ryan Davis: a "box" regression using box-score, play-by-play and player-tracking stats, and an "on-off" component built from the player's on-court ratings, his courtmates' ratings without him, and the courtmates' other courtmates' ratings. Overall RAPTOR ≈ 0.85 × box + 0.21 × on-off, the weights chosen by out-of-sample RAPM prediction; "box" was much more predictive than "on-off". — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- Defensive regression R² against in-sample RAPM was about 0.6 with tracking inputs versus about 0.3 with steals, blocks, defensive rebounds and fouls alone. Example weights: a steal is worth 1.49 points on defense; each missed two-pointer as nearest defender +1.05; each three-point attempt defended (made or missed) +0.17; each free throw made after the player's foul −0.19. — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- Replacement level −2.75; WAR = (RAPTOR + 2.75) × minutes × ((league pace + individual pace impact)/league pace) × 0.0005102 (0.0005262 in playoffs). The predictive variant PREDATOR correlated 0.98 (offense) and 0.95 (defense) with RAPTOR. — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- Status: the GitHub folder still serves the frozen history (`modern_RAPTOR_by_player.csv`, 2013-14 to 2022-23, returned HTTP 200, about 1.2 MB, on 19 Nov 2026; columns include `raptor_box_total`, `raptor_onoff_total`, `raptor_total`, `predator_total`, `pace_impact`, `mp`, `poss`). The "latest" files and game forecasts lived on projects.fivethirtyeight.com, which now redirects to abcnews.com. — [fivethirtyeight/data, nba-raptor](https://github.com/fivethirtyeight/data/tree/master/nba-raptor)

**EPM (Taylor Snarr, Dunks & Threes)**
- Current build: two statistical plus-minus models fitted to multi-season RAPM — a box-score model on 2003-04 to 2022-23 (20 seasons, 4.9 million possessions, playoffs included) and a tracking model for defense on 2017-18 to 2022-23 (6 seasons, 1.5 million possessions). Their output is the prior for an exponentially decayed RAPM run for every date since 2001-02 (5,153 dates, 32,190 games, about 6.2 million possessions), controlling for home court and the "rubber band" score effect. Every season from 2023-24 on is outside the training data. — [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)
- The inputs are "Estimated Skills": each stat has its own next-game model with an exponential decay factor (weight = factor^days-ago) tuned by differential evolution, an approach the page says is inspired by DARKO. Ratings come in a game-agnostic form and a game-optimized form that accounts for home court, rest, season type, opponent strength and the teammates and opponents expected to play. — [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)
- The earlier (2023) version used a 10-year RAPM sample (2004–2013) for offense and a 4-year sample (2018–2021) for defense, then a one-season RAPM with a strong penalty that usually moved a player less than 1 point from the prior; values typically ran from about −8 to +8 with an unweighted average near −1.0. — [Dunks & Threes, About EPM (archived early-2023 version)](https://web.archive.org/web/2023/https://dunksandthrees.com/about/epm)
- Price (paywalled, flag for a free-data project): Basic $24.95/year, Premium $49.95/year, Premium + API $250/year, all billed annually; listed features include EPM and skills access, team ratings for every date, game win probabilities, box-score predictions, CSV downloads and REST API access. — [Dunks & Threes, Subscribe](https://dunksandthrees.com/subscribe)
- API: JSON over HTTPS with an emailed key sent in an `Authorization` header, 90 requests a minute; endpoints `/api/v1/epm`, `/epm-all`, `/season-epm`, `/team-epm`, `/game-predictions`, `/game-predictions-box`; fields include `p_mp_48` (predicted minutes), `oepm`, `depm`, `epm`. Version 1 is retired after 2026-27; version 2 is current. — [Dunks & Threes API documentation](https://dunksandthrees.com/api/v1/documentation)
- **[own observation]** The public EPM leaderboard page rendered without login on 19 Nov 2026 and its HTML carried 537 player records; CSV download and API are listed only as subscriber features, and the footer reads "All rights reserved", so treat bulk use as paid. — [Dunks & Threes EPM page](https://dunksandthrees.com/epm)

**DARKO DPM (Kostya Medvedovsky): free, forecast-oriented**
- DARKO forecasts every box-score stat for a player's next game, then turns the forecasts into DPM ("Daily Plus Minus"). Each stat is weighted by β^t (t = days ago, β fitted per stat by differential evolution), combined with a modified Kalman filter through a gradient-boosted tree, with per-stat adjustments for rest, travel, home court, opponent, age, seasonality, interactions between stats and team changes. Covers every game since 1996-97 (791,507 player-games; 525 players rated on 18 Nov 2026). — [DARKO, About](https://darko.app/about)
- Memory differs by stat (half-lives for a 31-year-old, in-season): starting about 1 game; minutes about 2 games; playing at all about 3 games; share of shots from three about 13; usage about 17; assist rate about 24; points about 31; blocks about 41; defensive rebounds about 46; steal rate about 75; turnovers about 1.1 seasons; free-throw % about 1.4 seasons; three-point % about 1.5 seasons; rim % about 2.5 seasons. — [DARKO, About](https://darko.app/about)
- Two flavours: Box DPM (box-score projections only) and DPM (adds on/off). On/off's share = career possessions ÷ (career possessions + 10,000) on offense and ÷ (+ 6,000) on defense; a season as a starter is about 5,000 possessions, so a one-season starter is about 67% box / 33% on-off on offense and 55% / 45% on defense. — [DARKO, About](https://darko.app/about)
- Rookies start from age, draft slot and height only (no college, summer-league or preseason data): the 2026 No. 1 pick starts at −1.0, most other first-rounders between about −1.5 and −3.3, undrafted players about −2.2 to −3.6. Between seasons projections are pulled back toward average. — [DARKO, About](https://darko.app/about)
- Access: free site, ratings through 18 Nov 2026; CSV download buttons on the leaderboard, team pages, Compare, Standings, WOWY, Lineups, Longevity and Fantasy Lab; a "Time Machine" shows any date since 1996-97. A public MCP endpoint, `https://www.darko.app/mcp`, needs no sign-in but is built for charts. — [DARKO, About](https://darko.app/about); [DARKO, Use DARKO in your assistant](https://darko.app/assistant)
- **[own observation]** The leaderboard's own page-data route (`https://darko.app/__data.json`) returned JSON on 19 Nov 2026 with fields `nba_id`, `player_name`, `dpm`, `o_dpm`, `d_dpm`, `box_dpm`, `on_off_dpm`, `x_minutes`, `x_pace` and others. It is an internal, undocumented route; the documented path is the CSV button. — [DARKO leaderboard](https://darko.app/)

**LEBRON (BBall Index: Krishna Narsu and Tim "Cranjis McBasketball")**
- A box prior using the box-score weights of PIPM, stabilised with a padding technique credited to Medvedovsky and adjusted by offensive archetype, then used as the prior in a luck-adjusted RAPM (Ryan Davis's RAPM script). 0 is average and −2.7 is replacement level; "Wins Added" reuses Goldstein's formula. The database started at 2009-10. — [BBall Index, LEBRON Introduction](https://www.bball-index.com/lebron-introduction/)
- Access is unclear in November 2026: the 2023 site menu listed a "LEBRON Database" and "LEBRON Application" under "Free Data", while a partner page in 2026 says membership gives "every tool in full, including LEBRON". — [BBall Index, LEBRON Introduction](https://www.bball-index.com/lebron-introduction/); [Fanspo, BBall Index membership](https://fanspo.com/bball-index/subscribe)

**DRIP (The Analyst / Stats Perform)**
- "Daily-updated Rating of Individual Performance": box-score, play-by-play and lineup inputs; rookie priors from height, weight, age and draft pick; padding plus Bayes filters to "now-cast" each stat; gradient-boosted trees for next-game projections made "in a vacuum" (no opponent adjustment); output O-DRIP, D-DRIP, DRIP. The article publishes no accuracy test (published 19 Oct 2021, last modified 28 May 2025). — [The Analyst, NBA DRIP](https://theanalyst.com/articles/nba-drip-daily-updated-rating-of-individual-performance/)

**xRAPM (Jeremias Engelmann)**
- RAPM anchored ratings to which box-score stats and physical profiles are added through machine learning; ESPN's RPM was originally this design ("an SPM model as a Bayesian prior in a one-season RAPM calculation called xRAPM"). — [Engelmann on 5x5](https://www.roycewebb.com/p/adjusted-plus-minus-explained); [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)
- Access: xrapm.com is live and free, showing "Metrics updated on: 2026-11-18", with pages for xRAPM, historical xRAPM, 1-year, 3-year and 30-year RAPM, coach and pair RAPM; the front page is a plain HTML table (471 players when fetched). — [xRAPM](https://xrapm.com/)

**PIPM (Jacob Goldstein)**
- No longer public: BBall Index says Goldstein and PIPM moved to the Washington Wizards organisation; PIPM was built like LEBRON but with estimated rather than actual RAPM and without role adjustment or stabilisation. Its box-score weights survive inside LEBRON. — [BBall Index, LEBRON Introduction](https://www.bball-index.com/lebron-introduction/)

**Other free sources found**
- RAPM tables: nbarapm.com offers time-decay RAPM, rolling 2- to 5-year RAPM and "datasets" pages, plus peak tables for RAPTOR, DARKO, LEBRON and "LAKER (formerly estimated RAPTOR, a BPM-style metric)". — [nbarapm](https://www.nbarapm.com/)
- OpenRAPM (Nathan Walker): MIT-licensed code and ratings for every player-season from 1996-97, a ridge regression pulled toward a LightGBM box-score prior. — [OpenRAPM README](https://github.com/bbstats/openrapm)
- LUMA Basketball Research: CSV files under CC BY 4.0 for ARC (descriptive), LOKI (predictive, four releases a season) and HAPM, plus an API with a free key that also serves box scores, lineups and on/off since 1996-97. New in 2026 and self-published. — [lumahoops/NBA README](https://github.com/lumahoops/NBA)
- Hoop Impact Bench data (CC BY 4.0): `data/games.csv` (regular-season scores 2019-20 to 2025-26), `data/minutes.csv` (minutes per player per game), `data/players.csv` (NBA.com ids), and reference RAPM files. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Danny Harlan's EPM projections: free XGBoost projections 1–5 seasons ahead; out-of-fold mean absolute error for one-year-ahead predictive EPM is 0.74. — [nba-epm-projections README](https://github.com/dannyharlan05/nba-epm-projections)

**Availability summary, 19 November 2026**

| Metric | Status | How to get it | Cost |
|---|---|---|---|
| RAPM (1-, 3-, 30-year; time-decay) | Live | HTML tables at [xrapm.com](https://xrapm.com/) and [nbarapm.com](https://www.nbarapm.com/datasets); CSV in [Hoop Impact Bench](https://github.com/lumahoops/hoop-impact-bench) | Free |
| BPM 2.0 | Live | Season "Advanced" tables on Basketball-Reference, exportable as CSV from the page; or compute from the [published formula](https://www.basketball-reference.com/about/bpm2.html) | Free; automated access limited to 20 requests a minute, with a "jail" of up to a day, and no API or download files offered — [Sports Reference bot policy](https://www.sports-reference.com/bot-traffic.html) |
| RAPTOR | Dead since June 2023 | Frozen CSVs on [GitHub](https://github.com/fivethirtyeight/data/tree/master/nba-raptor) | Free |
| EPM | Live | Site, CSV and JSON API — [docs](https://dunksandthrees.com/api/v1/documentation) | **Paid: $24.95, $49.95 or $250 a year** — [Subscribe](https://dunksandthrees.com/subscribe) |
| DARKO DPM | Live | CSV buttons on [darko.app](https://darko.app/about); MCP endpoint | Free |
| LEBRON | Live | [bball-index.com](https://www.bball-index.com/lebron-introduction/) | Unconfirmed; membership-gated at least in part |
| DRIP | Not confirmed | Leaderboard on [theanalyst.com](https://theanalyst.com/articles/nba-drip-daily-updated-rating-of-individual-performance/); no download or API mentioned | Free to view, if still updated |
| xRAPM | Live | HTML tables at [xrapm.com](https://xrapm.com/) | Free |
| PIPM | Private | Not available — [BBall Index](https://www.bball-index.com/lebron-introduction/) | n/a |
| OpenRAPM, LUMA LOKI/ARC | Live | CSV on GitHub — [OpenRAPM](https://github.com/bbstats/openrapm), [LUMA](https://github.com/lumahoops/NBA) | Free |

### Inferences
- For a free-data project the practical shortlist is DARKO DPM (forecast-oriented, daily, with projected minutes in the same file), xRAPM, BPM and OpenRAPM. BPM is the only one whose full formula is published, so it can be recomputed in-house for any past date without look-ahead.
- Historical values shown today for EPM and DARKO are "today's model's value for that date", not what was published then (see the Hoop Impact Bench provenance notes in section 2). A backtest that uses them will look better than live use would have.
- Metrics do not share a zero point: Hoop Impact Bench found EPM's average team sat 2.90 points below zero. Re-centre summed team ratings on the league average each day before using them.
- The replacement-level conventions are close enough to use one default for unrated players: −2.0 (BPM, Hoop Impact Bench), −2.7 (LEBRON), −2.75 (RAPTOR), and DARKO's rookie priors of roughly −1 to −3.5.

### Gaps
- BBall Index's current prices and whether the LEBRON table can still be downloaded free: the site is a JavaScript app that could not be read; a search listing showed "$5.00/mo or $52.50/yr" for a Data & Tools package but that could not be verified and may be stale.
- Whether The Analyst still updates the DRIP leaderboard in 2026-27 (the page blocks scripted access; its metadata shows an edit on 10 Nov 2026 but no table was visible).
- Terms of use for automated collection from darko.app, xrapm.com and nbarapm.com were not found; none documents a public data API.
- xPM (VORP.app), Pulse (CourtSignal) and GRBNU appear in Hoop Impact Bench but their access terms were not checked.
- ESPN's RPM and its 2025 successor "Net Points" were not researched.

## 2. What head-to-head tests of predictive power exist, and which metric is considered most predictive?

### Takeaway
No metric wins every test. EPM won Snarr's 2020 retrodiction (RMSE 2.48 against 2.60 to 3.20 for nine others, 2013-14 to 2019-20) and leads the small 2026-27 live boards; in the open Hoop Impact Bench (2020-21 to 2025-26) newer projection-style metrics lead and LEBRON, DARKO, xRAPM and EPM sit together at 3.28 to 3.32; DARKO was the top pick of NBA team staff in 2021. The dependable gaps are hybrid metric > box-score-only BPM > last season's team rating, while differences among the hybrids are mostly within noise.

### Cited Findings

**Snarr's retrodiction test (Dunks & Threes, 17 June 2020; 2013-14 to 2019-20)**
- Method: each player's prior-season value × his actual minutes in the predicted season, summed to a team rating and compared with the team's adjusted net rating; players under 250 minutes and all rookies get replacement level (−2.0 for plus-minus metrics, 11 for PER, 0.045 for WS/48); six season pairs, 180 team-seasons; error is RMSE. The author created EPM and says so. — [Dunks & Threes, NBA Player Metric Comparison](https://dunksandthrees.com/blog/metric-comparison)
- RMSE: EPM 2.48; RPM 2.60; RAPTOR 2.63; BPM 2.71; PREDATOR 2.73; PIPM 2.78; RAPM 2.80; WS/48 2.85; team-adjusted PER 3.12; PER 3.20. — [Dunks & Threes, NBA Player Metric Comparison](https://dunksandthrees.com/blog/metric-comparison)
- Low-continuity teams (n = 99) / high-continuity teams (n = 81): EPM 2.55 / 2.36; RPM 2.64 / 2.48; RAPTOR 2.65 / 2.47; BPM 2.79 / 2.52; PIPM 2.88 / 2.57; RAPM 2.86 / 2.65; WS/48 2.97 / 2.61; PER 3.10 / 3.11. — [Dunks & Threes, NBA Player Metric Comparison](https://dunksandthrees.com/blog/metric-comparison)

**Hoop Impact Bench (open-source; LUMA Basketball Research; first results 29 Oct 2026)**
- Method: a team's rating in a game is 5 × the minutes-weighted average of its players' ratings using the minutes actually played; home rating minus away rating is the predicted margin (no home-court term). Tests: R² on game margins, correlation with team win %, and RMSE against opponent-adjusted team net rating after centring each metric's average team on zero. Unrated players count as −2.0. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Retro table, preseason ratings scored on 2020-21 to 2025-26 (7,230 games, 180 team-seasons), "full forecast" view — net error / game-margin R² / win % r:

| Metric | Net error (pts per 100) | Game R² | Win % r |
|---|---|---|---|
| Same-season RAPM (in-sample ceiling) | 1.51 | .267 | .958 |
| xPM (VORP.app) | 2.79 | .193 | .825 |
| GRBNU | 2.81 | .205 | .835 |
| Danny Harlan's EPM projection | 2.88 | .179 | .829 |
| Pulse | 2.95 | .177 | .807 |
| OpenRAPM | 3.01 | .171 | .801 |
| LOKI (maintainer's own) | 3.16 | .196 | .828 |
| LEBRON | 3.28 | .154 | .766 |
| DARKO | 3.28 | .159 | .773 |
| xRAPM | 3.31 | .169 | .782 |
| EPM | 3.32 (4.44 before centring) | .178 | .808 |
| BPM (Basketball-Reference) | 3.50 | .154 | .768 |
| Last season's RAPM, no prior | 3.55 | .132 | .711 |
| Last season's team rating (floor) | 4.08 | .092 | .609 |
| Every player rated 0 (floor) | 5.04 | .000 | .000 |

  — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- In the "established players" view (everyone under 250 minutes the season before, rookies included, set to −2.0): xPM 2.92; Harlan 2.98; LOKI 2.99; GRBNU 3.00; Pulse 3.01; OpenRAPM 3.12; LEBRON 3.22; DARKO 3.31; EPM 3.35; xRAPM 3.39; BPM 3.46; last season's team 3.96; every established player rated 0 scores 4.42 with game R² .125 and win % r .678. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Stated limits: the retro tables are "a loose baseline … not a conclusive ranking" because past values come from each metric's current model (EPM and DARKO are "today's model's value for that date"), so held-out fitting cannot be confirmed; rank ranges overlap for most neighbours. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Live 2026-27 "dynamic" board (each morning's published ratings; 138 games, 31 Oct to 18 Nov 2026): EPM 3.66; xRAPM 4.06; Pulse 4.30; DARKO 4.39; LEBRON 4.78; xPM 4.79; OpenRAPM 5.56; BPM 5.71; average of all metrics 4.06; last season's team 5.30; everyone 0 at 7.00. Preseason board (222 games from 20 Oct): EPM 4.46; xPM 4.57; DARKO 4.68; LEBRON 5.09; xRAPM 5.09; BPM 5.37; average of all metrics 4.37; last season's team 5.24. The site warns it is early (8–16 games per team) and that ranges overlap. — [Hoop Impact Bench](https://hoopimpactbench.org/)
- Picking the higher-rated team with no home edge over those 222 games: EPM 155-67, DARKO 149-73, BPM 151-71, LEBRON 142-80. — [Hoop Impact Bench](https://hoopimpactbench.org/)

**Other tests and expert views**
- Krishna Narsu's 2024 out-of-sample test (team win %, 2020-21 to 2022-23), as reproduced by Hoop Impact Bench: R² of .555 for LEBRON, .523 for DARKO and .514 for BPM. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Ben Taylor's Nylon Calculus test (8 Jan 2019; teams from 1998 to 2018; prior-season value × next-season minutes): for teams with 88%+ core continuity and SRS of at least 4 (41 teams), adjusted plus-minus missed by about 2.4 points and PIPM and AuPM by about 2.8; PER and Win Shares were within about 3 points for stable rosters but degraded substantially when rosters changed, and Taylor concluded PER should be retired. — [Nylon Calculus, What's the best advanced stat?](https://fansided.com/2019/01/08/nylon-calculus-best-advanced-stat)
- HoopsHype survey of NBA team staff and media (17 Sep 2021, 29 respondents): DPM was named the preferred all-in-one metric by 8, trusted by 10 more and distrusted by 1; 22 said they did not trust PER and 14 did not trust WS/48. Most teams rely on their own systems. — [DARKO, About](https://darko.app/about); [HoopsHype via Yahoo Sports](https://sports.yahoo.com/best-advanced-statistic-basketball-nba-120938416.html)
- FiveThirtyEight's internal testing: the forecast used the predictive PREDATOR variant in 2019-20, but "subsequent testing showed that standard RAPTOR is much better to use for this purpose" and PREDATOR was retired on 17 Dec 2020. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- BPM's own author (Daniel Myers, "DSMok1") wrote in November 2023 that he would "trust DARKO over BPM" because it uses more information; another modeller in the thread called DARKO "the pinnacle of public one number metrics". The thread contains no formal test. — [APBRmetrics forum, Comparing BPM and DarkoPM](https://apbr.org/metrics/viewtopic.php?t=10046)
- DARKO's own accuracy check was against two daily-fantasy projection sites: it beat both on points, rebounds, assists, blocks, turnovers and threes, and lost only on minutes. — [DARKO, About](https://darko.app/about)

### Inferences
- Averaging several metrics is a cheap, robust choice: the "consensus of all metrics" row is best on the 2026-27 preseason board (4.37) and tied for second on the dynamic board (4.06). A free blend of DARKO, xRAPM, OpenRAPM and BPM is therefore defensible.
- The spread between the best and worst hybrid metric (about 0.5 points of team net error in the retro table) is smaller than the gap between any player metric and last season's team rating (0.6 to 1.3 points). Getting the roster and minutes right matters more than which good metric is chosen.
- All these tests use actual minutes played, so they measure the ratings, not a forecaster's ability to project minutes; live accuracy will be lower.

### Gaps
- No independent test was found that scores archived, as-published daily ratings for several metrics over multiple full seasons; Hoop Impact Bench's live boards only began on 20 Oct 2026.
- Narsu's original 2024 post (on X) and HoopsHype's full ranked list could not be read directly; the numbers above come from pages that quote them.
- No published head-to-head test including DRIP was found.

## 3. How do player-based game models work end to end?

### Takeaway
Every published system does the same four steps: project each player's rating, project each player's minutes for the specific game, sum rating × minutes share into a team rating per 100 possessions, and convert the rating difference plus home court and rest into a margin and win probability. FiveThirtyEight is the only one that published every constant; DARKO and EPM publish the summation rule but not their game-level conversion.

### Cited Findings

**FiveThirtyEight's RAPTOR forecast (2019-20 to 2022-23), step by step**
- Player rating: a preseason RAPTOR projection is the prior. No in-season data are used until a player has 100 minutes; current-season performance is phased in between 100 and 1,000 minutes (750 in the playoffs); the prior's weight depends on age and experience. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Preseason projection weights: earlier versions weighted the last three seasons 60 / 30 / 10; later the weights depended on age (about 76% on the latest season for a 23-year-old entering his fourth year). — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- Minutes: projected MPG = (12.6 × preseason MPG projection + current-season minutes) ÷ (12.6 + current-season games). A depth-chart algorithm then allocates minutes by position among available players. From 2022-23 this was blended with a "history-based" figure (minutes over the past 15 days, up to five games): 60% history / 40% depth chart for a game today, sliding to 0% / 100% for games 15 or more days away. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Availability: staff marked players injured, resting or suspended game by game; from 2022-23 short-term injuries came automatically from ESPN data; a "load management" setting put certain stars on reduced minutes; a player forced to play well above his recommended minutes had his rating penalised. Two team ratings were shown, "current" (injuries applied) and "full-strength". — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Team rating: the minutes-weighted average of player offensive (and defensive) ratings × 5, then × 0.8 in the regular season or × 0.9 in the playoffs. The scalar exists because ratings describe a tied game and good teams play with leads. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/); [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- Score effect behind the scalar: a team leading by 10 points plays about 2.3 points per 100 possessions worse than in a tied game (4.6 for a 20-point lead), more so in later quarters and less in the playoffs. — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- Conversion to a win percentage: points scored = (league offensive rating + team offensive rating) ÷ 100 × 82 × pace, points allowed likewise with the defensive rating; win % = PF^14.3 ÷ (PF^14.3 + PA^14.3), exponent 13.2 in the playoffs. The 2018-19 league figures used were 108.44 points per 100 possessions and 101.91 possessions per 48 minutes; playoff pace × 0.965. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Conversion to an Elo-scale rating: Elo = 1504.6 − 450 × log10(1/win% − 1). From 2020-21 the result was blended with ordinary game-result Elo: about 65% player-based, 35% Elo on average, the Elo share ranging from 0 to 55% with roster continuity. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Game adjustments in Elo points: home court about 70 in 2022-23 (a rolling 10-year average; originally 92; cut 25% in 2020-21 for empty arenas); a team that played the previous day −46; travel distance and altitude also adjusted (values not published). Win probability = 1 ÷ (10^(−(rating difference + bonus difference)/400) + 1). — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Point spread: Elo difference (home edge included) ÷ 28; the 2015 Elo write-up used 100 points for home court. — [FiveThirtyEight, How We Calculate NBA Elo Ratings (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/features/how-we-calculate-nba-elo-ratings/)
- Pure Elo baseline for comparison: K = 20, home court only, each team reverted a quarter of the way to 1505 between seasons, no roster knowledge. Season simulations ran 50,000 times. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Pace: RAPTOR also estimated each player's effect on possessions per 48 minutes (Westbrook +2.7 in 2018-19); about half of a team's pace was attributed to players and half to coach and system. — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)

**DARKO**
- Team rating = players' DPM weighted by DARKO's projected minutes over the full 240 team minutes, in points per 100 possessions against an average team; each point of team rating is worth about 2.7 wins over 82 games. Example on the page: Jokic at +7.1 DPM and 35.9 projected minutes with four average teammates gives a +5.0 team rating and 55 wins. — [DARKO, Teams](https://darko.app/teams); [DARKO, About](https://darko.app/about)
- Projected minutes are "when he plays": a player ruled out on the official injury report still shows his healthy minutes, with a note on his page, so the user must zero him out. — [DARKO, About](https://darko.app/about)

**EPM (Dunks & Threes)**
- Team ratings combine player EPM with expected minutes. The "next-game rating" uses the expected lineup including known injuries; the "season rating" uses the season-expected rotation; all are centred on the league average for the date. — [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)
- Minutes are predicted for every player in every game and updated as tip-off nears from known injuries and official status; "when a player is out, game context informs how their minutes shift to teammates". Game predictions (score, margin, home win probability) refresh more often inside 30 minutes of tip-off. The model is retrained before each season on earlier seasons only. — [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)
- Season simulations run 30,000 times nightly with player availability simulated game by game and "a random margin around the predicted spread". — [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)

**ESPN BPI**
- ESPN's own description (27 Oct 2015) is team-level: final scores adjusted for opponent, pace, home court, visiting-team travel distance and days of rest, with preseason priors from Las Vegas win totals and the prior year; 10,000 season simulations. It gives no weights and does not mention player ratings or injuries. — [ESPN, What is ESPN's NBA Basketball Power Index?](https://www.espn.ph/nba/story/_/id/13984129/what-espn-nba-basketball-power-index)

**A sportsbook's description**
- DraftKings Engineering has published an article titled "Kalman Filters For NBA Player Ratings", which indicates at least one book maintains player-level ratings updated by a Kalman filter; the text could not be retrieved. — [DraftKings Engineering on Medium](https://medium.com/draftkings-engineering/kalman-filters-for-nba-player-ratings-d3bb9365221b)

### Inferences
- The summation rule is identical everywhere: team rating = Σ over players of rating × (minutes ÷ 48), which equals 5 × the minutes-weighted average. With separate offensive and defensive ratings a simple end-to-end version is: home points per 100 = league average + home offense − away defense; away likewise; expected possessions from team or player pace; margin = possessions/100 × (difference) + home court + rest terms; total = possessions/100 × (sum).
- FiveThirtyEight's two formulas together imply a logistic link between spread and win probability with a scale of 400 ÷ (28 × ln 10) ≈ 6.2 points, equivalent to a standard deviation of about 11.3 points; its 46-point back-to-back penalty is about 1.6 points of spread and its 70-point home edge about 2.5 points.
- The 0.8 regular-season scalar is a strong prior that raw sums of player ratings overstate team differences by about a fifth; any home-built sum should be calibrated against actual margins rather than used at face value.
- Minutes are the weakest link in every system (DARKO lost only on minutes; EPM's biggest gain over a naive baseline is on minutes), so a simple, transparent minutes rule (recent-game average blended with a slower prior, then redistribution of absent players' minutes) is where most of the engineering effort should go.

### Gaps
- Neither DARKO nor EPM publishes the formula that turns team ratings into a spread, total or win probability, or how minutes of absent players are redistributed.
- ESPN's current BPI methodology (post-2015) was not found; a search summary of ESPN's BPI table glossary referred to a player-based "talent" component built on RPM, which could not be verified.
- The DraftKings article was blocked to automated reading.

## 4. How many points of spread are individual players worth, and how far do lines move on injury news?

### Takeaway
Oddsmakers put the single most valuable player at about 5.5 to 7 points, other MVP candidates at 3.5 to 5, ordinary All-Stars at 2 to 3, good starters at 1 to 2 and most rotation players at 1 point or nothing, and they scale values down when the supporting cast or backup is strong and in expected blowouts. Model arithmetic gives the same range, multiple absences cost more than the sum of the parts, and lines re-price within seconds of news.

### Cited Findings

**Oddsmakers' stated values**

| Source and season | Values (points of spread) |
|---|---|
| theScore, 2026 playoffs (undated page) | Jokic 5.5; Gilgeous-Alexander 4; Wembanyama 4; Doncic 3.5; Cunningham 3; Edwards 3; J. Brown, Avdija, Maxey 2.5; Embiid, Brunson, Mitchell, Mobley, Harden, Tatum, Barnes, Durant 2; Banchero, F. Wagner 1.5; LeBron James about 4 while Doncic and Reaves were out; Jalen Williams, Reaves, Aaron Gordon no more than 1 — [theScore](https://www.thescore.com/nba/news/3531319/nba-playoff-injury-woes-how-much-are-stars-worth-to-their-teams) |
| ESPN, 26 Feb 2022 (2021-22) | Jokic 7; Embiid 6.5 before the Harden trade and about 4 after; Curry 4.5 (Jeff Sherman of the SuperBook: "seven to eight" earlier that season); Giannis 4; Morant 3; DeRozan 2.5 — [ESPN](https://www.espn.com/chalk/story/_/id/33367184/how-much-do-nba-mvp-candidates-impact-daily-odds-betting-games) |
| CG Technology (William Bernanke), 2019-20 preseason | 5+ points: Giannis, Harden, Curry, Anthony Davis. 4: LeBron, Kawhi Leonard, Lillard. 2–3: Jokic, Embiid, Butler, Westbrook, Irving, Walker, Griffin, Young, Beal, George, Booker, Doncic, Murray, Towns, Gobert. 1–2: Porzingis, Tatum, Simmons, Oladipo, Dragic, Zion Williamson, Conley, Klay Thompson, Siakam. 1 point: 26 players, mostly a team's second- to fourth-best — [Action Network](https://www.actionnetwork.com/nba/2019-2020-nba-player-point-spread-betting-values-vegas-odds) |
| Two oddsmakers (Scott Cooley; Mike Young of CG Technology), 2018-19 preseason | Tiers of 5, 4, 3, 2 and 1 points, each movable by a point either way; LeBron James 6–7 with the Lakers, "more than any other player … over the past handful of years"; many fifth-tier players "might not impact the spread at all" — [Action Network](https://www.actionnetwork.com/nba/nba-player-point-spread-values-2018-19-james-durant-curry-harden) |
| Action Network guide, updated 29 Sep 2026 | A top-five player "can be worth as much as 4 to 6 points" — [Action Network](https://www.actionnetwork.com/education/how-injuries-affect-betting-lines-a-guide-to-market-movement) |

**How values change with context**
- Value is situational: it reflects team, teammates, backup, coach and system, so a better player can be worth less than a worse one (Leonard was marked down because Paul George is similar; DeMar DeRozan was left off entirely because of the Spurs' system). — [Action Network, 2019-20 values](https://www.actionnetwork.com/nba/2019-2020-nba-player-point-spread-betting-values-vegas-odds)
- Stars are "worth their full value … in key games that are expected to be close" and less in expected blowouts; the Bucks' spread fell 3 to 5.5 points in games Giannis missed in 2018-19, the low end mostly against bad teams. — [Action Network, 2018-19 values](https://www.actionnetwork.com/nba/nba-player-point-spread-values-2018-19-james-durant-curry-harden); [Action Network, 2019-20 values](https://www.actionnetwork.com/nba/2019-2020-nba-player-point-spread-betting-values-vegas-odds)
- Depth matters as much as the star: Giannis moved the line only four points in 2021-22 because he had two All-Star teammates; in 2026 Avdija (2.5) was rated above Brunson (2) because the Knicks cope better without Brunson. — [ESPN](https://www.espn.com/chalk/story/_/id/33367184/how-much-do-nba-mvp-candidates-impact-daily-odds-betting-games); [theScore](https://www.thescore.com/nba/news/3531319/nba-playoff-injury-woes-how-much-are-stars-worth-to-their-teams)
- Absences compound: when Cleveland rested James, Irving and Love together (individual values summing to 8–9 points), the line moved from Cavaliers −7.5 to Grizzlies −7, a 14.5-point swing; 11 points came on the news and the market pushed it 3.5 more. — [Action Network, 2018-19 values](https://www.actionnetwork.com/nba/nba-player-point-spread-values-2018-19-james-durant-curry-harden)
- Playoffs: one oddsmaker rated "playoff LeBron" at least a point higher than in the regular season. — [Action Network, 2018-19 values](https://www.actionnetwork.com/nba/nba-player-point-spread-values-2018-19-james-durant-curry-harden)

**Observed line moves**
- Spurs were 1.5-point favourites in a 2026 playoff Game 3 without Wembanyama and 5.5-point favourites in Game 4 with him (4 points). — [theScore](https://www.thescore.com/nba/news/3531319/nba-playoff-injury-woes-how-much-are-stars-worth-to-their-teams)
- ESPN's 2022 example: Denver −8.5 against Houston with Jokic, −1.5 without (7 points). — [ESPN](https://www.espn.com/chalk/story/_/id/33367184/how-much-do-nba-mvp-candidates-impact-daily-odds-betting-games)
- A 2018 preseason Lakers line opened +7 and closed +11.5 after LeBron was ruled out (4.5 points). — [Action Network, 2018-19 values](https://www.actionnetwork.com/nba/nba-player-point-spread-values-2018-19-james-durant-curry-harden)
- Results without the star: Denver was 46-24 with Jokic and 4-8 without him in 2024-25, while Boston went 8-2 without Tatum. — [RotoWire, 10 Dec 2025](https://www.rotowire.com/basketball/article/nba-lineups-sportsbooks-betting-odds-97545)
- Speed and process: books react "in seconds, not minutes", often with automated feeds; the game is taken off the board, re-opened at a new number, and sharp money then corrects it. Books "often over-adjust for big names", and "the betting public always overreacts to superstar absences". A 3-point player takes a −3.5 favourite to about −0.5 and a −170 moneyline to about −125. — [Action Network guide](https://www.actionnetwork.com/education/how-injuries-affect-betting-lines-a-guide-to-market-movement); [Action Network, 2018-19 values](https://www.actionnetwork.com/nba/nba-player-point-spread-values-2018-19-james-durant-curry-harden)
- Totals: losing an offensive star usually lowers the total; losing an elite rim protector can raise it. — [Action Network guide](https://www.actionnetwork.com/education/how-injuries-affect-betting-lines-a-guide-to-market-movement)
- Late scratches can come minutes before tip-off and "it's nearly impossible to beat oddsmakers to the punch". — [RotoWire, 10 Dec 2025](https://www.rotowire.com/basketball/article/nba-lineups-sportsbooks-betting-odds-97545)

**Academic evidence**
- Dare, Dennis and Paul (Finance Research Letters, 2015): NBA lines move away from the team with absences, especially for meaningful players; opening lines carry significant errors in games with a player absence; no profitable strategy exists at the closing line. — [EconPapers abstract](https://econpapers.repec.org/RePEc:eee:finlet:v:13:y:2015:i:c:p:130-136)

**Model-based values**
- DARKO's worked example: +7.1 DPM at 35.9 minutes with four average teammates is +5.0 points per 100 of team rating (about 14 extra wins over 82 games). Its current scale: median player −0.7, top 10% at +1.7 or better (55 of 525 players), top 1% at +5.2, best +7.1. — [DARKO, About](https://darko.app/about)
- Current top ratings for scale (19 Nov 2026): EPM has Wembanyama +11.0, Gilgeous-Alexander +8.9, Antetokounmpo +8.1, Jokic +7.7; DARKO has Jokic +7.1, Wembanyama +6.8, Gilgeous-Alexander +6.4. — [Dunks & Threes](https://dunksandthrees.com/); [DARKO leaderboard](https://darko.app/)

### Inferences
- Spread value ≈ (player rating − average rating of whoever absorbs his minutes) × minutes/48 × possessions/100, then × roughly 0.8 if FiveThirtyEight's score-effect scalar is applied. For Jokic at DARKO's numbers: replaced by replacement-level minutes (−2.0) this is (7.1 + 2.0) × 0.748 ≈ 6.8 per 100, or about 5.4 after the 0.8 scalar; replaced by median-level minutes (−0.7) about 4.7. That brackets the 5.5 oddsmakers quoted in 2026.
- A top-10% player (+1.7) at 32 minutes replaced by median-level minutes works out to about 1.3 points after the scalar, in line with oddsmakers' "1 to 2 points" for good starters; a typical rotation player is under half a point, consistent with "may not move the spread at all".
- Because cumulative absences move lines more than the sum of single-player values, a model should redistribute minutes down the whole depth chart (each absence pushes worse players into more minutes) instead of subtracting fixed per-player values.
- Published oddsmaker values are a useful sanity check on a model's injury adjustment: if the model moves a line 9 points for one absence, it is almost certainly wrong.

### Gaps
- The Dare, Dennis and Paul paper's sample period and effect sizes are behind a paywall.
- No systematic dataset of line moves at the moment of injury announcements was found; the examples above are individual cases.
- Two further lists surfaced only as search summaries and could not be opened: a 2022 list attributed to oddsmaker Kenny White (Curry, Durant, Antetokounmpo 6; Jokic 5) and a 69-player ranking attributed to USA Today (Jokic 5.15, Embiid 4.52, Antetokounmpo 4.38, Curry 4.09). Treat both as unverified.

## 5. How should a model treat injury-report statuses, rest, minutes restrictions and returns from long absences?

### Takeaway
Treat Out as zero and Doubtful as almost zero; Probable plays about 85 to 95% of the time and Questionable about half the time (roughly 50 to 60%, nearer 70% for high-minute players), and players who do play after a Questionable tag log close to normal minutes on average. The league publishes no percentages, the only published tracker covers 2026 alone, and rest is now mostly visible in advance through the official report, back-to-backs and the star-participation rules.

### Cited Findings

**Official rules and data format (2026-27)**
- Teams must designate a status and a specific reason for any player whose participation may be affected by 5 p.m. local time the day before a game; for the second game of a back-to-back, by 1 p.m. local time on game day. A game-day report is also due between 11 a.m. and 1 p.m. local time (8–10 a.m. for tip-offs at 5 p.m. or earlier). "Reports are updated on a continual basis throughout the day." The page defines no percentages for the statuses. — [NBA Official, Injury Report: 2026-27 Season](https://official.nba.com/nba-injury-report-2026-27-season/)
- The reports are PDFs published every 15 minutes at `https://ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HH_MMAM.pdf` (for example `Injury-Report_2026-11-19_05_00PM.pdf`); 86 files had been posted for 19 Nov 2026 by 9:15 p.m. ET. — [NBA Official, Injury Report: 2026-27 Season](https://official.nba.com/nba-injury-report-2026-27-season/)
- The move from hourly to 15-minute public updates, and the 11 a.m.–1 p.m. game-day window, came from a league memo reported on 19 Dec 2025 after the gambling investigations. — [ESPN, 19 Dec 2025](https://www.espn.com/nba/story/_/id/47361909/nba-outlines-injury-info-prop-betting-changes-memo-teams)
- Columns in each report: Game Date, Game Time (ET), Matchup, Team, Player Name ("Last, First"), Current Status, Reason. A free Python package, `nbainjuries` (pip; needs Python 3.10+ and Java for tabula-py), returns a report for a given timestamp as JSON or a DataFrame; archived reports exist from 2021-22, not for preseason, with occasional gaps. — [nbainjuries README](https://github.com/mxufc29/nbainjuries)
- **[own observation]** In 41 official reports from 21 Oct to 10 Nov 2025 the statuses used were Out, Doubtful, Questionable, Probable and Available, with a team-level "NOT YET SUBMITTED" placeholder. Reasons were "Injury/Illness" (2,219 rows), "G League" two-way or assignment (605), "Not With Team" (61), "Personal Reasons" (24), "Rest" (6), "Team Suspension" (3) and "Coach's Decision" (2). Rest was rarely labelled as such; "Injury Management" under Injury/Illness was more common. Files from that period used hourly names (`…_05PM.pdf`). — [NBA Official, Injury Report: 2026-27 Season](https://official.nba.com/nba-injury-report-2026-27-season/)
- **[own observation]** The NBA file host returned HTTP 403 "Access Denied" after about 40 files were requested in a burst of eight parallel connections, and stayed blocked. A collector should fetch slowly and cache.

**Play rates by status**
- Published tracker: over 2,007 designations for games from 18 Jan to 22 Oct 2026, players first listed Questionable played 48.3% of the time, Doubtful 4.2% and Probable 86.6%; a later snapshot gave 47.7%, 4.7% and 86.6%. The designation is the first status the official report gave the player for that game; "played" means minutes in the box score. These figures appeared in search-engine snapshots of the page; when fetched directly on 19 Nov 2026 the page said play rates were "still being collected", so they could not be re-verified. — [Is He Playing Tonight, questionable play rate](https://isheplayingtonight.com/nba-injuries/questionable-play-rate)
- Conventional labels of about 75% for Probable, 50% for Questionable and 25% for Doubtful circulate on betting sites, but the league defines no percentages. — [NBA Official, Injury Report: 2026-27 Season](https://official.nba.com/nba-injury-report-2026-27-season/)
- **[own calculation]** Play rates from 41 official report PDFs for the 21 game dates 21 Oct to 10 Nov 2025, joined to per-game minutes; "played" = more than zero minutes; 95% Wilson intervals in brackets. The sample is three early-season weeks only (collection was cut short by the access block above):

| Report used | Questionable | Probable | Doubtful | Out |
|---|---|---|---|---|
| 5 p.m. ET the day before (teams that had already filed) | 52/94 = 55% (45–65) | 27/30 = 90% (74–97) | 0/12 (0–24) | 1/473 = 0.2% |
| 10 a.m. ET on game day | 95/161 = 59% (51–66) | 40/47 = 85% (72–93) | 0/16 (0–19) | 3/722 = 0.4% |
| 5 p.m. ET on game day (games tipping 5:30 p.m. ET or later) | 74/145 = 51% (43–59) | 52/55 = 95% (85–98) | 0/15 (0–20) | 2/989 = 0.2% |

  — data: [NBA Official injury reports](https://official.nba.com/nba-injury-report-2026-27-season/); [Hoop Impact Bench minutes.csv and games.csv](https://github.com/lumahoops/hoop-impact-bench)
- **[own calculation]** Same sample, Questionable players by season minutes per game, 5 p.m. ET game-day report (10 a.m. in brackets): 28+ minutes 68% of 47 (73% of 44); 18–28 minutes 50% of 62 (58% of 76); under 18 minutes 32% of 34 (49% of 39). — data: [NBA Official injury reports](https://official.nba.com/nba-injury-report-2026-27-season/); [Hoop Impact Bench data](https://github.com/lumahoops/hoop-impact-bench)
- **[own calculation]** Same sample, players tagged "Available" at 5 p.m. ET: 84% played overall (82/98), 100% of those averaging 28+ minutes (18/18), 93% of 18–28 minutes (40/43), 69% of under 18 minutes (24/35). The tag means cleared, not guaranteed minutes. — data as above
- **[own calculation]** Same sample, minutes when they did play (players averaging 15+ minutes): Questionable at 5 p.m. ET averaged 95% of their season average (median 99%, n = 65); Questionable at 10 a.m. 93% (median 99%, n = 82); Probable 99% (median 96%, n = 47). — data as above

**Rest and load management**
- Star players missed 10.6 games a season on average in the 1990s and 23.9 in the 2020s, per the league's 57-page study sent to teams in January 2024. The study (10 years of data) found no lower injury rate when players rested and no rise in injuries on second nights of back-to-backs, while noting it also lacks evidence that load management fails. — [NBA.com, 12 Jan 2024](https://www.nba.com/news/nba-sends-data-load-management-study)
- League executive Joe Dumars said the data suggest "maybe guys aren't as efficient on the second night of a back to back". — [CBS Sports, 11 Oct 2023](https://www.cbssports.com/nba/news/league-study-shows-that-load-management-doesnt-correlate-to-lack-of-injuries)
- Stars playing one game of a back-to-back but not the other rose 87% from 2017-18 to 2022-23; in 2022-23 there were 88 such instances and 77% of the skipped games were on the road (66% the season before). Teams averaged 14 back-to-backs in 2023-24. — [Sportico via Yahoo Sports, 24 Oct 2023](https://sports.yahoo.com/nba-load-management-rules-limit-040100843.html)
- Player Participation Policy (approved 13 Sep 2023, in force from 2023-24): a "star" is anyone named All-Star or All-NBA in the prior three seasons (or the current season after the All-Star Game). Teams must have no more than one star unavailable in a game, make stars available for national TV and NBA Cup games, balance home and road one-game absences, avoid long shutdowns, and keep resting players visible. — [NBA.com](https://www.nba.com/news/nba-board-of-governors-approves-new-player-participation-policy)
- Exceptions and penalties: a star may be pre-approved to sit one game of a back-to-back if he is 35 or older on opening night, has 34,000 career minutes or 1,000 career games (regular season plus playoffs), or has a qualifying injury history; if one of the two games is on national TV or in the Cup he must play that one. Fines are $100,000, then $250,000, then $1 million more than the previous fine. — [Hoops Rumors, 26 Nov 2024](https://hoopsrumors.com/2024/11/hoops-rumors-glossary-player-participation-policy.html)
- Awards need 65 games (62 with a season-ending injury); five of the 15 All-NBA players in 2022-23 would not have qualified. — [Sportico via Yahoo Sports, 24 Oct 2023](https://sports.yahoo.com/nba-load-management-rules-limit-040100843.html)
- FiveThirtyEight penalised a team that played the previous day by 46 Elo points (about 1.6 points of spread) and added a "load management" reduced-minutes setting for certain stars from 2020-21. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)

**Minutes restrictions and returns from long absences**
- Published systems handle role changes through fast-moving minutes estimates: DARKO's minutes estimate has a half-life of about 2 games and "starting" about 1 game; FiveThirtyEight gave 60% weight to a player's last (up to) five games within 15 days for today's game. — [DARKO, About](https://darko.app/about); [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- EPM's minutes model misses by 4.6 minutes a game on average against 5.4 for a season-to-date average (2023-24 to 2025-26), a 14.5% improvement and its largest gain on any stat. — [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)
- FiveThirtyEight lowered a player's rating when a short-handed team forced him well above his recommended minutes. — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- Long-term outcomes after severe injury: of 285 NBA players with a severe ankle, knee or hip injury (2008–2019), 69% were still in the NBA one year later and 45% two years later; of those still playing, 30% (one year) and 37% (two years) matched their pre-injury games played. — [Bullock et al., PNAS Nexus 2022](https://ora.ox.ac.uk/objects/uuid:111f999a-0bd1-469f-9270-43c9daf77f12)
- DARKO raises its learning rate for players who change teams and pulls every player toward average between seasons; it describes no special handling of injury layoffs. — [DARKO, About](https://darko.app/about)

### Inferences
- Suggested default probabilities of playing: Out 0; Doubtful 0.03; Questionable 0.55 from a morning report and 0.50 from a late-afternoon report, shifted to about 0.70 for players averaging 28+ minutes and about 0.40 for deep-bench players; Probable 0.90; Available 1.0 for rotation players. These blend the 2026 tracker (first designation) with the small own sample and should be re-estimated from a full season of reports.
- Questionable drops from 59% (10 a.m.) to 51% (5 p.m.) in the own sample because players who are going to play get upgraded to Available during the day, leaving a more doubtful residue. The right probability therefore depends on the time the model runs.
- For a Questionable player, compute the game twice (plays at about 95% of normal minutes; sits with minutes redistributed) and probability-weight the two results. Averaging matters for moneyline because win probability is not linear in rating.
- Compare the model with sportsbook prices only when both reflect the same report; otherwise an apparent edge is usually stale injury information, since books re-price within seconds.
- Rest is partly predictable from public facts: second night of a back-to-back, road game, a star aged 35+ or with 34,000 minutes, not a national TV or Cup game, and late-season games for teams with nothing to play for. The day-before deadline for the report does not apply to back-to-back second nights (1 p.m. on game day), so those games carry the most late uncertainty.
- For returns from long absences, a cautious default is to cap projected minutes in the first games back and let a fast-moving minutes estimate (half-life of about two games, as in DARKO) take over; no data were found to set the cap.

### Gaps
- No multi-season published study of play rates by status was found; the tracker covers 2026 only and could not be re-verified, and the own sample covers three weeks. A full-season rebuild from the official PDFs is feasible but was blocked here.
- No systematic data on minutes in the first games back from a long absence; only news anecdotes surfaced in search summaries (first-game minutes of roughly 16 to 25 for returning stars), which were not verified.
- An Achilles-rupture study surfaced in search (value over replacement about 24% below pre-injury two seasons later) but its page could not be opened.
- No published estimate of the size of the second-night back-to-back effect by player was found beyond FiveThirtyEight's team-level 46 Elo points.
- Whether and how often the Player Participation Policy has reduced star rest since 2023-24 was not quantified in any source read.

## 6. How much does adding player availability improve accuracy over a team-rating-only model?

### Takeaway
Measured gains are consistent and modest: about 0.3 to 0.4 points less average miss on the final margin (roughly 3%) and 1 to 2 percentage points more winners picked, rising in seasons with heavy absences (2020-21) and vanishing when player information is used only to set preseason ratings. With perfect knowledge of minutes, preseason player ratings explain 15 to 20% of game-margin variance against 9% for last season's team rating.

### Cited Findings
- Dunks & Threes, player-based model versus a baseline of each team's opponent-adjusted net rating (seeded by a preseason projection that fades). Backtest 2005-06 to 2023-24 (24,425 games, each season predicted by a model trained on earlier seasons): average miss on final margin 9.6 against 9.9 points; winners picked 67.8% against 66.3%. Live record 2024-25 to 2025-26 (2,643 games): 11.0 against 11.4 points; 68.4% against 67.5%. The page notes errors are larger in recent seasons for every model. — [Dunks & Threes, About EPM](https://dunksandthrees.com/about/epm)
- **[own calculation]** FiveThirtyEight's archived game file holds, for every game, its pure Elo probability (game results and home court only) and its player-based probability (RAPTOR ratings, depth charts with injuries, rest, travel, altitude and, from 2020-21, a partial Elo blend). Regular season, same games, margin implied by 538's ÷28 rule:

| Season | Games | Winners picked: player-based / Elo | Brier: player-based / Elo | Avg miss on margin: player-based / Elo |
|---|---|---|---|---|
| 2019-20 | 1,059 | 64.9% / 63.9% | .2200 / .2223 | 10.21 / 10.23 |
| 2020-21 | 1,080 | 63.5% / 60.8% | .2202 / .2336 | 10.92 / 11.36 |
| 2021-22 | 1,230 | 66.6% / 64.5% | .2167 / .2272 | 10.91 / 11.25 |
| 2022-23 | 1,230 | 64.6% / 63.1% | .2205 / .2297 | 9.89 / 10.22 |
| 2019-20 to 2022-23 | 4,599 | 64.9% / 63.1% | .2193 / .2283 | 10.48 / 10.77 |
| 2015-16 to 2018-19 ("CARM-Elo"/CARMELO column) | 4,920 | 66.6% / 66.5% | .2113 / .2122 | 9.82 / 9.85 |

  — data: [FiveThirtyEight nba_elo.csv (archived 24 Oct 2023)](https://web.archive.org/web/20231024142254/https://projects.fivethirtyeight.com/nba-model/nba_elo.csv); definitions: [How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- FiveThirtyEight's own conclusion from testing in 2020: about 35% weight on Elo and 65% on player-based talent "produces the best predictive results for future games", with the Elo share varying from 0 to 55% by roster continuity. The original motive for the player model was that Elo could not see injuries, trades or rest. — [FiveThirtyEight, How Our NBA Predictions Work (archived)](https://web.archive.org/web/2023/https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/)
- Hoop Impact Bench, 2020-21 to 2025-26 (7,230 games, actual minutes used): last season's team rating gives a team net error of 4.08 and game-margin R² of .092; preseason player metrics give 2.79 to 3.50 and .154 to .205; plain RAPM fitted on the same season (an in-sample ceiling) gives 1.51 and .267. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Minutes alone carry signal: rating every established player 0 and every sub-250-minute player or rookie −2.0 already reaches game R² .125 and a .678 correlation with team win % in the same benchmark. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Dunks & Threes describes player-driven team ratings as more accurate than traditional team ratings and "more flexible at the start of the season, when there are injuries, and following trades". — [Dunks & Threes](https://dunksandthrees.com/)
- A 2026 review of NBA analytics concludes that availability prediction is still emerging and that no system it retained prospectively tests an availability or lineup rule against a credible alternative. — [arXiv 2609.27245](https://arxiv.org/pdf/2609.27245)

### Inferences
- The gain is concentrated where rosters differ from the recent past: the start of a season, after trades, and when stars sit. In 2020-21, a season of constant absences, the player-based forecast picked 2.7 points more winners than Elo; in 2015-16 to 2017-18, when player projections only set preseason ratings, there was no gain.
- The FiveThirtyEight comparison overstates the pure effect of availability a little, because the player-based forecast also had rest, travel and altitude terms that pure Elo lacked.
- A realistic target for a one-person model is to match these published gains: roughly 0.3 points of average margin error over its own team-only baseline. A much larger measured gain would suggest look-ahead leakage (for example, using actual minutes or back-filled ratings).
- A strong team-only rating updated game by game already contains most of the information; player data should be layered on as an adjustment (who is missing tonight relative to the lineup that produced the team rating), which is how FiveThirtyEight's blend weights by roster continuity.

### Gaps
- No public study runs one model with and without availability inputs on the same games while holding everything else fixed; the comparisons above each change more than one thing.
- The archived FiveThirtyEight file has no betting lines, so the gap between these forecasts and the closing line on the same games was not computed here.
- Dunks & Threes does not publish season-by-season results or a comparison with market closing lines.

## 7. What simple approaches work with only box-score data, and how good are they?

### Takeaway
A box-score-only rating summed by projected minutes captures roughly half of the improvement that the best hybrid metrics achieve over last season's team rating, and BPM 2.0 is the best documented choice because its full formula is public. Older box-score aggregates (PER, Win Shares) test clearly worse and break down when rosters change, and the box score's main blind spot is defense.

### Cited Findings
- BPM 2.0 can be computed from standard box scores with the published coefficients, position and role estimates and team adjustment listed in section 1. — [Basketball-Reference, About BPM 2.0](https://www.basketball-reference.com/about/bpm2.html)
- How BPM compares (2020-21 to 2025-26, 7,230 games): team net error 3.50 for BPM against 2.79 to 3.32 for the hybrids, 4.08 for last season's team rating and 5.04 for no information; game-margin R² .154 for BPM against .154 to .205 for the hybrids and .092 for last season's team. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- Earlier test (2013-14 to 2019-20): BPM 2.71 RMSE against EPM 2.48, RPM 2.60, RAPTOR 2.63; WS/48 2.85; team-adjusted PER 3.12; PER 3.20. — [Dunks & Threes, NBA Player Metric Comparison](https://dunksandthrees.com/blog/metric-comparison)
- Team win % test (2020-21 to 2022-23): BPM R² .514 against LEBRON .555 and DARKO .523. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)
- PER and Win Shares predict stable rosters to within about 3 points but degrade substantially for teams with low continuity, suggesting they misassign credit among teammates. — [Nylon Calculus, 8 Jan 2019](https://fansided.com/2019/01/08/nylon-calculus-best-advanced-stat)
- Game Score (Hollinger), a per-game production total: PTS + 0.4·FG − 0.7·FGA − 0.4·(FTA − FT) + 0.7·ORB + 0.3·DRB + STL + 0.7·AST + 0.7·BLK − 0.4·PF − TOV. — [Basketball-Reference glossary](https://www.basketball-reference.com/about/glossary.html)
- Box-score information is more predictive than on/off information at season scale: RAPTOR weighted its box component 0.85 and its on-off component 0.21. — [FiveThirtyEight, How Our RAPTOR Metric Works (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/)
- In OpenRAPM's simulated league with known true impacts, plain RAPM reached a correlation of 0.74 with true offensive impact, the box-score prior alone 0.88, and the two combined 0.93. — [OpenRAPM README](https://github.com/bbstats/openrapm)
- The weakness is defense: traditional defensive stats explained about 0.3 of RAPM variance against about 0.6 with tracking data; Engelmann notes "the only defensive stats in the box score are rebounds, blocks and steals" and that his box-score model struggles more on defense than offense; Basketball-Reference says the same of BPM. — [FiveThirtyEight, RAPTOR (archived)](https://web.archive.org/web/20230601000000/https://fivethirtyeight.com/features/how-our-raptor-metric-works/); [Engelmann on 5x5, 4 May 2026](https://www.roycewebb.com/p/how-to-build-an-nba-box-score-metric); [Basketball-Reference, About BPM 2.0](https://www.basketball-reference.com/about/bpm2.html)
- Recipe for a home-made box-score metric (Engelmann): one row per player, target = multi-season RAPM, inputs = per-100-possession stats (z-scored), separate offensive and defensive regressions, each player weighted by the inverse of his RAPM standard error, model chosen by leave-one-out error; fitted on 2016-17 to 2025-26. No coefficients are published. — [Engelmann on 5x5, 4 May 2026](https://www.roycewebb.com/p/how-to-build-an-nba-box-score-metric)
- Known failure cases for BPM: low-assist bigs and rookies (Walker Kessler about −3 on BPM and +1 on DARKO in November 2023; Chet Holmgren about +6 on BPM and +1.2 on DARKO early in his first season). — [APBRmetrics forum](https://apbr.org/metrics/viewtopic.php?t=10046)
- Conventions for players with little data: −2.0 for anyone unrated or under 250 minutes the season before, rookies included. — [Hoop Impact Bench README](https://github.com/lumahoops/hoop-impact-bench)

### Inferences
- On the Hoop Impact Bench figures BPM closes about 45% of the gap in team net error between last season's team rating and the best metric ((4.08 − 3.50) ÷ (4.08 − 2.79)) and about 55% of the gap in game R² ((.154 − .092) ÷ (.205 − .092)). The simplest "who is on the floor" rule (0 for established players, −2 for fringe players) closes about 30% of the R² gap.
- A workable free pipeline is therefore: a prior-informed BPM (blend last season, this season and career, padded toward −2.0 for small samples) as the in-house rating that can be rebuilt for any past date, cross-checked against or averaged with DARKO and xRAPM for current games.
- "Minutes-weighted missing production" is the right first-order injury adjustment: tonight's team rating minus the usual-lineup team rating, both computed as Σ rating × minutes/48, with absent players' minutes redistributed to the next players at their own ratings.
- Game Score, PER and Win Shares are poor substitutes for a plus-minus-scaled rating because they are not in points per 100 possessions and credit volume; if used they must be rescaled (Hoop Impact Bench's advice for PER is to subtract 15 and rescale).

### Gaps
- No published test of Game Score per minute, or of a simple "usage-weighted missing production" rule, as a game predictor was found.
- The formula for DRE (Daily RAPM Estimate), a simpler box-score alternative mentioned on Basketball-Reference's BPM page, could not be retrieved (the original Nylon Calculus article returned a 404).
- No public test isolates how much a box-score rating loses specifically on defense-heavy players in game prediction.
