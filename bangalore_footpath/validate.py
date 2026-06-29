"""Phase 3 — validation harness for the footpath 0/1 layer.

Two jobs:

  1. SAMPLE: draw a random (optionally stratified) set of road segments and
     write a labelling template a human fills in by walking the street or
     checking Street View. This is the ground-truth collection step.

  2. EVALUATE: join the filled-in ground truth back to the predictions and
     report a confusion matrix plus precision / recall / accuracy / F1 /
     specificity / Cohen's kappa — both by segment count and length-weighted
     (length-weighted is the policy-relevant view: error per kilometre).

The metric functions are pure and offline-tested (see selftest.py).

CLI
---
    # 1. draw 60 segments, ~half predicted-present / half predicted-absent:
    python validate.py sample --geojson out/roads_footpath.geojson \
        --n 60 --stratify --seed 42 --out validation_sample.csv

    # 2. (human fills the 'truth' column with 0/1) then score:
    python validate.py evaluate --predictions out/roads_footpath.csv \
        --truth validation_sample.csv
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Dict, Optional

import pandas as pd

ID_COL = "road_id"
PRED_COL = "footpath_present"
TRUTH_COL = "truth"
WEIGHT_COL = "length_m"


# --------------------------------------------------------------------------- #
# Pure metric logic
# --------------------------------------------------------------------------- #
def confusion(pred: pd.Series, truth: pd.Series, weight: Optional[pd.Series] = None) -> Dict[str, float]:
    """Return weighted TP/FP/FN/TN. Default weight = 1 per segment (counts)."""
    pred = pred.astype(int).to_numpy()
    truth = truth.astype(int).to_numpy()
    w = (weight.to_numpy() if weight is not None else [1] * len(pred))
    tp = fp = fn = tn = 0.0
    for p, t, wi in zip(pred, truth, w):
        if p == 1 and t == 1:
            tp += wi
        elif p == 1 and t == 0:
            fp += wi
        elif p == 0 and t == 1:
            fn += wi
        else:
            tn += wi
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def metrics_from_confusion(c: Dict[str, float]) -> Dict[str, float]:
    """Derive precision/recall/accuracy/F1/specificity/kappa from a matrix."""
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    total = tp + fp + fn + tn
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    accuracy = _safe_div(tp + tn, total)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    # Cohen's kappa: agreement beyond chance.
    po = accuracy
    pe = _safe_div((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp), total * total)
    kappa = _safe_div(po - pe, 1 - pe) if pe < 1 else 0.0
    return {
        "n": total,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "accuracy": round(accuracy, 4),
        "f1": round(f1, 4),
        "kappa": round(kappa, 4),
    }


def evaluate(
    predictions: pd.DataFrame,
    truth: pd.DataFrame,
    id_col: str = ID_COL,
    pred_col: str = PRED_COL,
    truth_col: str = TRUTH_COL,
    weight_col: Optional[str] = WEIGHT_COL,
) -> Dict[str, dict]:
    """Join predictions to ground truth on id and compute count + length metrics.

    Rows with a blank/NaN truth label are dropped (not yet labelled). Returns a
    dict with 'count', 'count_confusion', and (if weights present) 'length',
    'length_confusion', plus 'n_labelled' / 'n_unlabelled'.
    """
    t = truth.copy()
    t[truth_col] = pd.to_numeric(t[truth_col], errors="coerce")
    n_total = len(t)
    t = t.dropna(subset=[truth_col])
    n_labelled = len(t)

    merged = predictions.merge(
        t[[id_col, truth_col]], on=id_col, how="inner", validate="one_to_one"
    )
    if merged.empty:
        sys.exit("No overlapping road_id between predictions and truth.")

    out: Dict[str, dict] = {
        "n_labelled": n_labelled,
        "n_unlabelled": n_total - n_labelled,
        "n_scored": len(merged),
    }
    c_cnt = confusion(merged[pred_col], merged[truth_col])
    out["count_confusion"] = c_cnt
    out["count"] = metrics_from_confusion(c_cnt)

    if weight_col and weight_col in merged.columns:
        c_len = confusion(merged[pred_col], merged[truth_col], merged[weight_col])
        out["length_confusion"] = {k: round(v, 1) for k, v in c_len.items()}
        out["length"] = metrics_from_confusion(c_len)
    return out


# --------------------------------------------------------------------------- #
# Sampling
# --------------------------------------------------------------------------- #
def sample_segments(
    df: pd.DataFrame,
    n: int,
    stratify: bool = False,
    pred_col: str = PRED_COL,
    seed: int = 0,
) -> pd.DataFrame:
    """Pick ``n`` segments to label. If stratify, split evenly across the
    predicted classes so both precision (pred=1) and recall (pred=0) are
    estimable. Deterministic given ``seed``."""
    n = min(n, len(df))
    if stratify and pred_col in df.columns and df[pred_col].nunique() > 1:
        parts = []
        classes = sorted(df[pred_col].unique())
        per = max(1, n // len(classes))
        for cls in classes:
            sub = df[df[pred_col] == cls]
            parts.append(sub.sample(min(per, len(sub)), random_state=seed))
        out = pd.concat(parts)
        if len(out) < n:  # top up to n from the remainder
            rest = df.drop(out.index)
            out = pd.concat([out, rest.sample(min(n - len(out), len(rest)), random_state=seed)])
        return out.reset_index(drop=True)
    return df.sample(n, random_state=seed).reset_index(drop=True)


def build_template(sample: pd.DataFrame) -> pd.DataFrame:
    """Columns the human needs: id, name, length, the prediction, blank truth."""
    cols = [c for c in [ID_COL, "name", WEIGHT_COL, PRED_COL] if c in sample.columns]
    tmpl = sample[cols].copy()
    tmpl[TRUTH_COL] = ""  # to be filled with 0/1 on the ground
    tmpl["notes"] = ""
    return tmpl


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _read_any(path: str) -> pd.DataFrame:
    if path.lower().endswith((".geojson", ".json", ".shp", ".gpkg")):
        import geopandas as gpd

        g = gpd.read_file(path)
        return pd.DataFrame(g.drop(columns="geometry"))
    return pd.read_csv(path)


def _print_report(rep: Dict[str, dict]) -> None:
    print(f"Scored {rep['n_scored']} labelled segments "
          f"({rep['n_unlabelled']} still unlabelled).\n")
    for view in ("count", "length"):
        if view not in rep:
            continue
        m = rep[view]
        c = rep[f"{view}_confusion"]
        unit = "segments" if view == "count" else "metres"
        print(f"== {view.upper()}-weighted ({unit}) ==")
        print(f"  confusion: TP={c['tp']} FP={c['fp']} FN={c['fn']} TN={c['tn']}")
        print(f"  precision={m['precision']}  recall={m['recall']}  "
              f"specificity={m['specificity']}")
        print(f"  accuracy={m['accuracy']}  F1={m['f1']}  kappa={m['kappa']}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample", help="draw segments to label")
    s.add_argument("--geojson", "--predictions", dest="src", required=True,
                   help="pipeline output (GeoJSON or CSV) to sample from")
    s.add_argument("--n", type=int, default=50)
    s.add_argument("--stratify", action="store_true",
                   help="split evenly across predicted present/absent")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", default="validation_sample.csv")

    e = sub.add_parser("evaluate", help="score predictions against ground truth")
    e.add_argument("--predictions", required=True, help="pipeline output (GeoJSON or CSV)")
    e.add_argument("--truth", required=True, help="labelled sample CSV (truth column filled)")

    args = ap.parse_args()

    if args.cmd == "sample":
        df = _read_any(args.src)
        sample = sample_segments(df, args.n, stratify=args.stratify, seed=args.seed)
        build_template(sample).to_csv(args.out, index=False)
        print(f"Wrote {len(sample)} segments to {args.out}. "
              f"Fill the 'truth' column with 0/1, then run 'evaluate'.")
    else:
        preds = _read_any(args.predictions)
        truth = _read_any(args.truth)
        _print_report(evaluate(preds, truth))


if __name__ == "__main__":
    main()
