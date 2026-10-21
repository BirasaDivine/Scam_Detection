# backend/model

Place the exported files here. They are not written by hand.

| File | Tracked in git | Purpose |
| --- | --- | --- |
| `svm_plain.joblib` | no | TF-IDF + LinearSVC pipeline |
| `cutoffs.json` | no | decision_function cut-offs per rule |
| `masking.py` | yes | masking v2, exported from the notebook |
| `chunking.py` | yes | piece chunking, exported from the notebook |

If any file is missing the backend starts in mock mode and the UI shows a MOCK MODEL banner.

Expected `cutoffs.json` shape:

```text
{
  "model_version": "...",
  "trained_on": "standard split, seed 42",
  "sms":      {"fpr_01": <float>, "fpr_05": <float>, "fpr_10": <float>},
  "dialogue": {"fpr_01": <float>, "fpr_05": <float>, "fpr_10": <float>}
}
```
