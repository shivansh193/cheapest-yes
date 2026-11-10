"""Evaluation. `python -m cy.eval` (or `make eval`) writes:

  artifacts/eval.json           numbers the dashboard reads
  reports/intent_calibration.png
  reports/criteo_qini.png
  reports/sim_policies.png
  docs/EVAL.md                  the tables quoted in the README

Three parts:
  1. Intent model on public data (UCI test split): AUC, Brier score, reliability curve.
  2. Uplift method on public data (Criteo uplift v2.1, a random sample): the same T-learner
     recipe, scored with a Qini curve. Criteo's treatment is ad exposure, not a checkout
     incentive, so this checks the method, not the store.
  3. Simulator A/B: a fresh population (different seed from training) with hidden true
     responses. Every policy is scored on the same shoppers with common random numbers.
     Simulator results, not field results.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402

from . import sim  # noqa: E402
from .config import DEFAULT, INCENTIVES, LABELS  # noqa: E402
from .data import CRITEO_GZ, load_uci  # noqa: E402
from .economics import amounts, incentive_cost  # noqa: E402
from .engine import choose_batch  # noqa: E402
from .models import LGB_PARAMS, ARTIFACTS, get_bundle  # noqa: E402
from .train import train_intent, with_intent  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
EVAL_SEED = 2026
N_EVAL = 20_000
N_BOOT = 1000

INK, MUTED, ACCENT, GOOD = "#1f2937", "#6b7280", "#2563eb", "#059669"


def _style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=12, color=INK)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(alpha=0.25)


# ---------------------------------------------------------------- 1. intent
def eval_intent() -> dict:
    uci = load_uci()
    model, (Xte, yte), auc = train_intent(uci)
    p = model.predict(Xte)
    frac_pos, mean_pred = calibration_curve(yte, p, n_bins=10, strategy="quantile")
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    ax.plot([0, 1], [0, 1], ls="--", color=MUTED, lw=1, label="perfectly calibrated")
    ax.plot(mean_pred, frac_pos, marker="o", color=ACCENT, label=f"intent model (AUC {auc:.3f})")
    _style(ax, "Intent model calibration (UCI test split)", "predicted P(buy)", "observed purchase rate")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(REPORTS / "intent_calibration.png", dpi=140)
    plt.close(fig)
    return {"auc": round(float(auc), 4), "brier": round(float(brier_score_loss(yte, p)), 4),
            "n_test": int(len(yte)), "base_rate": round(float(yte.mean()), 4)}


# ---------------------------------------------------------------- 2. Criteo Qini
def _criteo_sample(frac: float = 0.12, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    parts = []
    for chunk in pd.read_csv(CRITEO_GZ, chunksize=1_000_000):
        parts.append(chunk[rng.random(len(chunk)) < frac])
    return pd.concat(parts, ignore_index=True)


def qini_curve(uplift: np.ndarray, y: np.ndarray, t: np.ndarray, n_points: int = 100):
    order = np.argsort(-uplift)
    y, t = y[order], t[order]
    cy_t, cy_c = np.cumsum(y * t), np.cumsum(y * (1 - t))
    n_t, n_c = np.cumsum(t), np.cumsum(1 - t)
    q = cy_t - cy_c * np.divide(n_t, n_c, out=np.zeros_like(n_t, dtype=float), where=n_c > 0)
    idx = np.linspace(0, len(y) - 1, n_points).astype(int)
    x = (idx + 1) / len(y)
    return np.concatenate([[0], x]), np.concatenate([[0], q[idx]])


def eval_criteo() -> dict | None:
    if not CRITEO_GZ.exists():
        print("Criteo file not found; skipping (run: python -c 'from cy.data import load_criteo; load_criteo(1)')")
        return None
    t0 = time.time()
    df = _criteo_sample()
    feats = [f"f{i}" for i in range(12)]
    rng = np.random.default_rng(1)
    test = rng.random(len(df)) < 0.3
    tr, te = df[~test], df[test]
    out = {"n_sample": int(len(df)), "n_test": int(test.sum()), "outcome": "visit",
           "treatment_rate": round(float(df["treatment"].mean()), 3), "visit_rate": round(float(df["visit"].mean()), 4)}
    params = {**LGB_PARAMS, "n_estimators": 200}
    m1 = lgb.LGBMClassifier(random_state=0, **params).fit(tr.loc[tr.treatment == 1, feats], tr.loc[tr.treatment == 1, "visit"])
    m0 = lgb.LGBMClassifier(random_state=0, **params).fit(tr.loc[tr.treatment == 0, feats], tr.loc[tr.treatment == 0, "visit"])
    u = m1.predict_proba(te[feats])[:, 1] - m0.predict_proba(te[feats])[:, 1]
    y, t = te["visit"].to_numpy(), te["treatment"].to_numpy()
    x, q = qini_curve(u, y, t)
    total = q[-1]
    rand = x * total
    area_model = np.trapezoid(q, x) if hasattr(np, "trapezoid") else np.trapz(q, x)
    area_rand = np.trapezoid(rand, x) if hasattr(np, "trapezoid") else np.trapz(rand, x)
    out["qini_coefficient"] = round(float((area_model - area_rand) / max(len(y), 1)), 6)
    out["auuc_ratio_vs_random"] = round(float(area_model / area_rand), 3) if area_rand else None
    top = int(0.2 * len(y))
    o = np.argsort(-u)[:top]
    yt, tt = y[o], t[o]
    out["top20_uplift"] = round(float(yt[tt == 1].mean() - yt[tt == 0].mean()), 4)
    out["overall_uplift"] = round(float(y[t == 1].mean() - y[t == 0].mean()), 4)
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.plot(x * 100, q, color=ACCENT, label="T-learner (LightGBM)")
    ax.plot(x * 100, rand, ls="--", color=MUTED, label="random targeting")
    _style(ax, "Qini curve, Criteo uplift v2.1 (visit)", "% of users targeted, ranked by predicted uplift", "incremental visits")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(REPORTS / "criteo_qini.png", dpi=140)
    plt.close(fig)
    out["seconds"] = round(time.time() - t0, 1)
    return out


# ---------------------------------------------------------------- 3. simulator A/B
def _score_policy(choice: np.ndarray, pop: sim.Population, u: np.ndarray, v: np.ndarray, cfg=DEFAULT) -> dict[str, np.ndarray]:
    """Per-shopper realised and expected outcomes for a policy (common random numbers u, v)."""
    n = len(choice)
    idx = np.array([INCENTIVES.index(c) for c in choice])
    p = pop.p_true.to_numpy()[np.arange(n), idx]
    plp = pop.pl_true.to_numpy()[np.arange(n), idx]
    p_none = pop.p_true["none"].to_numpy()
    item = pop.signals["cart_value"].to_numpy()
    total = np.array([amounts(c, inc, cfg).total for c, inc in zip(item, choice)])
    inc_cost = np.array([incentive_cost(c, inc, cfg) for c, inc in zip(item, choice)])
    margin = cfg.gross_margin_rate * item
    fee = cfg.paypal_pct * total + cfg.paypal_fixed
    buy = (u < p).astype(float)
    used_pl = (v < plp).astype(float) * buy
    pl_extra = used_pl * cfg.paylater_extra_pct * total
    profit = buy * (margin - inc_cost - fee) - pl_extra
    exp_profit = p * (margin - inc_cost - fee - plp * cfg.paylater_extra_pct * total)
    spend = buy * inc_cost + pl_extra * (choice == "paylater")
    would_buy = (u < p_none).astype(float)
    leakage = spend * would_buy * (choice != "none")
    return {"profit": profit, "exp_profit": exp_profit, "buy": buy, "spend": spend, "leakage": leakage,
            "offered": (choice != "none").astype(float)}


def _boot_ci(x: np.ndarray, rng, n_boot=N_BOOT) -> tuple[float, float]:
    n = len(x)
    means = np.array([x[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def eval_sim() -> dict:
    b = get_bundle()
    uci = load_uci()
    pop = sim.generate(N_EVAL, uci, seed=EVAL_SEED)
    X = with_intent(pop, b.intent)
    rng = np.random.default_rng(EVAL_SEED + 1)
    u, v = rng.random(N_EVAL), rng.random(N_EVAL)

    n = N_EVAL
    true_best = (pop.p_true.to_numpy() * 0)  # oracle: argmax true expected profit
    from .economics import profit_if_buy

    item = pop.signals["cart_value"].to_numpy()
    ep = np.zeros((n, len(INCENTIVES)))
    for j, inc in enumerate(INCENTIVES):
        pib = np.array([profit_if_buy(c, inc, q) for c, q in zip(item, pop.pl_true[inc].to_numpy())])
        ep[:, j] = pop.p_true[inc].to_numpy() * pib
    del true_best
    oracle = np.array(INCENTIVES)[ep.argmax(axis=1)]

    policies = {
        "No incentive": np.array(["none"] * n),
        "Blanket 10% off": np.array(["discount_10"] * n),
        "Always show Pay Later": np.where([amounts(c, "paylater").total >= DEFAULT.paylater_min_total for c in item], "paylater", "none"),
        "Cheapest Yes": choose_batch(X, b.response).to_numpy(),
        "Cheapest Yes without Pay Later": choose_batch(X, b.response, exclude=frozenset({"paylater"})).to_numpy(),
        "Oracle (knows hidden truth)": oracle,
    }
    scored = {k: _score_policy(c, pop, u, v) for k, c in policies.items()}
    boot = np.random.default_rng(7)
    results = {}
    base = scored["No incentive"]["profit"]
    blanket = scored["Blanket 10% off"]["profit"]
    always_pl = scored["Always show Pay Later"]["profit"]
    for name, s in scored.items():
        per = 1000  # report per 1,000 shoppers
        lo, hi = _boot_ci(s["profit"], boot)
        d_none = s["profit"] - base
        d_bl = s["profit"] - blanket
        r = {
            "profit_per_1k": round(s["profit"].mean() * per, 0),
            "profit_per_1k_ci": [round(lo * per, 0), round(hi * per, 0)],
            "expected_profit_per_1k": round(s["exp_profit"].mean() * per, 0),
            "conversion": round(s["buy"].mean(), 4),
            "conversion_ci": [round(x, 4) for x in _boot_ci(s["buy"], boot)],
            "offer_rate": round(s["offered"].mean(), 4),
            "incentive_spend_per_1k": round(s["spend"].mean() * per, 0),
            "leakage_per_1k": round(s["leakage"].mean() * per, 0),
            "leakage_share_of_spend": round(s["leakage"].sum() / s["spend"].sum(), 3) if s["spend"].sum() else 0.0,
            "lift_vs_none_per_1k": round(d_none.mean() * per, 0),
            "lift_vs_none_ci": [round(x * per, 0) for x in _boot_ci(d_none, boot)],
            "lift_vs_blanket_per_1k": round(d_bl.mean() * per, 0),
            "lift_vs_blanket_ci": [round(x * per, 0) for x in _boot_ci(d_bl, boot)],
            "lift_vs_always_paylater_per_1k": round((s["profit"] - always_pl).mean() * per, 0),
            "lift_vs_always_paylater_ci": [round(x * per, 0) for x in _boot_ci(s["profit"] - always_pl, boot)],
            "mix": {LABELS[k]: round(float(np.mean(policies[name] == k)), 4) for k in INCENTIVES},
        }
        results[name] = r

    cy_choice = policies["Cheapest Yes"]
    agree = float(np.mean(cy_choice == oracle))
    sig = pop.signals
    fairness = {}
    for gname, mask in {"mobile": sig.is_mobile == 1, "desktop": sig.is_mobile == 0,
                        "new visitor": sig.is_returning == 0, "returning visitor": sig.is_returning == 1}.items():
        m = mask.to_numpy()
        fairness[gname] = {"shoppers": int(m.sum()), "offer_rate": round(float(np.mean(cy_choice[m] != "none")), 4),
                           "discount_rate": round(float(np.mean(np.isin(cy_choice[m], ["discount_5", "discount_10"]))), 4)}
    by_arch = {a: {LABELS[k]: round(float(np.mean(cy_choice[pop.archetype == a] == k)), 3) for k in INCENTIVES}
               for a in sim.ARCHETYPES}

    names = list(results)
    vals = [results[k]["profit_per_1k"] for k in names]
    err = np.array([[results[k]["profit_per_1k"] - results[k]["profit_per_1k_ci"][0],
                     results[k]["profit_per_1k_ci"][1] - results[k]["profit_per_1k"]] for k in names]).T
    colors = [MUTED, MUTED, MUTED, ACCENT, "#93c5fd", "#d1d5db"]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.barh(names[::-1], vals[::-1], xerr=err[:, ::-1], color=colors[::-1], capsize=3)
    _style(ax, f"Profit per 1,000 shoppers, simulator ({N_EVAL:,} shoppers, 95% CI)", "USD", "")
    fig.tight_layout()
    fig.savefig(REPORTS / "sim_policies.png", dpi=140)
    plt.close(fig)

    return {"n_shoppers": N_EVAL, "seed": EVAL_SEED, "policies": results, "agreement_with_oracle": round(agree, 4),
            "fairness": fairness, "mix_by_hidden_archetype": by_arch}


def _md(ev: dict) -> str:
    i, c, s = ev["intent"], ev.get("criteo"), ev["sim"]
    lines = [
        "# Evaluation results",
        "",
        f"Generated by `make eval` on {ev['generated_at']}. Regenerate rather than edit.",
        "",
        "## 1. Purchase-intent model (public data)",
        "",
        "UCI Online Shoppers Purchasing Intention, stratified 80/20 split.",
        "",
        f"| Metric | Value |\n|---|---|\n| Test AUC | **{i['auc']:.3f}** |\n| Brier score | {i['brier']:.4f} |\n| Test sessions | {i['n_test']:,} |\n| Purchase rate | {i['base_rate']:.1%} |",
        "",
        "![Calibration](../reports/intent_calibration.png)",
        "",
        "## 2. Uplift method (public data)",
        "",
    ]
    if c:
        lines += [
            f"Criteo uplift v2.1, random {c['n_sample']:,}-row sample, 30% held out. Outcome: visit. "
            "Same T-learner recipe the store uses. Criteo's treatment is ad exposure, not a checkout incentive, "
            "so this validates the method only.",
            "",
            f"| Metric | Value |\n|---|---|\n| AUUC vs random targeting | **{c['auuc_ratio_vs_random']}x** |\n"
            f"| Qini coefficient (per user) | {c['qini_coefficient']} |\n| Uplift in top 20% by model | {c['top20_uplift']:.2%} |\n"
            f"| Average uplift (everyone) | {c['overall_uplift']:.2%} |",
            "",
            "![Qini](../reports/criteo_qini.png)",
            "",
        ]
    else:
        lines += ["Criteo file not present when this ran; section skipped.", ""]
    lines += [
        "## 3. Simulator A/B",
        "",
        f"{s['n_shoppers']:,} fresh simulated shoppers (seed {s['seed']}, never used in training). Each policy is "
        "scored on the same shoppers with common random numbers; 95% bootstrap CIs. Profit is after incentive cost, "
        "PayPal fees and the Pay Later surcharge. **Simulator results, not field results.**",
        "",
        "| Policy | Profit / 1k shoppers | vs no incentive | vs blanket 10% | Conversion | Offer rate | Incentive spend / 1k | Leakage / 1k |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for k, r in s["policies"].items():
        lines.append(
            f"| {k} | ${r['profit_per_1k']:,.0f} ({r['profit_per_1k_ci'][0]:,.0f}–{r['profit_per_1k_ci'][1]:,.0f}) | "
            f"{r['lift_vs_none_per_1k']:+,.0f} ({r['lift_vs_none_ci'][0]:+,.0f}–{r['lift_vs_none_ci'][1]:+,.0f}) | "
            f"{r['lift_vs_blanket_per_1k']:+,.0f} ({r['lift_vs_blanket_ci'][0]:+,.0f}–{r['lift_vs_blanket_ci'][1]:+,.0f}) | "
            f"{r['conversion']:.1%} | {r['offer_rate']:.0%} | ${r['incentive_spend_per_1k']:,.0f} | ${r['leakage_per_1k']:,.0f} |")
    cyr, ab = s["policies"]["Cheapest Yes"], s["policies"]["Cheapest Yes without Pay Later"]
    lines += [
        "",
        "Leakage = incentive cost spent on shoppers who would have bought with no incentive.",
        "",
        "![Policies](../reports/sim_policies.png)",
        "",
        "### Ablation: what Pay Later contributes",
        "",
        f"Removing Pay Later from the ladder changes profit per 1k shoppers from ${cyr['profit_per_1k']:,.0f} to "
        f"${ab['profit_per_1k']:,.0f} ({ab['profit_per_1k'] - cyr['profit_per_1k']:+,.0f}) and incentive spend from "
        f"${cyr['incentive_spend_per_1k']:,.0f} to ${ab['incentive_spend_per_1k']:,.0f}.",
        "",
        f"Against simply always showing Pay Later, Cheapest Yes adds {cyr['lift_vs_always_paylater_per_1k']:+,.0f} USD per 1k shoppers "
        f"(95% CI {cyr['lift_vs_always_paylater_ci'][0]:+,.0f} to {cyr['lift_vs_always_paylater_ci'][1]:+,.0f}). Most of the win is "
        "Pay Later itself; the engine adds the rest by spending on paid incentives only where they pay off.",
        "",
        f"Cheapest Yes picks the same incentive as the oracle (which sees the hidden truth) for "
        f"{s['agreement_with_oracle']:.0%} of shoppers.",
        "",
        "### Mix of choices",
        "",
        "| Policy | " + " | ".join(LABELS[k] for k in INCENTIVES) + " |",
        "|---|" + "---|" * len(INCENTIVES),
    ]
    for k, r in s["policies"].items():
        lines.append(f"| {k} | " + " | ".join(f"{r['mix'][LABELS[x]]:.0%}" for x in INCENTIVES) + " |")
    lines += ["", "### Cheapest Yes choices by hidden archetype", "",
              "| Hidden archetype | " + " | ".join(LABELS[k] for k in INCENTIVES) + " |", "|---|" + "---|" * len(INCENTIVES)]
    for a, m in s["mix_by_hidden_archetype"].items():
        lines.append(f"| {a} | " + " | ".join(f"{m[LABELS[x]]:.0%}" for x in INCENTIVES) + " |")
    lines += ["", "### Fairness check", "", "| Group | Shoppers | Offer rate | Discount rate |", "|---|---|---|---|"]
    for g, f in s["fairness"].items():
        lines.append(f"| {g} | {f['shoppers']:,} | {f['offer_rate']:.0%} | {f['discount_rate']:.0%} |")
    lines += [
        "",
        "## Limits",
        "",
        "- The store's incentive responses come from a simulator whose archetypes and effect sizes are assumptions. "
        "The eval shows the engine recovers those effects from a randomized log and turns them into profit; "
        "it does not show what real shoppers would do.",
        "- Browsing behaviour is grounded in real UCI sessions, but cart, hesitation and comparison signals are simulated.",
        "- The simulator A/B ignores the daily budget and per-shopper caps (the live engine enforces both).",
        "- Criteo validates the uplift-modelling recipe on real randomized data, in a different domain (advertising).",
        "",
    ]
    return "\n".join(lines)


def main(skip_criteo: bool = False) -> dict:
    REPORTS.mkdir(exist_ok=True)
    t0 = time.time()
    ev = {"generated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    ev["intent"] = eval_intent()
    print("intent", ev["intent"])
    ev["criteo"] = None if skip_criteo else eval_criteo()
    print("criteo", ev["criteo"])
    ev["sim"] = eval_sim()
    for k, r in ev["sim"]["policies"].items():
        print(f"{k:32s} profit/1k {r['profit_per_1k']:>8,.0f}  conv {r['conversion']:.3f}  spend {r['incentive_spend_per_1k']:>7,.0f}  leak {r['leakage_per_1k']:>6,.0f}")
    (ARTIFACTS / "eval.json").write_text(json.dumps(ev, indent=1))
    (ROOT / "docs" / "EVAL.md").write_text(_md(ev), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f}s")
    return ev


if __name__ == "__main__":
    import sys

    main(skip_criteo="--skip-criteo" in sys.argv)
