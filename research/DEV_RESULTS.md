# Development-period research output (2024-01-01 to 2026-11-23)

Raw output of the diagnostics and candidate tests that informed PREREGISTRATION.md.

## Diagnostics
```

===== long: 28832 market-days
A. rule by threshold (cap 20x)
  thr 2% Ghostlyne    realized 1.31% [0.85%,1.84%] fc 1.16% meanlev 7.45 abstain 2.6%
  thr 2% GARCH(1,1)-t realized 1.40% [0.91%,1.95%] fc 1.28% meanlev 7.23 abstain 4.3%
  thr 2% EWMA RiskMet realized 1.38% [0.85%,1.96%] fc 1.14% meanlev 7.07 abstain 5.2%
  thr 5% Ghostlyne    realized 3.08% [2.35%,3.86%] fc 2.74% meanlev 9.73 abstain 1.2%
  thr 5% GARCH(1,1)-t realized 2.96% [2.25%,3.73%] fc 2.83% meanlev 9.50 abstain 0.3%
  thr 5% EWMA RiskMet realized 2.96% [2.23%,3.77%] fc 2.97% meanlev 9.72 abstain 0.2%
  thr 10% Ghostlyne    realized 5.99% [4.99%,7.07%] fc 5.75% meanlev 12.24 abstain 0.2%
  thr 10% GARCH(1,1)-t realized 6.15% [5.04%,7.34%] fc 5.89% meanlev 11.99 abstain 0.1%
  thr 10% EWMA RiskMet realized 5.66% [4.63%,6.76%] fc 5.72% meanlev 11.79 abstain 0.1%
B. Ghostlyne thr5% conditional (forecast vs realized, n)
  vol_pct
    50-80    n=  8290 gl fc 2.80%   real 2.77% [1.95%,3.68%]  | garch real 2.70%
    80-95    n=  3727 gl fc 2.91%   real 4.42% [2.73%,6.50%]  | garch real 5.23%
    <50      n= 15282 gl fc 2.64%   real 2.99% [2.14%,3.91%]  | garch real 2.60%
    >95      n=  1533 gl fc 3.04%   real 2.33% [1.30%,3.48%]  | garch real 2.30%
  breadth_down
    0        n= 17458 gl fc 2.67%   real 2.45% [1.72%,3.26%]  | garch real 2.22%
    0-10%    n=  4990 gl fc 2.76%   real 2.82% [1.39%,4.44%]  | garch real 2.53%
    10-30%   n=  3204 gl fc 2.85%   real 2.82% [1.11%,4.79%]  | garch real 3.42%
    >30%     n=  3180 gl fc 2.97%   real 7.37% [3.80%,11.15%]  | garch real 7.21%
  breadth_up
    0        n= 13846 gl fc 2.74%   real 3.93% [2.69%,5.26%]  | garch real 3.67%
    0-10%    n=  7320 gl fc 2.68%   real 2.80% [1.60%,4.17%]  | garch real 2.85%
    10-30%   n=  4872 gl fc 2.76%   real 1.77% [0.86%,2.93%]  | garch real 1.91%
    >30%     n=  2794 gl fc 2.85%   real 1.83% [0.57%,3.39%]  | garch real 1.52%
  v1_rel
    -.5-0    n=  5700 gl fc 2.78%   real 2.41% [1.64%,3.21%]  | garch real 2.53%
    .5-1     n=  2161 gl fc 3.01%   real 4.91% [3.10%,6.82%]  | garch real 4.78%
    0-.5     n=  4234 gl fc 2.88%   real 3.55% [2.37%,4.77%]  | garch real 4.19%
    <-.5     n= 14935 gl fc 2.59%   real 2.60% [1.85%,3.41%]  | garch real 2.19%
    >1       n=  1802 gl fc 3.21%   real 6.30% [3.19%,10.15%]  | garch real 5.59%
  rec_lev
    0        n=   359 gl fc -       real nan% [nan%,nan%]  | garch real 1.56%
    10       n= 14476 gl fc 2.99%   real 3.21% [2.36%,4.12%]  | garch real 2.76%
    15       n=  2284 gl fc 3.37%   real 3.55% [2.24%,5.00%]  | garch real 2.19%
    20       n=  1546 gl fc 2.41%   real 3.10% [2.15%,4.20%]  | garch real 1.94%
    5        n=   254 gl fc 2.83%   real 9.84% [0.00%,22.45%]  | garch real 11.11%
    7        n=  9913 gl fc 2.27%   real 2.59% [1.73%,3.54%]  | garch real 3.43%
  by market (realized at thr5%, worst 6)
                  fc    real     n
s                                 
OPUSDT        0.0285  0.0423  1016
1000PEPEUSDT  0.0275  0.0414   943
INJUSDT       0.0275  0.0405  1013
FILUSDT       0.0278  0.0373  1019
DOGEUSDT      0.0273  0.0364  1016
UNIUSDT       0.0282  0.0364  1016
D. matched-risk frontier: mean leverage offered (abstain=0) at equal realized rate
  Ghostlyne                    @2%: 8.56x  @3%: 9.65x  @4%: 10.61x  @5%: 11.56x
  Textbook (ATR, normal)       @2%: 8.31x  @3%: 9.51x  @4%: 10.53x  @5%: 11.22x
  EWMA RiskMetrics             @2%: 8.30x  @3%: 9.75x  @4%: 10.50x  @5%: 11.32x
  GARCH(1,1)-t                 @2%: 8.24x  @3%: 9.53x  @4%: 10.35x  @5%: 11.22x
  Filtered historical simulati @2%: 8.26x  @3%: 9.61x  @4%: 10.48x  @5%: 11.30x
  Rolling 1-year frequency     @2%: 7.99x  @3%: 9.06x  @4%: 10.07x  @5%: 10.82x
  Ghostlyne - GARCH-t at 3%: +0.12x  90% [-0.00,+0.43]
  Ghostlyne - GARCH-t at 4%: +0.26x  90% [+0.03,+0.52]

===== short: 29448 market-days
A. rule by threshold (cap 20x)
  thr 2% Ghostlyne    realized 1.42% [1.06%,1.79%] fc 1.18% meanlev 7.29 abstain 5.2%
  thr 2% GARCH(1,1)-t realized 1.32% [1.00%,1.64%] fc 1.11% meanlev 6.86 abstain 4.1%
  thr 2% EWMA RiskMet realized 1.32% [0.97%,1.69%] fc 1.05% meanlev 6.70 abstain 6.2%
  thr 5% Ghostlyne    realized 3.39% [2.77%,3.99%] fc 3.03% meanlev 9.89 abstain 1.2%
  thr 5% GARCH(1,1)-t realized 3.21% [2.64%,3.78%] fc 2.97% meanlev 9.39 abstain 1.4%
  thr 5% EWMA RiskMet realized 3.21% [2.56%,3.85%] fc 3.06% meanlev 9.26 abstain 1.1%
  thr 10% Ghostlyne    realized 6.29% [5.43%,7.17%] fc 5.80% meanlev 12.14 abstain 0.5%
  thr 10% GARCH(1,1)-t realized 6.46% [5.54%,7.37%] fc 6.30% meanlev 12.08 abstain 0.3%
  thr 10% EWMA RiskMet realized 6.22% [5.24%,7.19%] fc 6.22% meanlev 11.74 abstain 0.3%
B. Ghostlyne thr5% conditional (forecast vs realized, n)
  vol_pct
    50-80    n=  8622 gl fc 3.14%   real 3.07% [2.48%,3.73%]  | garch real 3.20%
    80-95    n=  3901 gl fc 3.08%   real 3.86% [2.91%,4.80%]  | garch real 4.35%
    <50      n= 15378 gl fc 2.95%   real 3.45% [2.70%,4.32%]  | garch real 2.82%
    >95      n=  1547 gl fc 3.01%   real 3.34% [1.91%,4.97%]  | garch real 4.68%
  breadth_down
    0        n= 17738 gl fc 2.99%   real 3.27% [2.60%,3.95%]  | garch real 2.80%
    0-10%    n=  5130 gl fc 3.05%   real 4.83% [3.35%,6.44%]  | garch real 4.43%
    10-30%   n=  3316 gl fc 3.12%   real 2.41% [1.53%,3.55%]  | garch real 3.13%
    >30%     n=  3264 gl fc 3.11%   real 2.72% [1.49%,4.25%]  | garch real 3.63%
  breadth_up
    0        n= 14266 gl fc 3.04%   real 2.90% [2.26%,3.67%]  | garch real 2.66%
    0-10%    n=  7432 gl fc 3.02%   real 2.96% [2.27%,3.74%]  | garch real 2.92%
    10-30%   n=  4956 gl fc 2.98%   real 4.03% [2.71%,5.34%]  | garch real 4.22%
    >30%     n=  2794 gl fc 3.05%   real 5.93% [3.21%,8.63%]  | garch real 5.10%
  v1_rel
    -.5-0    n=  5834 gl fc 3.06%   real 3.13% [2.48%,3.82%]  | garch real 3.12%
    .5-1     n=  2231 gl fc 3.20%   real 3.46% [2.42%,4.57%]  | garch real 4.26%
    0-.5     n=  4323 gl fc 3.11%   real 3.50% [2.72%,4.27%]  | garch real 4.06%
    <-.5     n= 15196 gl fc 2.96%   real 3.24% [2.62%,3.89%]  | garch real 2.41%
    >1       n=  1864 gl fc 3.12%   real 5.19% [2.60%,7.96%]  | garch real 7.08%
  rec_lev
    0        n=   364 gl fc -       real nan% [nan%,nan%]  | garch real 8.09%
    10       n= 13370 gl fc 3.14%   real 3.52% [2.80%,4.27%]  | garch real 2.89%
    15       n=  3197 gl fc 3.64%   real 4.50% [3.33%,5.81%]  | garch real 3.07%
    20       n=  1997 gl fc 2.65%   real 3.66% [2.39%,5.19%]  | garch real 2.05%
    5        n=  2037 gl fc 2.40%   real 2.21% [1.46%,3.08%]  | garch real 4.78%
    7        n=  8483 gl fc 2.85%   real 2.97% [2.33%,3.65%]  | garch real 3.60%
  by market (realized at thr5%, worst 6)
                  fc    real     n
s                                 
1000PEPEUSDT  0.0315  0.0614   944
UNIUSDT       0.0316  0.0491  1039
XRPUSDT       0.0304  0.0460  1044
DOGEUSDT      0.0301  0.0425  1035
NEARUSDT      0.0304  0.0414  1038
SUIUSDT       0.0309  0.0408   980
D. matched-risk frontier: mean leverage offered (abstain=0) at equal realized rate
  Ghostlyne                    @2%: 8.30x  @3%: 9.38x  @4%: 10.57x  @5%: 11.33x
  Textbook (ATR, normal)       @2%: 7.74x  @3%: 9.16x  @4%: 10.05x  @5%: 10.93x
  EWMA RiskMetrics             @2%: 7.79x  @3%: 9.00x  @4%: 10.05x  @5%: 10.84x
  GARCH(1,1)-t                 @2%: 7.88x  @3%: 9.21x  @4%: 10.20x  @5%: 10.95x
  Filtered historical simulati @2%: 7.72x  @3%: 9.00x  @4%: 9.98x  @5%: 10.82x
  Rolling 1-year frequency     @2%: 7.48x  @3%: 8.68x  @4%: 9.73x  @5%: 10.45x
  Ghostlyne - GARCH-t at 3%: +0.18x  90% [-0.00,+0.45]
  Ghostlyne - GARCH-t at 4%: +0.37x  90% [+0.18,+0.58]
```
## Candidate improvements
```

===== long n=28832
stress days: 15.0%
Ghostlyne                  Brier skill vs current 40..5x: +0.000 +0.000 +0.000 +0.000 +0.000 +0.000 | thr5% real 3.08% [3.86%] stress 6.14% [3.56%,9.18%] fc 3.02% calm 2.57% | lev@3% 9.65 @4% 10.61 abstain 1.2%
Ghostlyne+regime           Brier skill vs current 40..5x: +0.000 +0.000 +0.001 +0.003 +0.004 -0.002 | thr5% real 3.11% [3.93%] stress 6.45% [3.83%,9.47%] fc 3.07% calm 2.56% | lev@3% 9.73 @4% 10.64 abstain 1.0%
Ghostlyne+regime+jumps     Brier skill vs current 40..5x: +0.000 +0.000 +0.001 -0.004 +0.001 -0.001 | thr5% real 3.10% [3.88%] stress 6.09% [3.67%,8.90%] fc 3.03% calm 2.60% | lev@3% 9.70 @4% 10.63 abstain 1.1%
GARCH(1,1)-t               Brier skill vs current 40..5x: -0.016 -0.014 -0.009 +0.025 +0.016 -0.003 | thr5% real 2.96% [3.73%] stress 5.88% [3.45%,8.71%] fc 2.89% calm 2.44% | lev@3% 9.53 @4% 10.35 abstain 0.3%
GJR-GARCH-t                Brier skill vs current 40..5x: -0.017 -0.017 -0.011 +0.024 +0.016 +0.002 | thr5% real 3.14% [3.96%] stress 6.35% [3.85%,9.32%] fc 2.95% calm 2.58% | lev@3% 9.42 @4% 10.41 abstain 0.1%
EVT-FHS                    Brier skill vs current 40..5x: -0.018 -0.017 -0.012 +0.022 +0.017 -0.002 | thr5% real 3.13% [3.95%] stress 6.93% [4.28%,10.07%] fc 3.00% calm 2.46% | lev@3% 9.63 @4% 10.48 abstain 0.2%
Ensemble (regime+GJR+EVT)  Brier skill vs current 40..5x: -0.003 -0.002 +0.002 +0.030 +0.025 +0.005 | thr5% real 2.92% [3.71%] stress 6.36% [3.77%,9.39%] fc 3.04% calm 2.32% | lev@3% 9.67 @4% 10.57 abstain 0.5%
  Ghostlyne+regime at 3%: vs GARCH-t +0.20x [-0.02,+0.44]  vs current +0.08x [-0.14,+0.14]
  Ghostlyne+regime at 4%: vs GARCH-t +0.29x [+0.03,+0.48]  vs current +0.03x [-0.11,+0.14]
  Ghostlyne+regime+jumps at 3%: vs GARCH-t +0.17x [-0.01,+0.47]  vs current +0.05x [-0.12,+0.16]
  Ghostlyne+regime+jumps at 4%: vs GARCH-t +0.28x [+0.08,+0.46]  vs current +0.02x [-0.14,+0.17]
  Ensemble (regime+GJR+EVT) at 3%: vs GARCH-t +0.14x [+0.02,+0.34]  vs current +0.02x [-0.19,+0.13]
  Ensemble (regime+GJR+EVT) at 4%: vs GARCH-t +0.22x [+0.08,+0.32]  vs current -0.03x [-0.28,+0.14]

===== short n=29448
stress days: 14.1%
Ghostlyne                  Brier skill vs current 40..5x: +0.000 +0.000 +0.000 +0.000 +0.000 +0.000 | thr5% real 3.39% [3.99%] stress 5.44% [3.43%,7.59%] fc 3.08% calm 3.07% | lev@3% 9.38 @4% 10.57 abstain 1.2%
Ghostlyne+regime           Brier skill vs current 40..5x: -0.001 -0.001 -0.001 -0.001 -0.007 -0.014 | thr5% real 3.27% [3.84%] stress 5.11% [3.23%,7.12%] fc 3.02% calm 2.99% | lev@3% 9.47 @4% 10.52 abstain 1.9%
Ghostlyne+regime+jumps     Brier skill vs current 40..5x: -0.001 -0.002 -0.001 -0.002 +0.002 +0.012 | thr5% real 3.32% [3.92%] stress 5.24% [3.28%,7.35%] fc 3.03% calm 3.02% | lev@3% 9.48 @4% 10.48 abstain 1.7%
GARCH(1,1)-t               Brier skill vs current 40..5x: -0.005 -0.011 -0.014 -0.012 -0.001 +0.005 | thr5% real 3.21% [3.78%] stress 5.86% [4.15%,7.70%] fc 3.01% calm 2.80% | lev@3% 9.21 @4% 10.20 abstain 1.4%
GJR-GARCH-t                Brier skill vs current 40..5x: -0.006 -0.013 -0.015 -0.013 +0.004 +0.020 | thr5% real 3.20% [3.77%] stress 5.80% [3.96%,7.73%] fc 3.06% calm 2.79% | lev@3% 9.17 @4% 10.25 abstain 1.1%
EVT-FHS                    Brier skill vs current 40..5x: -0.009 -0.021 -0.024 -0.025 -0.012 +0.006 | thr5% real 3.23% [3.90%] stress 7.26% [4.82%,9.86%] fc 3.01% calm 2.57% | lev@3% 8.99 @4% 9.94 abstain 0.4%
Ensemble (regime+GJR+EVT)  Brier skill vs current 40..5x: +0.003 -0.001 -0.004 -0.003 +0.006 +0.022 | thr5% real 2.99% [3.56%] stress 5.54% [3.63%,7.63%] fc 3.03% calm 2.59% | lev@3% 9.32 @4% 10.35 abstain 1.2%
  Ghostlyne+regime at 3%: vs GARCH-t +0.27x [+0.13,+0.49]  vs current +0.09x [-0.02,+0.18]
  Ghostlyne+regime at 4%: vs GARCH-t +0.32x [+0.14,+0.49]  vs current -0.05x [-0.15,+0.06]
  Ghostlyne+regime+jumps at 3%: vs GARCH-t +0.27x [+0.10,+0.46]  vs current +0.09x [-0.05,+0.19]
  Ghostlyne+regime+jumps at 4%: vs GARCH-t +0.28x [+0.13,+0.48]  vs current -0.09x [-0.15,+0.03]
  Ensemble (regime+GJR+EVT) at 3%: vs GARCH-t +0.12x [+0.02,+0.26]  vs current -0.06x [-0.23,+0.09]
  Ensemble (regime+GJR+EVT) at 4%: vs GARCH-t +0.15x [+0.03,+0.28]  vs current -0.22x [-0.36,-0.04]
```
## Stress calibration and gate
```

== long
Ghostlyne                   plain skill +0.000 +0.000 +0.000 +0.000 +0.000 +0.000 | real 3.08% [2.35%,3.86%] | stress real 6.14% [3.56%,9.18%] fc 3.02% | meanlev 9.73 stress-lev 7.92 abstain-stress 6.6%
Ghostlyne stress-calibrated plain skill -0.002 +0.002 +0.008 +0.030 +0.016 -0.005 | real 3.14% [2.43%,3.90%] | stress real 4.74% [2.60%,7.33%] fc 3.03% | meanlev 9.85 stress-lev 7.02 abstain-stress 7.7%
Ghostlyne                   gate  skill +0.000 +0.000 +0.000 +0.000 +0.000 +0.000 | real 2.64% [2.00%,3.31%] | stress real 3.06% [1.43%,5.00%] fc 1.54% | meanlev 9.47 stress-lev 6.20 abstain-stress 10.0%
Ghostlyne stress-calibrated gate  skill -0.002 +0.002 +0.008 +0.030 +0.016 -0.005 | real 2.84% [2.17%,3.56%] | stress real 2.58% [1.04%,4.42%] fc 1.42% | meanlev 9.62 stress-lev 5.50 abstain-stress 13.9%
GARCH(1,1)-t                plain skill -0.016 -0.014 -0.009 +0.025 +0.016 -0.003 | real 2.96% [2.25%,3.73%] | stress real 5.88% [3.45%,8.71%] fc 2.89% | meanlev 9.50 stress-lev 8.56 abstain-stress 0.9%
GARCH(1,1)-t                gate  skill -0.016 -0.014 -0.009 +0.025 +0.016 -0.003 | real 2.58% [1.93%,3.26%] | stress real 3.44% [1.60%,5.59%] fc 1.57% | meanlev 9.24 stress-lev 6.81 abstain-stress 8.4%
  stress-cal lev@3%: 9.72 @4%: 10.65
  stress-cal vs GARCH-t at 3%: +0.19x [-0.00,+0.53]
  stress-cal vs GARCH-t at 4%: +0.30x [+0.03,+0.46]

== short
Ghostlyne                   plain skill +0.000 +0.000 +0.000 +0.000 +0.000 +0.000 | real 3.39% [2.77%,3.99%] | stress real 5.44% [3.43%,7.59%] fc 3.08% | meanlev 9.89 stress-lev 7.74 abstain-stress 5.3%
Ghostlyne stress-calibrated plain skill -0.001 -0.002 -0.002 -0.003 -0.006 -0.000 | real 3.33% [2.77%,3.91%] | stress real 3.89% [2.30%,5.74%] fc 2.94% | meanlev 9.90 stress-lev 6.59 abstain-stress 10.3%
Ghostlyne                   gate  skill +0.000 +0.000 +0.000 +0.000 +0.000 +0.000 | real 3.05% [2.53%,3.58%] | stress real 2.95% [1.61%,4.42%] fc 1.38% | meanlev 9.62 stress-lev 5.82 abstain-stress 13.5%
Ghostlyne stress-calibrated gate  skill -0.001 -0.002 -0.002 -0.003 -0.006 -0.000 | real 3.20% [2.69%,3.72%] | stress real 2.85% [1.48%,4.55%] fc 1.36% | meanlev 9.68 stress-lev 4.98 abstain-stress 20.5%
GARCH(1,1)-t                plain skill -0.005 -0.011 -0.014 -0.012 -0.001 +0.005 | real 3.21% [2.64%,3.78%] | stress real 5.86% [4.15%,7.70%] fc 3.01% | meanlev 9.39 stress-lev 8.05 abstain-stress 5.4%
GARCH(1,1)-t                gate  skill -0.005 -0.011 -0.014 -0.012 -0.001 +0.005 | real 2.88% [2.38%,3.36%] | stress real 3.42% [2.25%,4.61%] fc 1.41% | meanlev 9.13 stress-lev 6.26 abstain-stress 9.2%
  stress-cal lev@3%: 9.50 @4%: 10.57
  stress-cal vs GARCH-t at 3%: +0.30x [+0.06,+0.58]
  stress-cal vs GARCH-t at 4%: +0.37x [+0.16,+0.61]
```
