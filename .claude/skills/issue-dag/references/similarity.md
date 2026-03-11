# Similarity Analysis Criteria

## Scoring Method

Composite weighted score combining three signals:

| Signal | Weight | Method |
|--------|--------|--------|
| Keywords | 0.5 | Jaccard similarity after UL normalization |
| Touched Paths | 0.3 | Jaccard similarity of glob patterns |
| Title Tokens | 0.2 | Jaccard similarity of word tokens |

## Threshold

Default: **0.15** (configurable via `--threshold`). Low default for broad detection ("block + confirm" UX).

- `>= 0.5`: High confidence duplicate
- `0.3 - 0.5`: Likely related
- `0.15 - 0.3`: Possibly related (presented to user for confirmation)

## UL Normalization

Before comparison, all keywords are mapped through the Ubiquitous Language dictionary:

1. Look up each keyword in alias→canonical map
2. If found, replace with canonical term
3. If not found, use keyword as-is (lowercase)

This enables cross-language matching: "auth" → "인증", "payment" → "결제"

## UL Priority

1. **Project-internal UL**: `.claude/ubiquitous-language.yaml`, `docs/glossary*`, domain model classes
2. **Wiki UL dictionary**: `ubiquitous-language.json` in GitHub Wiki (fallback)

## Jaccard Similarity

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

Returns 0.0 when both sets are empty.
