# Production Continuous Learning Guide

## 🎯 Overview

This system enables your ML model to **learn and improve continuously** from production data, without manual labeling!

**Current Status:**
- ML Model: F1 = 70% (trained on 201 examples)
- Target: F1 = 85%+ through continuous learning

**How it works:**
1. **Dual Extraction**: Run both ML and context-aware regex on each car listing
2. **Agreement Detection**: When both agree → High confidence → Auto-save as training data
3. **Disagreement Review**: When they disagree → Flag for manual review
4. **Periodic Retraining**: Combine all data sources and retrain model monthly

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Extraction                     │
│                  (production_extractor.py)                   │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
      ✅ Full Agreement              ❌ Disagreement
   (ML = Regex on all fields)    (ML ≠ Regex on ≥1 field)
              │                               │
              ▼                               ▼
   ┌──────────────────────┐      ┌──────────────────────┐
   │ auto_training_data   │      │   review_queue.json  │
   │      .json           │      │                      │
   │  (Auto-collected)    │      │  (Needs human review)│
   └──────────────────────┘      └──────────┬───────────┘
              │                              │
              │                    ┌─────────▼──────────┐
              │                    │  Human Review      │
              │                    │ (review_disagree-  │
              │                    │  ments.py)         │
              │                    └─────────┬──────────┘
              │                              │
              │                              ▼
              │                  ┌──────────────────────┐
              │                  │ manual_review_data   │
              │                  │      .json           │
              │                  │ (Human-corrected)    │
              │                  └──────────┬───────────┘
              │                             │
              └─────────────┬───────────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │   Retrain Model        │
                │ (retrain_model.py)     │
                │                        │
                │ Sources:               │
                │ 1. Original (201)      │
                │ 2. Auto-collected      │
                │ 3. Manual review       │
                └───────────┬────────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │   New Model Version    │
                │   (Higher F1 score)    │
                └────────────────────────┘
```

---

## 🚀 Quick Start

### Step 1: Run Production Extraction

Test on a few examples first:

```bash
python3 production_extractor.py
```

This will:
- Load your trained ML model from `ml_models/car_ner`
- Test with 3 example car descriptions
- Show extraction results with confidence levels
- Save agreements and disagreements

**Example Output:**
```
Testing production extractor:

Example 1:
Text: Škoda Octavia 2015, STK do 2027, najeto 150000 km, výkon 110 kW, diesel

Result:
  Mileage: 150000
  Year: 2015
  Power: 110
  Fuel: diesel
  Confidence: high
  Agreement: full
  Flagged for review: False

Production Extraction Statistics
==================================
Total extractions:     3
Full agreements:       2 (66.7%)
Partial agreements:    1 (33.3%)
Disagreements:         0 (0.0%)
```

### Step 2: Integrate with Your Scraper

Add to your `data_scrap.py`:

```python
from production_extractor import ProductionExtractor

# Initialize once
extractor = ProductionExtractor()

# In your scraping loop
async def scrape_car(car_id, description):
    # Your existing scraping code...

    # Extract car data
    result = extractor.extract(description, car_id=car_id)

    # Use the extracted data
    mileage = result['mileage']
    year = result['year']
    power = result['power']
    fuel = result['fuel']
    confidence = result['confidence']  # 'high', 'medium', 'low'

    # Save to database with confidence score
    # ...

# After scraping session (e.g., daily at midnight)
extractor.save_queues()  # Saves auto_training_data.json and review_queue.json
extractor.print_stats()
```

### Step 3: Review Disagreements (Weekly)

When you have 50+ disagreements in `review_queue.json`:

```bash
python3 review_disagreements.py
```

**Interactive Review Session:**
```
📋 Disagreement Review Tool
============================
Found 127 cases to review

[1/127]
Car ID: 123456789
Text: Škoda Octavia rok výroby 2015, STK do 2027, servis 2023...

🚗 MILEAGE:
   1. ML found:    150000
   2. Regex found: 150000
   ✅ Both agree: 150000

📅 YEAR:
   1. ML found:    2027        ❌
   2. Regex found: 2015        ✅

Which is correct? (1/2/3=Neither/custom value): 2

✅ Saved correction: year = 2015

⚡ POWER:
   1. ML found:    110
   2. Regex found: None

Which is correct? (1/2/3=Neither/custom value): 1

✅ Saved correction: power = 110

Progress: 1/127 reviewed
Continue? (y/n): y
```

This creates `manual_review_data.json` with corrected training examples.

### Step 4: Retrain Model (Monthly)

When you have accumulated enough new data:

```bash
python3 retrain_model.py --iterations 150
```

**Example Output:**
```
📊 Training Data Growth
========================
Original labeled:       201 examples
Auto-collected:         856 examples
Manual review:          127 examples
────────────────────────────────────
Total:                 1184 examples
========================

✨ You've added 983 new examples from production!
   Expected F1 improvement: +30%

Proceed with retraining? (y/n): y

============================================================
Starting Model Retraining
============================================================
Total training examples: 1184
Training iterations:     150
Output path:             ./ml_models/car_ner
============================================================

Training model...
Losses: {'ner': 12.45} (iteration 1/150)
Losses: {'ner': 8.32} (iteration 50/150)
Losses: {'ner': 3.21} (iteration 100/150)
Losses: {'ner': 1.45} (iteration 150/150)

Saving model to ./ml_models/car_ner...

✅ Retraining complete!
New model saved to: ./ml_models/car_ner

🎉 Success!
============================================================
Your model has been retrained with 1184 examples

💡 Next steps:
1. Test the new model: python3 test_ml_model.py
2. Update production to use new model
3. Continue collecting data for next retraining
```

---

## 📁 File Reference

### `production_extractor.py`
**Purpose:** Main production extraction engine

**Key Features:**
- Dual extraction (ML + context-aware regex)
- Confidence scoring (high/medium/low)
- Agreement tracking
- Auto-saves training data
- Statistical monitoring

**Usage in Code:**
```python
from production_extractor import ProductionExtractor

extractor = ProductionExtractor(
    ml_model_path='./ml_models/car_ner',
    auto_training_file='auto_training_data.json',
    review_queue_file='review_queue.json',
    stats_file='extraction_stats.json'
)

result = extractor.extract(text, car_id='12345')

# After batch processing
extractor.save_queues()
extractor.print_stats()
```

### `review_disagreements.py`
**Purpose:** Interactive tool for reviewing ML-Regex disagreements

**When to Use:**
- Run weekly or when review_queue.json has 50+ items
- Creates high-quality training data from corrections
- Helps identify patterns where ML fails

**Output Files:**
- `manual_review_data.json` - Corrected training examples
- Updated `review_queue.json` - Removes reviewed items

### `retrain_model.py`
**Purpose:** Retrain ML model with accumulated data

**Data Sources:**
1. **Original labeled data** (`training_data_labeled.json`) - Your 201 manually labeled examples
2. **Auto-collected data** (`auto_training_data.json`) - High-confidence agreements from production
3. **Manual review data** (`manual_review_data.json`) - Corrected disagreements

**When to Retrain:**
- Monthly, or when you have 500+ new examples
- After fixing regex patterns (to teach ML the corrections)
- When F1 score plateaus

**Arguments:**
```bash
python3 retrain_model.py \
  --original training_data_labeled.json \
  --auto auto_training_data.json \
  --manual manual_review_data.json \
  --iterations 150 \
  --output ./ml_models/car_ner_v2
```

---

## 🎯 Expected Results

### Week 1: Initial Production Run
- Process: 1000 car listings
- Full agreements: ~700 (70%)
- Partial agreements: ~200 (20%)
- Disagreements: ~100 (10%)
- **Auto-collected training data: 700 examples**

### Week 2: First Review Session
- Review: 100 disagreements (30 min @ 20 cases/hour)
- **Manual training data: 100 examples**
- Regex improvements: Fix 2-3 patterns based on common errors

### Week 3: First Retraining
- Original: 201 examples
- Auto: 700 examples
- Manual: 100 examples
- **Total: 1001 examples**
- **Expected F1: 80-85%** (up from 70%)

### Month 2: Improved System
- Process: 1000 car listings
- Full agreements: ~850 (85%) ← Model improved!
- Disagreements: ~50 (5%) ← Fewer errors!
- **New training data: 850 examples**

### Month 3: Second Retraining
- Total: 2001 examples
- **Expected F1: 85-90%**

---

## 💡 Best Practices

### 1. Monitor Agreement Rates
```python
extractor.print_stats()
```

**Healthy System:**
- Full agreements: 70-85%
- Partial agreements: 10-20%
- Disagreements: 5-15%

**Warning Signs:**
- Full agreements < 50% → Check if model/regex broke
- Disagreements > 30% → Retrain needed urgently

### 2. Review Regularly
- Don't let review_queue.json grow too large (> 500 items)
- Review in batches of 50-100
- Track common error patterns

### 3. Improve Regex Based on Reviews
If you see ML consistently wrong on specific patterns:
1. Fix the regex pattern in `context_aware_patterns.py`
2. Review past cases with that pattern
3. Retrain model to learn the correction

### 4. Version Your Models
```bash
# Before retraining
cp -r ml_models/car_ner ml_models/car_ner_v1_backup

# Retrain with version number
python3 retrain_model.py --output ./ml_models/car_ner_v2

# Test new version before replacing
python3 test_ml_model.py --model ./ml_models/car_ner_v2

# If good, replace production model
mv ml_models/car_ner ml_models/car_ner_v1_old
mv ml_models/car_ner_v2 ml_models/car_ner
```

### 5. Clean Up Old Data
After retraining, archive the data:

```bash
# Create archive directory
mkdir -p training_archives/2026-01

# Move used data
mv auto_training_data.json training_archives/2026-01/
mv manual_review_data.json training_archives/2026-01/

# Empty review queue (if all reviewed)
echo "[]" > review_queue.json
```

---

## 🔍 Monitoring & Debugging

### Check Extraction Quality

```python
from production_extractor import ProductionExtractor

extractor = ProductionExtractor()

# Test on specific text
text = "Your car description here..."
result = extractor.extract(text, car_id="test_001")

print(f"ML result:    {result['ml_result']}")
print(f"Regex result: {result['regex_result']}")
print(f"Final:        {result}")
print(f"Confidence:   {result['confidence']}")
```

### View Statistics

```bash
python3 -c "
from production_extractor import ProductionExtractor
import json

extractor = ProductionExtractor()

with open('extraction_stats.json', 'r') as f:
    stats = json.load(f)
    print(json.dumps(stats, indent=2))
"
```

### Check Queue Sizes

```bash
# Auto-training queue
python3 -c "import json; print(f\"Auto-training examples: {len(json.load(open('auto_training_data.json')))}\")"

# Review queue
python3 -c "import json; print(f\"Cases to review: {len(json.load(open('review_queue.json')))}\")"

# Manual corrections
python3 -c "import json; print(f\"Manual corrections: {len(json.load(open('manual_review_data.json')))}\")"
```

---

## 📈 Progress Tracking

Create a simple tracking sheet:

| Date       | Total Cars | Agreements | Disagreements | F1 Score | Notes                          |
|------------|------------|------------|---------------|----------|--------------------------------|
| 2026-01-18 | 0          | -          | -             | 70%      | Initial model (201 examples)   |
| 2026-01-25 | 1000       | 720 (72%)  | 98 (10%)      | 70%      | First week of production       |
| 2026-02-01 | 2000       | 1450 (72%) | 195 (10%)     | 70%      | Reviewed 100 disagreements     |
| 2026-02-08 | 2000       | -          | -             | 82%      | 🎉 Retrained with 1001 total   |
| 2026-02-15 | 3000       | 850 (85%)  | 50 (5%)       | 82%      | Model improving!               |

---

## ❓ FAQ

### Q: How much time does review take?
**A:** ~20-30 cases per hour. If you review 100 cases per week, that's 5-7 hours/month of review work.

### Q: Can I automate the review?
**A:** Partially. You can:
1. Auto-accept when ML confidence is high AND regex agrees
2. Auto-reject when both are None
3. Only review true conflicts

But human review ensures highest quality training data.

### Q: When should I retrain?
**A:** Retrain when:
- You have 300+ new examples (3x your original set)
- Monthly as a regular schedule
- After major regex improvements
- When you notice degrading performance

### Q: What if F1 score doesn't improve?
**A:** Check:
1. Are new examples diverse? (Not just same car model)
2. Are corrections accurate in manual_review_data.json?
3. Is training converging? (Try more iterations)
4. Run consistency check: `python3 check_label_consistency.py manual_review_data.json`

### Q: Can I use this without the ML model?
**A:** Yes! The context-aware regex is already quite good (65-70% accuracy). You can:
```python
from context_aware_patterns import ContextAwarePatterns

patterns = ContextAwarePatterns()
mileage = patterns.find_mileage(text)
year = patterns.find_years(text)
power = patterns.find_power(text)
```

---

## 🎓 Learning Resources

### Understanding Your Model
```bash
# Test current model
python3 test_ml_model.py

# Validate training data
python3 validate_labels.py training_data_labeled.json

# Check label consistency
python3 check_label_consistency.py training_data_labeled.json

# Analyze patterns
python3 analyze_labeled_data.py
```

### Context-Aware Regex
See `context_aware_patterns.py` for patterns that avoid false positives:
- **YEAR**: Excludes STK dates, service dates, part replacement dates
- **MILEAGE**: Excludes electric car range, daily commute distances
- **POWER**: Validates reasonable range (30-500 kW)

---

## 🚧 Roadmap

### Short Term (Next Month)
- [ ] Process 1000+ cars through production system
- [ ] Review first batch of disagreements
- [ ] First model retraining
- [ ] Achieve F1 = 80%+

### Medium Term (3 Months)
- [ ] Automate daily extraction runs
- [ ] Build dashboard for monitoring
- [ ] Achieve F1 = 85%+
- [ ] Reduce manual review to 1 hour/week

### Long Term (6 Months)
- [ ] 5000+ training examples
- [ ] F1 = 90%+
- [ ] Expand to other car attributes (color, transmission, body type)
- [ ] Multi-language support

---

## 🤝 Support

If you encounter issues:

1. **Check Logs**: Production extractor logs disagreements with context
2. **Test Individual Components**:
   ```bash
   python3 context_aware_patterns.py  # Test regex
   python3 ml_extractor.py            # Test ML model
   python3 production_extractor.py    # Test full system
   ```
3. **Validate Data**:
   ```bash
   python3 validate_labels.py auto_training_data.json
   python3 validate_labels.py manual_review_data.json
   ```

---

## 🎉 Success Metrics

You'll know the system is working when:

✅ **Week 1**:
- Successfully extracted 1000+ cars
- 70%+ agreement rate
- auto_training_data.json has 500+ examples

✅ **Month 1**:
- Reviewed 100+ disagreements
- Retrained model with 800+ total examples
- F1 score improved by 5-10%

✅ **Month 3**:
- F1 score > 85%
- Agreement rate > 80%
- Review time < 2 hours/week
- Model confidently handles Czech text variations

---

**You're all set! Start with Step 1 and let the continuous learning begin! 🚀**
