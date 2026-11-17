"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")
    tp = fp = fn = tn = 0
    for h, j in zip(human, judge):
        h_pos, j_pos = h == POS, j == POS
        if h_pos and j_pos:
            tp += 1        # judge bắt đúng lỗi
        elif j_pos:
            fp += 1        # judge báo lỗi nhưng người nói tốt (báo nhầm)
        elif h_pos:
            fn += 1        # judge bỏ sót lỗi
        else:
            tn += 1        # cả hai đều nói tốt
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0   # trong số judge báo lỗi, bao nhiêu là lỗi thật
    recall = tp / (tp + fn) if tp + fn else 0.0      # trong số lỗi thật, judge bắt được bao nhiêu
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = sum(cm.values())
    if n == 0:
        raise ValueError("kappa undefined for empty input")
    p_o = (cm["tp"] + cm["tn"]) / n                              # tỉ lệ đồng ý thực tế
    h_fail = (cm["tp"] + cm["fn"]) / n
    j_fail = (cm["tp"] + cm["fp"]) / n
    p_e = h_fail * j_fail + (1 - h_fail) * (1 - j_fail)          # tỉ lệ đồng ý do ngẫu nhiên
    if p_e == 1:
        raise ValueError("kappa undefined (p_e == 1): constant labels carry no signal")
    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denom = sensitivity + specificity - 1
    if denom <= 0:
        return float("nan")      # judge không hơn đoán mò: không thể hiệu chỉnh
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / denom))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    if len(a) != len(b):
        raise ValueError("a and b must be paired: same items, same order")
    if len(a) == 0:
        raise ValueError("paired_bootstrap needs at least one item")
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if np.array_equal(x, y):
        return (0.0, 0.0, 0.0)          # không có khác biệt: scipy sẽ lỗi vì mọi mẫu giống hệt nhau

    def diff_of_means(u, v, axis=-1):
        return np.mean(u, axis=axis) - np.mean(v, axis=axis)

    res = bootstrap((x, y), diff_of_means, paired=True, vectorized=True, n_resamples=n_resamples,
                    confidence_level=confidence, method="percentile", rng=np.random.default_rng(rng))
    ci = res.confidence_interval
    return (float(np.mean(x) - np.mean(y)), float(ci.low), float(ci.high))


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    # TODO M6
    raise NotImplementedError


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    # TODO M6
    raise NotImplementedError
