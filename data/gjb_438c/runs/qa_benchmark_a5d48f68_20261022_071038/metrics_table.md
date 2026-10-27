# QA benchmark 结果 (label=silver, 非gold, 仅作参考)

- frozen: `C:\Users\12488\Desktop\data_clean\data\gjb_438c\qa_frozen\scene1_qa_frozen_v1.jsonl` (91行)
- labels: `C:\Users\12488\Desktop\data_clean\data\gjb_438c\runs\review_qa_with_glm53_582b51e5_20261021_145212\final_labels.jsonl`
- split: mode=section seed=38 sizes={'train': 60, 'dev': 14, 'test': 17}

## B0_majority

- n=17 accuracy=0.823529 macro_f1=0.301075 invalid=0 abstain=0
- citation: {'n_rows_with_citations': 0, 'n_citations': 0, 'n_valid': 0, 'precision': None}

| class | precision | recall | f1 | predicted | support |
|---|---|---|---|---|---|
| support | 0.0 | 0.0 | 0.0 | 0 | 1 |
| refute | 0.0 | 0.0 | 0.0 | 0 | 2 |
| not_in_evidence | 0.823529 | 1.0 | 0.903226 | 17 | 14 |

混淆矩阵 (行=gold, 列=pred):
```json
{
 "classes": [
  "support",
  "refute",
  "not_in_evidence"
 ],
 "matrix": [
  [
   0,
   0,
   1
  ],
  [
   0,
   0,
   2
  ],
  [
   0,
   0,
   14
  ]
 ],
 "invalid_by_gold": {
  "support": 0,
  "refute": 0,
  "not_in_evidence": 0
 }
}
```

## B2_lexical

- n=17 accuracy=0.823529 macro_f1=0.301075 invalid=0 abstain=0
- citation: {'n_rows_with_citations': 0, 'n_citations': 0, 'n_valid': 0, 'precision': None}

| class | precision | recall | f1 | predicted | support |
|---|---|---|---|---|---|
| support | 0.0 | 0.0 | 0.0 | 0 | 1 |
| refute | 0.0 | 0.0 | 0.0 | 0 | 2 |
| not_in_evidence | 0.823529 | 1.0 | 0.903226 | 17 | 14 |

混淆矩阵 (行=gold, 列=pred):
```json
{
 "classes": [
  "support",
  "refute",
  "not_in_evidence"
 ],
 "matrix": [
  [
   0,
   0,
   1
  ],
  [
   0,
   0,
   2
  ],
  [
   0,
   0,
   14
  ]
 ],
 "invalid_by_gold": {
  "support": 0,
  "refute": 0,
  "not_in_evidence": 0
 }
}
```

## B3_rule_numeric

- n=17 accuracy=0.823529 macro_f1=0.301075 invalid=0 abstain=0
- citation: {'n_rows_with_citations': 0, 'n_citations': 0, 'n_valid': 0, 'precision': None}

| class | precision | recall | f1 | predicted | support |
|---|---|---|---|---|---|
| support | 0.0 | 0.0 | 0.0 | 0 | 1 |
| refute | 0.0 | 0.0 | 0.0 | 0 | 2 |
| not_in_evidence | 0.823529 | 1.0 | 0.903226 | 17 | 14 |

混淆矩阵 (行=gold, 列=pred):
```json
{
 "classes": [
  "support",
  "refute",
  "not_in_evidence"
 ],
 "matrix": [
  [
   0,
   0,
   1
  ],
  [
   0,
   0,
   2
  ],
  [
   0,
   0,
   14
  ]
 ],
 "invalid_by_gold": {
  "support": 0,
  "refute": 0,
  "not_in_evidence": 0
 }
}
```
