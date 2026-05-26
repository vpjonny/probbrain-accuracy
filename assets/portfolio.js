/*
 * ProbBrain Virtual Portfolio — math library
 * ------------------------------------------
 * Pure, browser-loadable ES module. No build step, no external deps.
 * Linked publicly from /portfolio so any reader can audit the math.
 *
 * Inputs (resolved trades): each carries
 *   signal_id, market_id, market_price_at_signal, our_estimate,
 *   outcome ("YES"|"NO"), correct (bool), direction (YES_UNDERPRICED|NO_UNDERPRICED),
 *   resolved_at, category, volume_usdc, posted_at
 *
 * All money in USD; probabilities are 0..1.
 *
 * Conventions:
 *   - YES_UNDERPRICED → buy YES at `market_price_at_signal`, payoff (1/p - 1) on win
 *   - NO_UNDERPRICED  → buy NO at (1 - market_price_at_signal), payoff (1/(1-p) - 1) on win
 *   - "win" = outcome matches the side we bet
 *   - Slippage modeled as linear impact: effective_fill_price = post_price * (1 + impact_rate * stake/volume)
 *     (move = stake-as-fraction-of-book times an impact rate; default 0.001 = 0.1%)
 */

export const DEFAULTS = {
    bankrollStart: 10_000,
    kellyFraction: 1 / 8,        // 1/8 Kelly per spec v3
    perBetCap: 0.01,             // 1% of bankroll cap
    impactRate: 0.001,           // 0.1% linear impact per unit-of-book
    liquidityCap: 0.005,         // effective stake ≤ 0.5% of volume (default tradable)
    liquidityCapConservative: 0.01, // 1% of volume — "conservative" toggle
    warmupMinResolutions: 20,    // headline KPIs hidden below this
};

/* ----- core sizing ----- */

/** Decimal odds you'd bet at given a YES-side price `p`. */
function yesOdds(p) { return 1 / Math.max(p, 1e-9); }
/** Decimal odds you'd bet at given a NO-side at `(1 - p)`. */
function noOdds(p) { return 1 / Math.max(1 - p, 1e-9); }

/**
 * Fractional Kelly stake (in $) given a directional bet.
 *
 * For YES_UNDERPRICED:
 *   q = our_estimate (subjective P(YES))
 *   b = yesOdds(p) - 1   (net decimal payoff per $1 staked)
 *   kelly = (b*q - (1-q)) / b
 * For NO_UNDERPRICED:
 *   q = 1 - our_estimate
 *   b = noOdds(p) - 1
 *
 * Returns the fractional Kelly $ stake, capped by `perBetCap` × bankroll
 * and floored at 0 (never bet a negative edge).
 */
export function kellyStake({ ourEstimate, marketPrice, direction, bankroll, fraction = DEFAULTS.kellyFraction, cap = DEFAULTS.perBetCap }) {
    if (!Number.isFinite(ourEstimate) || !Number.isFinite(marketPrice) || marketPrice <= 0 || marketPrice >= 1) {
        return 0;
    }
    let q, b;
    if (direction === "YES_UNDERPRICED") {
        q = ourEstimate;
        b = yesOdds(marketPrice) - 1;
    } else {
        q = 1 - ourEstimate;
        b = noOdds(marketPrice) - 1;
    }
    if (b <= 0) return 0;
    const fullKelly = (b * q - (1 - q)) / b;
    if (!Number.isFinite(fullKelly) || fullKelly <= 0) return 0;
    const fractioned = fullKelly * fraction;
    const dollar = fractioned * bankroll;
    return Math.min(dollar, cap * bankroll);
}

/**
 * Apply liquidity cap + linear-impact slippage.
 *
 * Returns { effectiveStake, effectiveFillPrice, slippageDollars, capped }.
 * `effectiveStake` is what actually gets deployed; the rest is left in the bankroll.
 * `effectiveFillPrice` is the avg price after walking the book by `impactRate × stake/volume`.
 */
export function applyLiquidity({ kelly, marketPrice, volume, direction, impactRate = DEFAULTS.impactRate, liquidityCap = DEFAULTS.liquidityCap }) {
    if (!Number.isFinite(volume) || volume <= 0) {
        return { effectiveStake: 0, effectiveFillPrice: marketPrice, slippageDollars: 0, capped: true };
    }
    const maxByBook = liquidityCap * volume;
    const effectiveStake = Math.min(kelly, maxByBook);
    const capped = effectiveStake < kelly - 1e-6;
    const sidePrice = direction === "YES_UNDERPRICED" ? marketPrice : 1 - marketPrice;
    const move = impactRate * (effectiveStake / volume);
    const effectiveSidePrice = Math.min(0.999, sidePrice * (1 + move));
    const effectiveFillPrice = direction === "YES_UNDERPRICED" ? effectiveSidePrice : 1 - effectiveSidePrice;
    const slippageDollars = effectiveStake * (effectiveSidePrice / sidePrice - 1);
    return { effectiveStake, effectiveFillPrice, slippageDollars, capped };
}

/** Resolve a single bet → $ P&L. */
export function resolveTrade({ effectiveStake, effectiveFillPrice, direction, outcome }) {
    if (effectiveStake <= 0) return 0;
    const sidePrice = direction === "YES_UNDERPRICED"
        ? effectiveFillPrice
        : 1 - effectiveFillPrice;
    const won = (direction === "YES_UNDERPRICED" && outcome === "YES")
              || (direction === "NO_UNDERPRICED"  && outcome === "NO");
    if (won) return effectiveStake * (1 / sidePrice - 1);
    return -effectiveStake;
}

/* ----- curve construction ----- */

/**
 * Build an equity curve from a chronologically-sorted list of resolved trades.
 * Each trade gets sized off the *bankroll at the time of the bet*, not the final
 * bankroll. Open positions are sized at posted_at; P&L lands at resolved_at.
 *
 * Returns { curve: [{ts, equity, pnlDelta, signal_id}], trades: [{...full ledger row}] }.
 */
export function buildCurve(resolvedSignals, {
    bankroll = DEFAULTS.bankrollStart,
    kellyFraction = DEFAULTS.kellyFraction,
    perBetCap = DEFAULTS.perBetCap,
    impactRate = DEFAULTS.impactRate,
    liquidityCap = DEFAULTS.liquidityCap,
    skipNoLiquidity = false,           // if true, drop signals with 0 stake after cap
} = {}) {
    // Sort by posted_at (or resolved_at fallback).
    const ordered = [...resolvedSignals]
        .filter(s => s && s.outcome && s.resolved_at)
        .sort((a, b) => {
            const at = a.actually_posted_at || a.posted_at || a.created_at || a.resolved_at;
            const bt = b.actually_posted_at || b.posted_at || b.created_at || b.resolved_at;
            return new Date(at) - new Date(bt);
        });

    let equity = bankroll;
    const curve = [];
    const trades = [];
    for (const s of ordered) {
        const marketPrice = Number(s.market_price_at_signal ?? s.market_yes_price);
        const ourEst = Number(s.our_estimate ?? s.our_calibrated_estimate);
        const direction = s.direction;
        const volume = Number(s.volume_usdc ?? 0);

        const kelly = kellyStake({
            ourEstimate: ourEst, marketPrice, direction,
            bankroll: equity, fraction: kellyFraction, cap: perBetCap,
        });
        const liq = applyLiquidity({
            kelly, marketPrice, volume, direction, impactRate, liquidityCap,
        });
        if (skipNoLiquidity && liq.effectiveStake <= 0) continue;

        const pnl = resolveTrade({
            effectiveStake: liq.effectiveStake,
            effectiveFillPrice: liq.effectiveFillPrice,
            direction, outcome: s.outcome,
        });
        equity += pnl;
        const row = {
            signal_id: s.signal_id,
            market_id: s.market_id,
            question: s.question,
            category: s.category,
            posted_at: s.actually_posted_at || s.posted_at || s.created_at || null,
            resolved_at: s.resolved_at,
            direction,
            our_estimate: ourEst,
            market_price_at_post: marketPrice,
            kelly_stake: kelly,
            effective_stake: liq.effectiveStake,
            effective_fill_price: liq.effectiveFillPrice,
            slippage_dollars: liq.slippageDollars,
            volume_at_post: volume,
            liquidity_capped: liq.capped,
            outcome: s.outcome,
            won: pnl > 0,
            pnl,
            equity_after: equity,
            source: s._source || "published",
        };
        trades.push(row);
        curve.push({
            ts: s.resolved_at,
            equity,
            pnlDelta: pnl,
            signal_id: s.signal_id,
        });
    }
    return { curve, trades, finalEquity: equity, bankroll };
}

/* ----- stats ----- */

/** Profit factor: gross wins ÷ gross losses. Infinity if no losses, 0 if no trades. */
export function profitFactor(trades) {
    let win = 0, loss = 0;
    for (const t of trades) {
        if (t.pnl > 0) win += t.pnl;
        else loss += -t.pnl;
    }
    if (loss === 0) return win > 0 ? Infinity : 0;
    return win / loss;
}

/** Expectancy in $ per $1 staked. */
export function expectancy(trades) {
    let staked = 0, pnl = 0;
    for (const t of trades) {
        staked += t.effective_stake;
        pnl += t.pnl;
    }
    if (staked === 0) return 0;
    return pnl / staked;
}

/** Sortino: mean return / downside-deviation. Returns are per-trade ROI on stake. */
export function sortino(trades, mar = 0) {
    const rets = trades.filter(t => t.effective_stake > 0).map(t => t.pnl / t.effective_stake);
    if (rets.length === 0) return 0;
    const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
    const downside = rets.filter(r => r < mar).map(r => (r - mar) ** 2);
    if (downside.length === 0) return mean > 0 ? Infinity : 0;
    const dd = Math.sqrt(downside.reduce((a, b) => a + b, 0) / downside.length);
    if (dd === 0) return mean > 0 ? Infinity : 0;
    return (mean - mar) / dd;
}

/** Calmar: CAGR / |MaxDD%|. Days from first to last trade. */
export function calmar(curve, bankrollStart) {
    if (!curve.length) return 0;
    const finalEquity = curve[curve.length - 1].equity;
    const firstTs = new Date(curve[0].ts).getTime();
    const lastTs = new Date(curve[curve.length - 1].ts).getTime();
    const days = Math.max(1, (lastTs - firstTs) / 86400000);
    const cagr = Math.pow(finalEquity / bankrollStart, 365 / days) - 1;
    const dd = maxDrawdown(curve, bankrollStart);
    if (!dd.pctOfPeak) return cagr > 0 ? Infinity : 0;
    return cagr / Math.abs(dd.pctOfPeak);
}

/** Max drawdown: largest peak-to-trough drop in equity. */
export function maxDrawdown(curve, bankrollStart) {
    let peak = bankrollStart;
    let maxDD = 0;
    let maxDDPct = 0;
    for (const p of curve) {
        if (p.equity > peak) peak = p.equity;
        const dd = peak - p.equity;
        if (dd > maxDD) {
            maxDD = dd;
            maxDDPct = peak === 0 ? 0 : dd / peak;
        }
    }
    return { dollars: maxDD, pctOfPeak: maxDDPct };
}

/* ----- publication premium ----- */

/**
 * Bootstrap CI on a statistic.
 * Resamples `data` with replacement `iters` times, applies `statFn`, returns
 * { mean, lower, upper, samples } at the given confidence level.
 */
export function bootstrapCI(data, statFn, { iters = 1000, ci = 0.95 } = {}) {
    if (!data.length) return { mean: 0, lower: 0, upper: 0, samples: [] };
    const stats = new Array(iters);
    const n = data.length;
    for (let i = 0; i < iters; i++) {
        const resample = new Array(n);
        for (let j = 0; j < n; j++) resample[j] = data[(Math.random() * n) | 0];
        stats[i] = statFn(resample);
    }
    stats.sort((a, b) => a - b);
    const lo = stats[Math.floor(iters * (1 - ci) / 2)];
    const hi = stats[Math.floor(iters * (1 - (1 - ci) / 2))];
    const mean = stats.reduce((a, b) => a + b, 0) / iters;
    return { mean, lower: lo, upper: hi, samples: stats };
}

/**
 * Publication Premium = ROI(published-only) − ROI(shadow-included universe).
 *
 * The hypothesis is: do we systematically publish our best calls? If the
 * delta is positive AND its bootstrap CI excludes zero, the answer is "yes,
 * and that's a selection-bias warning, not a brag." If the CI crosses zero,
 * we explicitly say "not statistically significant" — preempts the gotcha.
 *
 * `published` and `universe` are arrays of trade rows from buildCurve().
 */
export function publicationPremium(published, universe, { iters = 1000 } = {}) {
    const roiOf = (trades) => {
        if (!trades.length) return 0;
        let pnl = 0, staked = 0;
        for (const t of trades) { pnl += t.pnl; staked += t.effective_stake; }
        return staked === 0 ? 0 : pnl / staked;
    };

    const publishedROI = roiOf(published);
    const universeROI = roiOf(universe);
    const delta = publishedROI - universeROI;

    // Bootstrap the delta by resampling both pools.
    const ci = bootstrapCI(
        [...published.map(t => ({ ...t, _pool: "p" })), ...universe.map(t => ({ ...t, _pool: "u" }))],
        (sample) => roiOf(sample.filter(s => s._pool === "p")) - roiOf(sample.filter(s => s._pool === "u")),
        { iters, ci: 0.95 },
    );

    // Two-sided p-value: fraction of resamples on the wrong side of zero,
    // doubled. Crude but standard enough for an audit panel.
    const sign = delta >= 0 ? 1 : -1;
    const wrongSide = ci.samples.filter(s => s * sign <= 0).length;
    const p = Math.min(1, 2 * (wrongSide / ci.samples.length));

    return {
        published_roi: publishedROI,
        universe_roi: universeROI,
        delta,
        ci_low: ci.lower,
        ci_high: ci.upper,
        p_value: p,
        significant: ci.lower > 0 || ci.upper < 0,
    };
}

/* ----- universe joining ----- */

/**
 * Match published signals against resolved.json by signal_id. Adds outcome
 * + resolved_at to the signal record.
 *
 * Probability convention: we use `our_calibrated_estimate` (what users
 * actually saw on the dashboard) as the bet's subjective probability.
 * `resolved.our_estimate` is heterogeneous across the file's history (some
 * raw, some calibrated) so we treat it as a fallback only.
 */
export function joinResolved(signals, resolved) {
    // resolved.json mixes schemas: legacy entries use outcome "YES"/"NO" strings,
    // newer entries use integers 1/0. resolved_shadow.json is exclusively integers.
    // Normalize to "YES"/"NO" so resolveTrade comparisons + the buildCurve truthy
    // filter both behave consistently.
    const normOutcome = (v) => {
        if (v === 1 || v === "YES") return "YES";
        if (v === 0 || v === "NO")  return "NO";
        if (typeof v === "string")  return v.toUpperCase();
        return v;
    };
    const byId = new Map(resolved.map(r => [r.signal_id, r]));
    const out = [];
    for (const s of signals) {
        const r = byId.get(s.signal_id);
        if (!r) continue;
        const calibrated = s.our_calibrated_estimate ?? s.our_estimate ?? r.our_estimate;
        out.push({
            ...s,
            outcome: normOutcome(r.outcome),
            correct: r.correct,
            resolved_at: r.resolved_at,
            market_price_at_signal: s.market_yes_price ?? r.market_price_at_signal,
            our_estimate: calibrated,
        });
    }
    return out;
}

/* ----- formatters (for the page; pure too) ----- */

export const fmt = {
    money: (n) => (n >= 0 ? "+$" : "−$") + Math.abs(n).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ","),
    moneyAbs: (n) => "$" + n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ","),
    pct: (n, digits = 1) => (n >= 0 ? "+" : "") + (n * 100).toFixed(digits) + "%",
    pctAbs: (n, digits = 1) => Math.abs(n * 100).toFixed(digits) + "%",
    ratio: (n, digits = 2) => Number.isFinite(n) ? n.toFixed(digits) : "∞",
    date: (iso) => iso ? iso.slice(0, 10) : "—",
};
