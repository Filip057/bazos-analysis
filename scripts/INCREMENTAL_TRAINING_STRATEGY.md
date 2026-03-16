# 📈 Incremental Training Strategy

## 🎯 Goal: Postupně rozšiřovat training data → stále lepší model

---

## ✅ SPRÁVNÝ PŘÍSTUP: ITERATIVE IMPROVEMENT

```
Round 1: Train on 200 samples  → Model v1 (baseline)
Round 2: Add 300 samples       → Model v2 (75% accuracy)
Round 3: Add 500 samples       → Model v3 (85% accuracy)
Round 4: Add 500 samples       → Model v4 (90% accuracy)
Round 5: Add 500 samples       → Model v5 (93% accuracy)
...
Target: 1500-2000 samples      → Production model (95%+ accuracy)
```

**KEY PRINCIPLE:** Více kvalitních dat = lepší model (až do bodu saturace)

---

## 📊 DATA QUALITY vs QUANTITY

### **Kolik training dat je "dost"?**

| Samples | Expected Accuracy | Status |
|---------|------------------|--------|
| 50-100  | 60-70% | ❌ Too small - model underfits |
| 200-300 | 70-80% | ⚠️  Baseline - works but limited |
| 500-800 | 80-90% | ✅ Good - usable for production |
| 1000-1500 | 90-95% | ✅✅ Very good - production ready |
| 2000-3000 | 95-97% | 🏆 Excellent - diminishing returns start |
| 5000+ | 97-98% | 🏆 Peak - small improvements only |

### **Diminishing Returns:**
```
0 → 500 samples:    +30% accuracy gain (huge!)
500 → 1000:         +10% accuracy gain (significant)
1000 → 2000:        +5% accuracy gain (good)
2000 → 5000:        +2% accuracy gain (small)
5000 → 10000:       +0.5% accuracy gain (minimal)
```

**OPTIMAL SWEET SPOT: 1500-2000 samples**
- High accuracy (90-95%)
- Reasonable labeling effort (~3-5 hours with Claude)
- Good generalization

---

## 🔄 INCREMENTAL WORKFLOW

### **Current State:**
```bash
# Check existing data
ls -lh *training*.json

# training_data_labeled.json:    50 samples
# filtered_training_skoda.json: 181 samples
# training_skoda.json:          193 samples

# TOTAL: ~200-400 samples (good baseline!)
```

### **Round 1: Add 300 samples**

```bash
# 1. Export 300 new offers
python3 scripts/export_for_claude_labeling.py --count 300

# 2. Claude labels → training_data_round1.json

# 3. Merge with existing
python3 scripts/merge_training_data.py \
    --existing training_data_labeled.json filtered_training_skoda.json \
    --new training_data_round1.json \
    --output training_data_v1.json

# Result: ~500-700 samples

# 4. Train model v1
python3 ml/train_model.py --input training_data_v1.json --output ml/models/v1

# 5. Evaluate
python3 ml/test_extractor.py --model ml/models/v1
```

---

### **Round 2: Add 500 samples (focus on hard cases)**

```bash
# 1. Export 500 offers
# TIP: Focus on brands/years where model v1 fails
python3 scripts/export_for_claude_labeling.py --count 500

# 2. Claude labels → training_data_round2.json

# 3. Merge ALL data
python3 scripts/merge_training_data.py \
    --existing training_data_v1.json \
    --new training_data_round2.json \
    --output training_data_v2.json

# Result: ~1000-1200 samples

# 4. Train model v2
python3 ml/train_model.py --input training_data_v2.json --output ml/models/v2

# 5. Compare v1 vs v2
python3 ml/compare_models.py --old ml/models/v1 --new ml/models/v2
```

---

### **Round 3: Add 500 samples (diverse brands)**

```bash
# Export diverse brands (Mazda, BMW, Audi, VW, ...)
python3 scripts/export_for_claude_labeling.py --count 500

# Merge → v3
python3 scripts/merge_training_data.py \
    --existing training_data_v2.json \
    --new training_data_round3.json \
    --output training_data_v3.json

# Result: ~1500-1700 samples

# Train v3
python3 ml/train_model.py --input training_data_v3.json --output ml/models/v3
```

**AT THIS POINT: Should have 90-95% accuracy! 🎉**

---

## 💡 SMART TRAINING STRATEGIES

### **1. Error-Driven Sampling**
```bash
# Find offers where current model FAILS
python3 ml/find_model_errors.py --model ml/models/v2 --count 500

# Export those specific offers
# Label them with Claude
# Add to training data → re-train

# Result: Model learns from its mistakes! ✅
```

### **2. Stratified Sampling**
```
Ensure diverse coverage:
- Different brands (Skoda, Mazda, BMW, VW, Audi, ...)
- Different years (2000-2010, 2010-2020, 2020-2025)
- Different mileage ranges (0-50k, 50-100k, 100k+, 200k+)
- Different fuel types (benzín, diesel, lpg, elektro, hybrid)

Avoid: 90% Skoda + 10% others → model overfits to Skoda!
```

### **3. Hard Negative Mining**
```
Focus on DIFFICULT examples:
- Vague descriptions (missing year/mileage)
- Multiple numbers (confuse model)
- Unusual formats ("150 tis. km" vs "150000")
- Mixed fuel types ("benzín + LPG")

These teach model edge cases!
```

---

## 📊 TRACK PROGRESS

### **Create training log:**

```bash
# training_progress.md

## Round 1 (2026-03-15)
- Samples: 500
- Model: v1
- Accuracy: 82%
- Notes: Good baseline, fails on old cars (pre-2000)

## Round 2 (2026-03-20)
- Samples: 1000 (+500 pre-2000 cars)
- Model: v2
- Accuracy: 88%
- Notes: Much better on old cars, still confuses power with model numbers

## Round 3 (2026-03-25)
- Samples: 1500 (+500 diverse brands)
- Model: v3
- Accuracy: 93%
- Notes: Production ready! 🎉
```

---

## ⚠️ DIMINISHING RETURNS WARNING

### **When to STOP adding more data:**

```
Signs you've hit saturation:
✅ Accuracy > 93%
✅ Adding 500 samples → <1% accuracy gain
✅ Model errors are mostly in garbage/ambiguous offers
✅ Training time becomes too long (>30 min)

At this point:
→ Focus on data QUALITY, not quantity
→ Clean up mislabeled examples
→ Add feature engineering (context patterns)
→ Try different model architectures
```

---

## 🎯 RECOMMENDED ROADMAP

### **Phase 1: Quick Start (TODAY!)**
```bash
# Current: ~200-400 samples
# Goal: 700 samples

python3 scripts/export_for_claude_labeling.py --count 300
# Claude labels → merge → train v1

Expected: 75-85% accuracy
```

### **Phase 2: Production Ready (NEXT WEEK)**
```bash
# Goal: 1500 samples

# Add 500 samples (diverse brands)
# Add 300 samples (error cases from v1)

Expected: 90-93% accuracy
```

### **Phase 3: Excellence (OPTIONAL)**
```bash
# Goal: 2000-2500 samples

# Add 500-1000 hard cases
# Focus on edge cases

Expected: 93-95% accuracy
```

### **Phase 4: Diminishing Returns (STOP HERE!)**
```
Beyond 2500 samples:
- Minimal gains (<1%)
- Better to improve extraction logic
- Or use ensemble methods
```

---

## 📈 EXPECTED TIMELINE

```
Week 1:
  Day 1: Export 300 + Claude label (1 hour)
  Day 2: Merge + train v1 (30 min)
  Day 3: Test + evaluate (1 hour)

  Result: ~700 samples, 75-85% accuracy

Week 2:
  Day 1: Export 500 + Claude label (2 hours)
  Day 2: Merge + train v2 (30 min)
  Day 3: Test + compare v1 vs v2 (1 hour)

  Result: ~1200 samples, 85-90% accuracy

Week 3:
  Day 1: Export 500 + Claude label (2 hours)
  Day 2: Merge + train v3 (30 min)
  Day 3: Final evaluation + deploy (1 hour)

  Result: ~1700 samples, 90-95% accuracy

TOTAL EFFORT: ~10-15 hours over 3 weeks
RESULT: Production-ready model! 🎉
```

---

## 🚀 START NOW!

```bash
# Step 1: Export 300 offers (easy win!)
python3 scripts/export_for_claude_labeling.py --count 300

# Step 2: Claude chat → training_data_new.json

# Step 3: Merge with existing
python3 scripts/merge_training_data.py \
    --existing training_data_labeled.json filtered_training_skoda.json \
    --new training_data_new.json \
    --output training_data_v1.json

# Step 4: Train!
python3 ml/train_model.py --input training_data_v1.json --output ml/models/v1

# Step 5: Celebrate! 🎉
```

---

## 📚 KEY TAKEAWAYS

✅ **More data = better model** (up to ~2000 samples)
✅ **Incremental approach is SMART** (don't start from scratch!)
✅ **Deduplication is CRITICAL** (avoid training on same offer twice)
✅ **Quality > quantity** after 1500-2000 samples
✅ **Track progress** (know when to stop!)
✅ **Sweet spot: 1500-2000 samples** (90-95% accuracy)

**🎯 START WITH 300 → ADD 500 → ADD 500 → DONE!**
