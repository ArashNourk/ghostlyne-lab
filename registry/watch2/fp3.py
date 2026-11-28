"""Three-outcome first passage for driftless Brownian motion in log price.

Barriers sit at log-distances du > 0 above and dd > 0 below the current price.
v is the variance still to come over the remaining window (sigma^2 * time, or an
integrated variance forecast when volatility changes: a time change of Brownian
motion, so the formula is exact for any deterministic variance path).

Returns (p_up_first, p_down_first, p_neither) by the eigenfunction expansion of the
heat equation on the interval with absorbing ends.
"""
import numpy as np


def fp3(du, dd, v, n_max=1500):
    du, dd, v = np.broadcast_arrays(np.asarray(du, float), np.asarray(dd, float), np.asarray(v, float))
    shape = du.shape
    du, dd, v = du.ravel(), dd.ravel(), v.ravel()
    L = du + dd
    y = dd / L                                     # position inside the interval, 0 = lower barrier
    s = np.clip(v, 0, None) / (L * L)              # dimensionless remaining variance
    up = np.zeros_like(y)
    dn = np.zeros_like(y)
    # far from both barriers relative to remaining variance: nothing can be touched
    far = np.minimum(du, dd) > 9 * np.sqrt(np.maximum(v, 1e-300))
    live = ~far & (s > 0)
    if live.any():
        # terms needed so the last term's decay factor is below 1e-12
        need = np.ceil(np.sqrt(2 * 27.7 / (np.pi ** 2 * np.maximum(s[live], 1e-12)))).astype(int)
        need = np.clip(need, 40, n_max)
        idx = np.flatnonzero(live)
        for cap in (40, 120, 400, n_max):
            sel = idx[(need <= cap) & (need > {40: 0, 120: 40, 400: 120, n_max: 400}[cap])]
            if sel.size == 0:
                continue
            n = np.arange(1, cap + 1)[None, :]
            decay = np.exp(-(n ** 2) * np.pi ** 2 * s[sel, None] / 2)
            coef = 2 * (-1.0) ** n / (n * np.pi)
            up[sel] = y[sel] + (coef * np.sin(n * np.pi * y[sel, None]) * decay).sum(1)
            dn[sel] = (1 - y[sel]) + (coef * np.sin(n * np.pi * (1 - y[sel, None])) * decay).sum(1)
    up, dn = np.clip(up, 0, 1), np.clip(dn, 0, 1)
    tot = up + dn
    over = tot > 1
    up[over], dn[over] = up[over] / tot[over], dn[over] / tot[over]
    return up.reshape(shape), dn.reshape(shape), (1 - up - dn).reshape(shape)


def monte_carlo(du, dd, v, paths=200_000, steps=2000, seed=1):
    rng = np.random.default_rng(seed)
    x = np.zeros(paths)
    hit = np.zeros(paths, int)                      # 1 up, -1 down, 0 none
    sd = np.sqrt(v / steps)
    # Broadie-Glasserman continuity correction: discrete monitoring misses touches between steps,
    # which is equivalent to barriers 0.5826 * sd further away; move them in to emulate continuous paths
    bu, bd = du - 0.5826 * sd, dd - 0.5826 * sd
    for _ in range(steps):
        alive = hit == 0
        x[alive] += rng.standard_normal(alive.sum()) * sd
        hit[alive & (x >= bu)] = 1
        hit[alive & (x <= -bd)] = -1
    return (hit == 1).mean(), (hit == -1).mean(), (hit == 0).mean()


if __name__ == "__main__":
    # discrete-step Monte Carlo slightly under-counts touches (crossings between steps), so use fine steps
    cases = [(0.02, 0.01, 0.0158 ** 2), (0.03, 0.02, (0.02 ** 2) * 0.5), (0.01, 0.01, 0.0005), (0.04, 0.01, 0.03 ** 2), (0.02, 0.03, 1e-5)]
    worst = 0
    for du, dd, v in cases:
        a = fp3(du, dd, v)
        b = monte_carlo(du, dd, v)
        err = max(abs(float(a[i]) - b[i]) for i in range(3))
        worst = max(worst, err)
        print(f"du={du:.3f} dd={dd:.3f} v={v:.2e}  formula up/down/none = {float(a[0]):.4f} {float(a[1]):.4f} {float(a[2]):.4f}   MC = {b[0]:.4f} {b[1]:.4f} {b[2]:.4f}   max diff {err*100:.2f} pp")
    print("worst difference:", round(worst * 100, 2), "pp")
