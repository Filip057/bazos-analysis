---
name: bazos-ml-pipeline
description: >
  Skill for working with the ML extraction pipeline — spaCy NER model training,
  regex-based attribute extraction, production extractor that combines both methods,
  resolver logic for cross-validation between ML and regex, and model evaluation.
  Use this skill whenever the user mentions NER, spaCy, extraction accuracy, mileage/fuel/power/year
  extraction, labeling data, training or retraining the model, resolvers, ProductionExtractor,
  error analysis, F1 score, training reports, or anything in the ml/ directory.
  Also trigger for labeling/ directory work (label_data_assisted.py, training data preparation).
---

# ML Pipeline Skill

## Purpose

Extract structured vehicle attributes (mileage, year of manufacture, fuel type, power)
from free-text Czech car listing descriptions on bazos.cz. The pipeline uses a dual
extraction approach — spaCy NER model + regex patterns — with cross-validation resolvers
that compare both outputs and pick the best result with confidence scoring.

## Architecture

```
ml/
├── production_extractor.py    # ProductionExtractor — main entry point, combines NER + regex
├── extractor.py               # Core extraction logic
├── resolvers/                 # Per-attribute resolution (mileage, fuel, power, year)
├── context_aware_patterns.py  # Advanced regex patterns with contextual awareness
├── training/                  # Model training scripts
├── error_analysis/            # Extraction quality analysis tools
└── clean_all_duplicates.py    # Deduplication utility

labeling/
├── label_data_assisted.py     # Semi-automated labeling (manual + auto-assisted)
├── export, filter, validate   # Supporting labeling scripts
└── scrape scripts             # Scraping raw data for labeling

ml_models/                     # Saved model artifacts (DO NOT modify without approval)
car_ner_model/                 # Active production NER model (DO NOT modify without approval)
training_reports/              # Post-training evaluation reports (F1 scores, metrics)
```

## How Extraction Works

### Dual Extraction Strategy

`ProductionExtractor` runs both methods on every listing description:

1. **spaCy NER model** — trained custom model that recognizes entities like MILEAGE, YEAR, FUEL, POWER in Czech text
2. **Regex patterns** — rule-based extraction using `context_aware_patterns.py` and per-attribute patterns

### Resolver Cross-Validation

For each attribute (mileage, year, fuel, power), a dedicated resolver:
- Preserves raw extraction values from both methods
- Normalizes values for comparison (e.g. "nafta" → "diesel", "150 koní" → 150)
- Detects disagreements between NER and regex results
- Classifies disagreement type
- Resolves to final value with confidence scoring

The resolvers are the critical quality layer — they catch cases where one method
extracts correctly and the other fails.

### Fuel Type Normalization

Extracted fuel values are normalized to one of 6 types:
`diesel`, `benzín`, `lpg`, `elektro`, `cng`, `hybrid`

## Model Training Workflow

### Preparing Training Data

1. Collect raw listing descriptions (from DB or via `labeling/` scrape scripts)
2. Use `label_data_assisted.py` for semi-automated labeling — combines manual review
   with auto-suggestions to speed up the process
3. Export/filter/validate labeled data using other `labeling/` scripts
4. Training data stored as JSON files in project root

### Training & Evaluation

1. Run training scripts from `ml/training/`
2. After training, evaluation report is saved to `training_reports/`
3. Reports contain metrics: F1 score, precision, recall per entity type
4. Compare new model against previous version before promoting to production

### Promoting a New Model

1. Training produces a new model in `ml_models/`
2. Review training report — check F1 scores, look for regressions
3. Only after explicit user approval: copy to `car_ner_model/` (production)
4. Never overwrite production model without approval

## Critical Rules

1. **Never modify `car_ner_model/` or `ml_models/` without explicit user approval.**
   This includes retraining, overwriting, or deleting model files.
2. **Never modify existing training data** without approval — these are manually curated.
3. **Resolver logic changes require careful testing** — a change in one resolver can
   affect extraction accuracy across thousands of listings.
4. **Always preserve raw extraction values** — resolvers should store both NER and regex
   raw outputs alongside the resolved value for debugging.

## Patterns to Follow

### Improving Extraction Accuracy

1. Identify problematic listings (error analysis tools in `ml/error_analysis/`)
2. Add them to labeling queue
3. Label with `label_data_assisted.py`
4. Retrain model
5. Review training report (F1, precision, recall)
6. If metrics improve, propose promotion to user

### Adding a New Regex Pattern

1. Add pattern to `context_aware_patterns.py`
2. Write tests with real Czech listing examples that the pattern should match
3. Also test that the pattern does NOT false-positive on similar but different text
4. Verify resolver still works correctly with the new pattern outputs

### Debugging an Extraction Error

1. Get the raw listing description text
2. Run `ProductionExtractor` on it in isolation
3. Check what NER extracted vs what regex extracted
4. Check resolver logs — which method "won" and why
5. Fix is usually one of: add training data (NER), add/fix regex pattern, or adjust resolver logic

## Common Pitfalls

- **Czech language quirks**: Abbreviations like "tis. km", "kW", "r.v." are common.
  Regex patterns must handle these. NER learns them from training data.
- **Ambiguous numbers**: "150" could be power (kW/HP) or mileage (150 000 km without units).
  Context-aware patterns and resolvers exist specifically for this.
- **Units**: Mileage can be in km or tis. km (thousands). Power in kW or HP. Always normalize.
- **Model overfitting**: Small training set risk. Always check validation metrics, not just training metrics.
