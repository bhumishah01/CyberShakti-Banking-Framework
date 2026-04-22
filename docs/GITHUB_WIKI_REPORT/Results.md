# Results & Output

## Output Screens and System Views
The project now has the following output surfaces that can be demonstrated directly from the live deployment:
- landing page
- customer dashboard
- send money result and transaction detail
- transaction history page
- bank dashboard
- analytics page
- sync queue page
- report/export page

## Measured Evaluation Results
The repository includes a deterministic fraud simulation and scoring performance benchmark in `src/evaluation/simulation.py`.

### Fraud Simulation Metrics
| Metric | Result |
|---|---:|
| Total simulated cases | 200 |
| Fraud cases | 72 |
| Baseline successful fraud cases | 72 |
| Successful fraud after framework protection | 19 |
| Fraud reduction | **73.61%** |
| True positive rate | **73.61%** |
| False positive rate | **17.19%** |

### Local Scoring Runtime Metrics
| Metric | Result |
|---|---:|
| Average scoring runtime | **0.0034 ms** |
| P95 scoring runtime | **0.0036 ms** |

## Observations
- The simulation shows a strong reduction in successful fraudulent cases relative to the no-protection baseline.
- The local fraud engine is extremely lightweight, which supports the project goal of working on low-resource devices.
- Explainable fraud reasons improve trust and presentation quality because decisions are not hidden behind a black-box score only.
- The visible sync queue and admin analytics make the architecture operationally demonstrable, not just conceptually described.

## Sample Output Types
- allowed transaction
- held transaction
- blocked transaction
- pending sync record
- suspicious alert record
- high-risk user record
- exportable change-log/report output

## Navigation
- Previous: [[Implementation]]
- Next: [[Challenges]]
