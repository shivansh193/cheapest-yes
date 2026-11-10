"""Train all models and write artifacts/models.joblib.

    python -m cy.train

1. Intent model on the public UCI dataset (80/20 stratified split; test AUC recorded).
2. A training population of simulated shoppers (seed 101) and a merchant exploration log
   with uniformly random incentives. The response models learn only from that log's
   observed outcomes, never from the hidden truth.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from . import sim
from .data import load_uci
from .models import Bundle, fit_calibrated, fit_response, uci_frame

TRAIN_SEED = 101
N_TRAIN = 90_000


def with_intent(pop: sim.Population, intent) -> pd.DataFrame:
    X = pop.signals.copy()
    X["intent_score"] = np.round(intent.predict(uci_frame(pop.uci)), 4)
    return X


def train_intent(uci: pd.DataFrame, seed: int = 0):
    X, y = uci_frame(uci), uci["Revenue"].astype(int).to_numpy()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=seed)
    m = fit_calibrated(Xtr.reset_index(drop=True), ytr, seed=seed)
    auc = roc_auc_score(yte, m.predict(Xte))
    return m, (Xte, yte), auc


def main() -> Bundle:
    t0 = time.time()
    uci = load_uci()
    intent, _, auc = train_intent(uci)
    print(f"intent model: UCI test AUC {auc:.3f}")

    pop = sim.generate(N_TRAIN, uci, seed=TRAIN_SEED)
    log = sim.randomized_log(pop, seed=TRAIN_SEED + 1)
    log["intent_score"] = with_intent(pop, intent)["intent_score"]
    response = fit_response(log, seed=TRAIN_SEED)
    meta = {"uci_test_auc": round(float(auc), 4), "n_train_log": int(len(log)), "train_seed": TRAIN_SEED,
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    b = Bundle(intent, response, meta)
    b.save()
    print(f"saved artifacts/models.joblib in {time.time() - t0:.1f}s; {meta}")
    return b


if __name__ == "__main__":
    main()
