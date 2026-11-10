"""Models.

IntentModel   P(buy) from browsing behaviour, trained on the public UCI Online Shoppers dataset.
ResponseModel One calibrated classifier per incentive (a T-learner): P(buy | incentive, session).
              Uplift for an incentive = P(buy | incentive) - P(buy | none). Also a small model
              for P(pays with Pay Later | buys, incentive), which drives Pay Later's real cost.

Explanations use LightGBM's built-in TreeSHAP (`pred_contrib=True`), so the service needs no
`shap` dependency at runtime. Pattern adapted from the author's wtp-dynamic-pricing-engine
(model/inference.py): one warm singleton, never raise to the caller.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from .config import INCENTIVES
from .features import FEATURE_ORDER, UCI_FEATURES

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

LGB_PARAMS = dict(n_estimators=300, learning_rate=0.04, num_leaves=15, min_child_samples=40,
                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)


def uci_frame(uci: pd.DataFrame) -> pd.DataFrame:
    X = uci[[c for c in UCI_FEATURES if c in uci.columns]].copy()
    X["is_returning"] = (uci["VisitorType"] == "Returning_Visitor").astype(int)
    X["is_weekend"] = uci["Weekend"].astype(int)
    return X[UCI_FEATURES].astype(float)


@dataclass
class Calibrated:
    model: lgb.LGBMClassifier
    iso: IsotonicRegression

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.iso.predict(self.model.predict_proba(X)[:, 1])

    def contrib(self, X: pd.DataFrame) -> np.ndarray:
        """Log-odds TreeSHAP contributions; last column is the bias."""
        return self.model.booster_.predict(X, pred_contrib=True)


def fit_calibrated(X: pd.DataFrame, y: np.ndarray, seed: int = 0, cal_frac: float = 0.25) -> Calibrated:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(X))
    k = int(len(X) * (1 - cal_frac))
    tr, ca = idx[:k], idx[k:]
    m = lgb.LGBMClassifier(random_state=seed, **LGB_PARAMS).fit(X.iloc[tr], y[tr])
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(m.predict_proba(X.iloc[ca])[:, 1], y[ca])
    return Calibrated(m, iso)


@dataclass
class ResponseModel:
    arms: dict[str, Calibrated]
    paylater_use: lgb.LGBMClassifier
    features: list[str] = field(default_factory=lambda: list(FEATURE_ORDER))

    def p_buy(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X[self.features]
        return pd.DataFrame({a: self.arms[a].predict(X) for a in INCENTIVES}, index=X.index)

    def p_paylater(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X[self.features]
        out = {}
        for a in INCENTIVES:
            Z = X.copy()
            Z["paylater_shown"] = int(a == "paylater")
            out[a] = self.paylater_use.predict_proba(Z)[:, 1]
        return pd.DataFrame(out, index=X.index)

    def uplift_contrib(self, X: pd.DataFrame, arm: str) -> pd.DataFrame:
        """Per-feature contribution to logit P(buy|arm) - logit P(buy|none), for one or more rows."""
        X = X[self.features]
        d = self.arms[arm].contrib(X) - self.arms["none"].contrib(X)
        return pd.DataFrame(d[:, :-1], columns=self.features, index=X.index)

    def base_contrib(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X[self.features]
        return pd.DataFrame(self.arms["none"].contrib(X)[:, :-1], columns=self.features, index=X.index)


def fit_response(log: pd.DataFrame, seed: int = 0) -> ResponseModel:
    arms = {}
    for i, a in enumerate(INCENTIVES):
        sub = log[log["arm"] == a]
        arms[a] = fit_calibrated(sub[FEATURE_ORDER], sub["bought"].to_numpy(), seed=seed + i)
    bought = log[log["bought"] == 1].copy()
    Xp = bought[FEATURE_ORDER].copy()
    Xp["paylater_shown"] = (bought["arm"] == "paylater").astype(int)
    plm = lgb.LGBMClassifier(random_state=seed, **{**LGB_PARAMS, "n_estimators": 150}).fit(Xp, bought["used_paylater"])
    return ResponseModel(arms, plm)


@dataclass
class Bundle:
    intent: Calibrated
    response: ResponseModel
    meta: dict

    def save(self, path: Path = ARTIFACTS / "models.joblib") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)

    @staticmethod
    def load(path: Path = ARTIFACTS / "models.joblib") -> "Bundle":
        return joblib.load(path)


_BUNDLE: Bundle | None = None


def get_bundle() -> Bundle:
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = Bundle.load()
    return _BUNDLE
