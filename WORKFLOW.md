# ML Training Workflow - RAW Data Approach

This document explains the complete workflow for training the ML model with raw, real-world data variations.

## 🎯 Philosophy

**Keep variations in training data, normalize only for database.**

The ML model should learn to recognize real-world text as it appears:
- ✅ "benzínový" → FUEL
- ✅ "dieselový" → FUEL
- ✅ "145 KW" → POWER
- ✅ "187.000 km" → MILEAGE

**NOT** the normalized versions:
- ❌ "benzín" (doesn't appear in text!)
- ❌ "diesel" (doesn't appear in text!)
- ❌ "145" (missing unit context!)

## 📊 Complete Workflow

### STEP 1: Data Scraping

```bash
# Run scraper (includes heading + description)
python3 -m scraper.data_scrap --skip-db
```

**What happens:**
- Scrapes car listings from Bazos.cz
- Combines heading + description for each car
  ```
  Heading: "Hyundai Santa Fe 2.2D 145KW 4x4"
  Description: "Motor dieselový 3.6 litru, najeto 187.000 km..."
  Combined: "Hyundai Santa Fe 2.2D 145KW 4x4\nMotor dieselový..."
  ```

### STEP 2: RAW Extraction (ML + Regex)

**What happens:**
- ML extracts RAW: `"dieselový"`, `"145 KW"`, `"187.000 km"`
- Regex extracts RAW: `"diesel"`, `"145"`, `"187000"`

**Important:** NO normalization at this stage!

### STEP 3: RAW Comparison

**What happens:**
- Compares RAW values with exact match:
  ```
  "dieselový" != "diesel" → DISAGREEMENT ✓
  "145 KW" != "145" → DISAGREEMENT ✓
  "187.000 km" != "187000" → DISAGREEMENT ✓
  ```

**Why this matters:**
- You see EXACTLY what ML is catching vs what Regex is catching
- ML might miss "diesel" but catch "dieselový" → you want to see this!
- ML might include units "145 KW" → you want to see this!

### STEP 4: Save to Review Queue (RAW!)

**Generated files:**
- `review_queue.json` - Disagreements (RAW values)
- `auto_training_data.json` - Agreements (RAW values)
- `extraction_stats.json` - Statistics

**review_queue.json format:**
```json
{
  "car_id": "https://auto.bazos.cz/...",
  "text": "Hyundai Santa Fe 2.2D 145KW...\nMotor dieselový...",
  "ml_result": {
    "fuel": "dieselový",
    "power": "145 KW",
    "mileage": "187.000 km"
  },
  "regex_result": {
    "fuel": "diesel",
    "power": "145",
    "mileage": "187000"
  }
}
```

### STEP 5: Manual Review (RAW Data)

```bash
# Review disagreements
python3 -m ml.review_disagreements
```

**What you see:**
```
⚠️  FUEL - DISAGREEMENT:
  1. ML found:    dieselový
  2. Regex found: diesel
  Which is correct? (1/2/3=Neither/custom value/skip): 1

✓ Using ML: dieselový
```

**Why ML is correct:**
- Text has "dieselový", not "diesel"
- You're labeling what actually appears in the text!

### STEP 6: Create Training Data (RAW with units!)

**What happens:**
- Finds "dieselový" in text → position (50, 59)
- Finds "145 KW" in text → position (40, 46)
- Finds "187.000 km" in text → position (70, 81)

**Saves to `manual_review_data.json`:**
```python
("Hyundai... Motor dieselový... 145 KW... 187.000 km", {
  'entities': [
    (50, 59, 'FUEL'),      # "dieselový"
    (40, 46, 'POWER'),     # "145 KW"
    (70, 81, 'MILEAGE')    # "187.000 km"
  ]
})
```

### STEP 7: Retrain Model

```bash
python3 -m ml.retrain_model
```

**What happens:**
- Combines 3 data sources:
  1. Original 201 labeled examples
  2. Auto-collected data (ML+Regex agreements)
  3. Manual review data (your corrections)
- Retrains spaCy NER model
- Model learns patterns from RAW variations:
  - "dieselový" → FUEL
  - "benzínový" → FUEL
  - "TDI" → FUEL
  - "145 KW" → POWER
  - "187.000 km" → MILEAGE

### STEP 8: Normalization (Database Only!)

**Option A: Automatic (during scraping)**
- Already happens in `production_extractor.py`
- Normalized data goes to database
- RAW data saved for training

**Option B: Manual (standalone script)**
```bash
# Normalize a JSON file
python3 -m ml.normalize_for_db --file extraction_results.json

# Preview normalization on review queue
python3 -m ml.normalize_for_db --review-queue
```

**What normalization does:**
```python
RAW → NORMALIZED (for database):
"dieselový" → "diesel"
"benzínový" → "benzín"
"145 KW" → 145
"187.000 km" → 187000
```

## 🔄 Continuous Improvement Loop

```
1. Scrape new data
   ↓
2. Extract with current model (RAW)
   ↓
3. Compare ML vs Regex (RAW)
   ↓
4. Review disagreements (RAW)
   ↓
5. Label corrections (RAW)
   ↓
6. Retrain model
   ↓
7. Model improves
   ↓
8. Go to step 1
```

## 📁 Key Files

### Input Files:
- `training_data_labeled.json` - Original 201 examples
- `review_queue.json` - Disagreements to review (RAW)
- `auto_training_data.json` - Auto-collected agreements (RAW)

### Output Files:
- `manual_review_data.json` - Your manual corrections (RAW labels)
- `extraction_stats.json` - Extraction accuracy metrics
- `ml_models/car_ner/` - Trained model

### Scripts:
- `scraper/data_scrap.py` - Main scraper
- `ml/production_extractor.py` - ML + Regex extraction
- `ml/review_disagreements.py` - Manual review interface
- `ml/retrain_model.py` - Model retraining
- `ml/normalize_for_db.py` - Data normalization (DB only)

## 🎓 Training Data Format (spaCy NER)

```python
training_data = [
    ("Motor dieselový 3.6 litru, najeto 187.000 km, rok 2015, výkon 145 KW", {
        'entities': [
            (6, 15, 'FUEL'),        # "dieselový" (as written!)
            (35, 46, 'MILEAGE'),    # "187.000 km" (with dots!)
            (53, 57, 'YEAR'),       # "2015"
            (65, 71, 'POWER')       # "145 KW" (with unit!)
        ]
    }),
    # ... more examples
]
```

**Key points:**
- Positions are character offsets in the text
- Labels are the RAW text as it appears
- Units are included: "145 KW", not "145"
- Variations are kept: "dieselový", not "diesel"

## ⚠️ Common Mistakes to Avoid

### ❌ WRONG: Normalizing before labeling
```python
Text: "Motor benzínový"
Label: "benzín" → FUEL  # ❌ "benzín" not in text!
```

### ✅ CORRECT: Labeling RAW text
```python
Text: "Motor benzínový"
Label: "benzínový" → FUEL  # ✓ Exact text!
```

### ❌ WRONG: Removing units
```python
Text: "výkon 145 KW"
Label: "145" → POWER  # ❌ Lost context!
```

### ✅ CORRECT: Keeping units
```python
Text: "výkon 145 KW"
Label: "145 KW" → POWER  # ✓ Full context!
```

## 🚀 Quick Start

```bash
# 1. Clean old data
rm review_queue.json manual_review_data.json

# 2. Fresh scrape with RAW extraction
python3 -m scraper.data_scrap --skip-db

# 3. Check stats
cat extraction_stats.json

# 4. Review disagreements (RAW data!)
python3 -m ml.review_disagreements

# 5. Retrain with accumulated data
python3 -m ml.retrain_model

# 6. Test new model
# Run scraper again, check improved accuracy!
```

## 📈 Expected Results

**Before fixes:**
- Many false disagreements: "benzín" vs "benzin"
- Lost context: "145" vs "145 KW"
- Fuel accuracy: ~22%

**After fixes (RAW workflow):**
- Only real disagreements: "dieselový" vs "diesel"
- Full context: "145 KW" vs "145"
- Clear view of what ML catches/misses
- Better training data → better model
- Expected fuel accuracy: 60-70%+

## 💡 Philosophy Summary

> "In labeled JSON I want differences because in real life people write data in so many ways. My goal is to teach the model what and where data could be - not to memorize normalized forms."

This workflow ensures:
1. ✅ Model learns real-world variations
2. ✅ You see exactly what ML extracts
3. ✅ Training data matches actual text
4. ✅ Normalization happens separately (DB only)
5. ✅ Continuous improvement through disagreement review
