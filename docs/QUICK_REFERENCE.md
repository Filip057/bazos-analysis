# Quick Reference - Production Learning System

## 🚀 Daily Operations

### Run Production Extraction (Test)
```bash
python3 production_extractor.py
```

### Check Queue Sizes
```bash
# Check how many need review
python3 -c "import json; print(f'To review: {len(json.load(open(\"review_queue.json\")))}')" 2>/dev/null || echo "0"

# Check auto-collected training data
python3 -c "import json; print(f'Auto-collected: {len(json.load(open(\"auto_training_data.json\")))}')" 2>/dev/null || echo "0"

# Check manual corrections
python3 -c "import json; print(f'Manual corrections: {len(json.load(open(\"manual_review_data.json\")))}')" 2>/dev/null || echo "0"
```

### Weekly: Review Disagreements (when queue > 50)
```bash
python3 review_disagreements.py
```

### Monthly: Retrain Model (when you have 300+ new examples)
```bash
# Check total training data
python3 -c "
import json
orig = len(json.load(open('training_data_labeled.json', 'r')))
auto = len(json.load(open('auto_training_data.json', 'r'))) if __import__('os').path.exists('auto_training_data.json') else 0
manual = len(json.load(open('manual_review_data.json', 'r'))) if __import__('os').path.exists('manual_review_data.json') else 0
print(f'Total: {orig + auto + manual} (orig:{orig} + auto:{auto} + manual:{manual})')
"

# Retrain
python3 retrain_model.py --iterations 150
```

---

## 📊 Monitoring Commands

### View Extraction Statistics
```bash
python3 -c "
from production_extractor import ProductionExtractor
extractor = ProductionExtractor()
extractor.print_stats()
"
```

### Test Model on Custom Text
```bash
python3 -c "
from production_extractor import ProductionExtractor
extractor = ProductionExtractor()
text = 'Škoda Octavia 2015, najeto 150000 km, výkon 110 kW, diesel'
result = extractor.extract(text, car_id='test')
print(result)
"
```

### Validate Training Data
```bash
# Original labels
python3 validate_labels.py training_data_labeled.json

# Auto-collected
python3 validate_labels.py auto_training_data.json

# Manual corrections
python3 validate_labels.py manual_review_data.json
```

---

## 🔧 Integration with Scraper

Add to your `data_scrap.py`:

```python
from production_extractor import ProductionExtractor

# Initialize once at startup
extractor = ProductionExtractor()

# In your scraping function
async def scrape_car_listing(car_id, description):
    # ... your scraping code ...

    # Extract car data with ML + regex
    result = extractor.extract(description, car_id=car_id)

    # Use extracted data
    car_data = {
        'id': car_id,
        'mileage': result['mileage'],
        'year': result['year'],
        'power': result['power'],
        'fuel': result['fuel'],
        'confidence': result['confidence'],  # 'high', 'medium', 'low'
        'needs_review': result['flagged_for_review']
    }

    # Save to database
    # await save_to_db(car_data)

    return car_data

# After scraping batch (e.g., end of daily run)
extractor.save_queues()  # Saves auto_training_data.json and review_queue.json
extractor.print_stats()  # Shows agreement rates
```

---

## 📅 Recommended Schedule

### Daily
- Run scraper with production_extractor integration
- Monitor agreement rates (should be 70%+ early, 85%+ after retraining)

### Weekly (Friday afternoon, 30-60 min)
```bash
# 1. Check review queue size
python3 -c "import json; print(len(json.load(open('review_queue.json'))))"

# 2. If > 50 cases, start review
python3 review_disagreements.py

# 3. Review 50-100 cases (takes ~30-60 min)
# Tip: You can press Ctrl+C anytime, progress is saved automatically
```

### Monthly (First Monday, 1-2 hours)
```bash
# 1. Check accumulated data
python3 -c "
import json, os
auto = len(json.load(open('auto_training_data.json'))) if os.path.exists('auto_training_data.json') else 0
manual = len(json.load(open('manual_review_data.json'))) if os.path.exists('manual_review_data.json') else 0
print(f'Ready to retrain with {auto + manual} new examples')
"

# 2. Retrain if > 300 new examples
python3 retrain_model.py --iterations 150

# 3. Test new model
python3 test_ml_model.py

# 4. Archive old data
mkdir -p training_archives/$(date +%Y-%m)
mv auto_training_data.json training_archives/$(date +%Y-%m)/
mv manual_review_data.json training_archives/$(date +%Y-%m)/
echo "[]" > review_queue.json
```

---

## 🎯 Key Metrics to Watch

### Healthy System
| Metric              | Target    | Warning Level |
|---------------------|-----------|---------------|
| Full Agreements     | 70-85%    | < 50%         |
| Disagreements       | 5-15%     | > 30%         |
| F1 Score (ML model) | 80-90%    | < 65%         |
| Review Queue Size   | < 200     | > 500         |

### Expected Progression

**Week 1** (Initial deployment):
- Agreement: ~70%
- F1 Score: 70%
- New training data: 700 examples/week

**Month 1** (After first retraining):
- Agreement: ~80%
- F1 Score: 80-82%
- New training data: 800 examples/week

**Month 3** (Mature system):
- Agreement: ~85%
- F1 Score: 85-88%
- New training data: 850 examples/week
- Review time: < 1 hour/week

---

## 🛠️ Troubleshooting

### Low Agreement Rate (< 50%)

**Possible Causes:**
1. Model file corrupted or missing
2. Regex patterns changed
3. Data format changed on Bazos.cz

**Fix:**
```bash
# Check model exists
ls -lh ml_models/car_ner/

# Test components separately
python3 context_aware_patterns.py  # Test regex
python3 ml_extractor.py            # Test ML model

# Check extraction on sample text
python3 production_extractor.py
```

### High Disagreement Rate (> 30%)

**Possible Causes:**
1. Model needs retraining
2. Regex patterns too strict/loose
3. New car listing format on Bazos.cz

**Fix:**
```bash
# Review some cases to identify pattern
python3 review_disagreements.py

# Look for common errors
python3 -c "
import json
from collections import Counter

queue = json.load(open('review_queue.json'))
disagreement_fields = []
for case in queue:
    disagreement_fields.extend(case['comparison']['disagreements'])

print('Most common disagreements:')
for field, count in Counter(disagreement_fields).most_common():
    print(f'  {field}: {count} cases')
"

# If one field dominates, fix that specific pattern
# Then retrain
```

### Model Not Improving After Retraining

**Possible Causes:**
1. Not enough new examples (need 300+)
2. New examples not diverse
3. Training iterations too low
4. Label quality issues

**Fix:**
```bash
# Check data quality
python3 validate_labels.py auto_training_data.json
python3 check_label_consistency.py manual_review_data.json

# Analyze diversity
python3 analyze_labeled_data.py

# Try more iterations
python3 retrain_model.py --iterations 200
```

---

## 💾 Backup & Recovery

### Backup Before Retraining
```bash
# Backup current model
tar -czf ml_models_backup_$(date +%Y%m%d).tar.gz ml_models/

# Backup training data
tar -czf training_data_backup_$(date +%Y%m%d).tar.gz \
  training_data_labeled.json \
  auto_training_data.json \
  manual_review_data.json
```

### Restore Previous Model
```bash
# Restore from backup
tar -xzf ml_models_backup_20260118.tar.gz

# Or use git
git checkout HEAD~1 -- ml_models/
```

---

## 📈 Performance Optimization

### Speed Up Extraction
```python
# Use batch processing
from production_extractor import ProductionExtractor

extractor = ProductionExtractor()

# Process multiple texts
results = []
for car_id, text in car_listings:
    result = extractor.extract(text, car_id=car_id)
    results.append(result)

# Save once at the end (faster)
extractor.save_queues()
```

### Reduce Review Time
```python
# Filter review queue - only show cases with 2+ disagreements
import json

queue = json.load(open('review_queue.json'))
high_priority = [
    case for case in queue
    if len(case['comparison']['disagreements']) >= 2
]

print(f"High priority: {len(high_priority)}/{len(queue)} cases")
```

---

## 📚 File Locations

```
bazos-analysis/
├── production_extractor.py          # Main production extraction
├── review_disagreements.py          # Interactive review tool
├── retrain_model.py                 # Model retraining script
├── context_aware_patterns.py        # Smart regex patterns
├── ml_extractor.py                  # ML model wrapper
│
├── ml_models/
│   └── car_ner/                     # Current production model
│
├── training_data_labeled.json       # Original 201 examples
├── auto_training_data.json          # Auto-collected (agreements)
├── manual_review_data.json          # Human corrections
├── review_queue.json                # Cases needing review
├── extraction_stats.json            # Performance metrics
│
└── training_archives/               # Historical data
    ├── 2026-01/
    ├── 2026-02/
    └── ...
```

---

## 🎓 Learn More

- **Full Guide**: `PRODUCTION_LEARNING_GUIDE.md`
- **Context-Aware Patterns**: See `context_aware_patterns.py` for regex examples
- **ML Model Details**: See `ml_extractor.py` for spaCy NER implementation
- **Labeling Tools**: `label_data_assisted.py` for manual labeling if needed

---

## 🆘 Emergency Commands

### Reset Everything (Start Fresh)
```bash
# ⚠️  WARNING: This deletes all production data!

# Backup first!
mkdir -p backups/$(date +%Y%m%d)
cp auto_training_data.json manual_review_data.json review_queue.json backups/$(date +%Y%m%d)/

# Reset queues
echo "[]" > auto_training_data.json
echo "[]" > manual_review_data.json
echo "[]" > review_queue.json

# Reset stats
echo '{"total_extractions": 0, "full_agreements": 0, "partial_agreements": 0, "disagreements": 0}' > extraction_stats.json
```

### Quick Health Check
```bash
#!/bin/bash
echo "=== Production System Health Check ==="
echo ""
echo "📁 Files:"
ls -lh training_data_labeled.json ml_models/car_ner/*.json 2>/dev/null || echo "  ⚠️  Model files missing"
echo ""
echo "📊 Queue Sizes:"
python3 -c "import json; print(f\"  Auto: {len(json.load(open('auto_training_data.json')))} examples\")" 2>/dev/null || echo "  Auto: 0 examples"
python3 -c "import json; print(f\"  Review: {len(json.load(open('review_queue.json')))} cases\")" 2>/dev/null || echo "  Review: 0 cases"
python3 -c "import json; print(f\"  Manual: {len(json.load(open('manual_review_data.json')))} corrections\")" 2>/dev/null || echo "  Manual: 0 corrections"
echo ""
echo "✅ Last Model Update:"
ls -lh ml_models/car_ner/ | grep -E '(meta|config)' | tail -1
echo ""
echo "📈 Total Training Data Available:"
python3 -c "
import json, os
o = len(json.load(open('training_data_labeled.json')))
a = len(json.load(open('auto_training_data.json'))) if os.path.exists('auto_training_data.json') else 0
m = len(json.load(open('manual_review_data.json'))) if os.path.exists('manual_review_data.json') else 0
print(f\"  {o + a + m} examples (orig:{o} + auto:{a} + manual:{m})\")
"
```

Save this as `health_check.sh` and run with `bash health_check.sh`

---

**Need help? Check `PRODUCTION_LEARNING_GUIDE.md` for detailed explanations!**
