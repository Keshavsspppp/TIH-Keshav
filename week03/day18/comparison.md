| Method | Msg correct | BER (real) | BER synth @true / @phase 0 | Phase tol. (bits) | Period tol. (%) | Safe bits (real) | Phase stab. (real) | Thr. tol. (real) | Agree w/ M0 | ms / 1000 fr |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 fixed threshold | n/a | n/a | 0.058 % / 9.5 % | 0.10 | 0 | 43.6 % | 90.5 % | 76.0 % | 100.0 % | 0.1 |
| M1 adaptive threshold | n/a | n/a | 0.050 % / 9.5 % | 0.10 | 0 | 44.0 % | 90.3 % | 76.0 % | 98.7 % | 0.3 |
| M0 + end margin 0.3 | n/a | n/a | 0.000 % / 8.6 % | 0.20 | 0 | 39.7 % | 88.6 % | 80.0 % | 95.9 % | 0.1 |
| M2 ML classifier (synth-trained) | n/a | n/a | 0.000 % / 7.4 % | 0.37 | 0 | 49.7 % | 91.5 % | 87.2 % | 80.7 % | 0.1 |

Hard synthetic case (noise 80, exposure 0.3): M0 fixed threshold: BER 2.03 % @true, 11.1 % @phase 0; M1 adaptive threshold: BER 2.09 % @true, 11.3 % @phase 0; M0 + end margin 0.3: BER 0.94 % @true, 10.9 % @phase 0; M2 ML classifier (synth-trained): BER 1.18 % @true, 11.4 % @phase 0
