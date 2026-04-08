# Machine Learning Guide for Car Data Extraction
## Learn ML by Solving a Real Problem!

This guide will teach you machine learning basics by solving your real problem: extracting car data from messy text.

---

## 📚 Table of Contents

1. [What is Machine Learning?](#what-is-machine-learning)
2. [Why ML for Your Problem?](#why-ml-for-your-problem)
3. [What You'll Learn](#what-youll-learn)
4. [Setup Instructions](#setup-instructions)
5. [Step-by-Step Workflow](#step-by-step-workflow)
6. [Understanding the Code](#understanding-the-code)
7. [Tips & Best Practices](#tips--best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What is Machine Learning?

Machine Learning (ML) teaches computers to learn patterns from examples, instead of programming explicit rules.

### Traditional Programming (What you have now with regex):
```
You write: "If text contains '120000 km', extract 120000"
Problem: Fails on "120 tis km", "120.000 km", "najeto 120000"
```

### Machine Learning:
```
You show 100 examples: "120000 km" → MILEAGE
Computer learns: "Numbers followed by 'km' are probably mileage"
Bonus: Also learns "tis km", "tisíc km", "najetých km", etc.
```

---

## Why ML for Your Problem?

Your regex currently catches maybe **70-80%** of cases. ML can get you to **90-95%**.

### Real examples from Czech car listings:

```
❌ Regex fails on:
- "najeto 85 tis km"          (tis without dot)
- "120.000 km najetých"       (different word order)
- "rok výroby: 2015"          (colon separator)
- "motor o výkonu 110kW"      (extra words)

✅ ML learns all these patterns!
```

---

## What You'll Learn

By following this guide, you'll understand:

1. **Named Entity Recognition (NER)**
   - Finding specific information in text
   - Like highlighting names/dates in a document

2. **Training Data**
   - Why ML needs examples
   - How to create quality training data

3. **Model Training**
   - How computers learn from examples
   - What "loss" and "iterations" mean

4. **Model Evaluation**
   - How to measure if your model is good
   - Precision, Recall, F1 scores

5. **Production Deployment**
   - Using ML in real applications
   - Hybrid approaches (regex + ML)

---

## Setup Instructions

### 1. Install spaCy

```bash
pip install spacy tqdm
```

That's it! SpaCy is lightweight (~100MB) and runs on CPU.

### 2. Verify Installation

```bash
python -c "import spacy; print('✓ spaCy installed')"
```

---

## Step-by-Step Workflow

### Phase 1: Get Your Data (10 minutes)

First, you need car descriptions to label.

```bash
# Export 100 descriptions from your database
python export_descriptions.py --output descriptions.txt --limit 100
```

This creates a file like:
```
Chevrolet Cruze, rok 2015, 120000 km, 110 kW
BMW X5, rok 2018, 85000 km, 150 kW
Škoda Octavia, rok 2016, 95000 km, 105 kW
...
```

### Phase 2: Label Your Data (30-60 minutes)

This is the most important step! You're teaching the computer what to look for.

```bash
# Start labeling (do 50 examples to start)
python label_data.py --input descriptions.txt --output training_data.json --limit 50
```

The tool will guide you through labeling:

```
[1/50]
Text: Chevrolet Cruze, rok 2015, 120000 km, 110 kW

📏 MILEAGE - Find the kilometers
  Type the mileage text: 120000 km

📅 YEAR - Find the year
  Type the year text: 2015

⚡ POWER - Find the power
  Type the power text: 110 kW
```

**Tips for good labeling:**
- Be consistent! Always label the same way
- Include the unit (km, kW) in your label
- Type exactly what's in the text
- Press Enter to skip if something is missing

**How many examples do you need?**
- **50 examples**: Basic model, ~80% accuracy
- **100 examples**: Good model, ~85% accuracy
- **200+ examples**: Great model, ~90%+ accuracy

Start with 50, you can always add more later!

### Phase 3: Train Your Model (5 minutes)

Now the computer learns from your examples.

```bash
python train_ml_model.py --data training_data.json --iterations 30
```

What you'll see:
```
Training Data Analysis:
  Total examples: 50
  Total entities: 140
  Average entities per example: 2.8

🎓 Training model with 30 iterations...

Iteration 5/30, Loss: 45.2
Iteration 10/30, Loss: 28.7
Iteration 15/30, Loss: 18.3
Iteration 20/30, Loss: 12.1
Iteration 25/30, Loss: 8.4
Iteration 30/30, Loss: 5.2

✓ Model saved to ./ml_models/car_ner

Model Performance:
  Precision: 92.3% (how many predictions were correct)
  Recall:    88.7% (how many entities were found)
  F1 Score:  90.4% (overall accuracy)
```

**Understanding the output:**

- **Loss going down** = Model is learning! 📉
- **Loss stuck high** = Need more training data or iterations
- **F1 Score > 80%** = Good model! ✅
- **F1 Score < 70%** = Need more/better training data

### Phase 4: Test Your Model (2 minutes)

```bash
# Test on new text
python -c "
from ml_extractor import CarDataExtractor
extractor = CarDataExtractor('./ml_models/car_ner')
result = extractor.extract('Škoda Fabia 2019, najeto 45000 km, výkon 70kW')
print(result)
"
```

Output:
```python
{'mileage': 45000, 'year': 2019, 'power': 70, 'fuel': None}
```

### Phase 5: Integrate with Your Scraper (5 minutes)

Now use your model in production!

Option A: **Test the hybrid extractor**
```bash
python integrate_ml.py
```

Option B: **Integrate into your scraper**

Modify `data_scrap.py`:

```python
from integrate_ml import HybridCarExtractor

# Initialize once at start
extractor = HybridCarExtractor()

# Use in your process_data function
async def process_data(brand, url, description, heading, price):
    # Use hybrid extraction instead of regex-only
    extracted = extractor.extract_all(description, heading)

    model = get_model(brand=brand, header=heading)

    car_data = {
        "brand": brand,
        "model": model,
        "year_manufacture": extracted['year'],     # From ML
        "mileage": extracted['mileage'],           # From ML
        "power": extracted['power'],               # From ML
        "price": price,
        "heading": heading,
        "url": url
    }
    return car_data
```

**Benefits of hybrid approach:**
- Tries regex first (fast)
- Falls back to ML only when needed
- Best of both worlds!

---

## Understanding the Code

### How NER Works

Named Entity Recognition finds and classifies specific information in text.

```python
Text: "Škoda 2015, 120000 km, 110 kW"

Step 1: Tokenize
["Škoda", "2015", ",", "120000", "km", ",", "110", "kW"]

Step 2: Classify each token
"Škoda"  → O (Outside)
"2015"   → B-YEAR (Beginning of Year entity)
","      → O
"120000" → B-MILEAGE
"km"     → I-MILEAGE (Inside Mileage entity)
","      → O
"110"    → B-POWER
"kW"     → I-POWER

Step 3: Extract entities
YEAR: 2015
MILEAGE: 120000 km
POWER: 110 kW
```

### Training Process

```python
# 1. Model makes a prediction
prediction = model.predict("Škoda 2015, 120000 km")
# prediction: YEAR=2019 (WRONG!), MILEAGE=120000 (CORRECT)

# 2. Compare with correct answer (your label)
correct = {"YEAR": 2015, "MILEAGE": 120000}

# 3. Calculate error (loss)
loss = how_wrong(prediction, correct)  # High loss = very wrong

# 4. Adjust model weights
model.adjust_to_reduce_error()

# 5. Repeat for all examples
# Each iteration, model gets better!
```

### What is "Loss"?

Loss measures how wrong the model is:
- **High loss (100+)**: Model is guessing randomly
- **Medium loss (20-50)**: Model is learning
- **Low loss (<10)**: Model is good
- **Very low (<5)**: Model might be overfitting

### Evaluation Metrics

```python
# Given 100 test cases:

True Positives (TP):  Model found 85 entities correctly
False Positives (FP): Model found 5 entities that don't exist
False Negatives (FN): Model missed 10 actual entities

Precision = TP / (TP + FP) = 85 / 90 = 94.4%
  → "When model says it found something, how often is it correct?"

Recall = TP / (TP + FN) = 85 / 95 = 89.5%
  → "Of all entities that exist, how many did model find?"

F1 Score = 2 * (Precision * Recall) / (Precision + Recall) = 91.9%
  → "Overall accuracy (balanced between precision and recall)"
```

**Rule of thumb:**
- F1 > 90%: Excellent
- F1 80-90%: Good
- F1 70-80%: Okay
- F1 < 70%: Need improvement

---

## Tips & Best Practices

### 1. Quality > Quantity in Training Data

**Bad labeling** (inconsistent):
```
Example 1: Label "120000 km"
Example 2: Label "120000" (without km)
Example 3: Label "120 tis"
→ Model gets confused!
```

**Good labeling** (consistent):
```
Always label: "120000 km", "85 tis km", "50000km"
→ Model learns the pattern clearly
```

### 2. Start Small, Improve Iteratively

```
Day 1: Label 50 examples → Train → 80% accuracy
Day 2: Find where it fails → Label 25 more → 85% accuracy
Day 3: Label 25 more edge cases → 90% accuracy
```

Don't try to get 1000 examples on day 1!

### 3. Focus on Hard Cases

After first training, your model will fail on certain patterns. Label more of those!

```bash
# Continue labeling where you left off
python label_data.py --input descriptions.txt --output training_data.json --continue --limit 25
```

### 4. Check Your Labels

Before training, look at your `training_data.json`:

```json
[
  ["Škoda 2015, 120000 km", {
    "entities": [
      [6, 10, "YEAR"],        // "2015"
      [12, 21, "MILEAGE"]     // "120000 km"
    ]
  }]
]
```

Verify:
- Numbers make sense (start < end)
- Labels are correct
- No overlapping entities

### 5. Monitor Statistics

```bash
# After integrating, check hybrid extractor stats
python integrate_ml.py
```

Output:
```
Hybrid Extractor Statistics:
Total extractions:     1000
Regex only:            750 (75%)    ← Most cases handled by regex
ML helped:             200 (20%)    ← ML filled in gaps
Still failed:          50 (5%)      ← Need more training data
```

If "Still failed" is > 10%, add more training data for those cases.

---

## Troubleshooting

### Problem: "Model Loss Not Decreasing"

```
Iteration 10/30, Loss: 89.4
Iteration 20/30, Loss: 87.1
Iteration 30/30, Loss: 85.2
```

**Solutions:**
1. Check your labels are correct
2. Add more training data (need at least 50 examples)
3. Increase iterations: `--iterations 50`

### Problem: "Low F1 Score (<70%)"

**Solutions:**
1. Add more training examples (aim for 100+)
2. Check for labeling inconsistencies
3. Make sure you're labeling all entity types

### Problem: "Model Works on Training but Not Real Data"

This is called **overfitting**. Model memorized training data.

**Solutions:**
1. Add more diverse training examples
2. Reduce training iterations
3. Use more training data

### Problem: "Module Not Found"

```bash
ModuleNotFoundError: No module named 'spacy'
```

**Solution:**
```bash
pip install spacy tqdm
```

### Problem: "Can't Find Model"

```
Model not found at ./ml_models/car_ner
```

**Solution:**
Train the model first:
```bash
python train_ml_model.py --data training_data.json
```

---

## Next Steps

Once you have a working model:

### 1. Improve Continuously

```bash
# Every week, check failed extractions
grep "failed" scraper.log > failed_cases.txt

# Label the failed cases
python label_data.py --input failed_cases.txt --output training_data.json --continue

# Retrain with new data
python train_ml_model.py --data training_data.json --iterations 30
```

### 2. Track Performance Over Time

Keep a log:
```
Week 1: F1=82%, Regex=75%, ML=20%, Failed=5%
Week 2: F1=87%, Regex=75%, ML=22%, Failed=3%
Week 3: F1=91%, Regex=75%, ML=23%, Failed=2%
```

### 3. Expand to Other Fields

Once you master mileage/year/power, add:
- **FUEL**: benzín, nafta, hybrid, elektro
- **COLOR**: černá, bílá, červená
- **TRANSMISSION**: automatická, manuální

Just add more labels in your training data!

---

## Understanding spaCy vs Transformers/BERT

You chose **spaCy**, which is perfect for your use case. Here's why:

| Aspect | spaCy NER | BERT/Transformers |
|--------|-----------|-------------------|
| **Learning curve** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐ Complex |
| **CPU speed** | ⚡ Fast (100ms) | 🐢 Slow (2-5s) |
| **Memory** | 💚 ~100MB | 💛 ~500MB |
| **Training time** | ⏱️ Minutes | ⏳ Hours |
| **Best for** | Extraction (NER) | Understanding (semantics) |
| **When to use** | Your use case | Sentiment, translation |

**BERT/Transformers** are like a nuclear reactor - powerful but overkill for turning on a light bulb.
**spaCy NER** is like a light switch - perfect for the job.

---

## Resources for Learning More

1. **spaCy Documentation**: https://spacy.io/usage/training
2. **NER Explanation**: https://spacy.io/usage/linguistic-features#named-entities
3. **Training Tips**: https://spacy.io/usage/training#tips-training-data

---

## Summary: Your ML Journey

```
Step 1: Export data          (10 min)  ✓ python export_descriptions.py
Step 2: Label 50 examples    (30 min)  ✓ python label_data.py
Step 3: Train model          (5 min)   ✓ python train_ml_model.py
Step 4: Evaluate             (2 min)   ✓ Check F1 score
Step 5: Integrate            (5 min)   ✓ Use HybridCarExtractor
Step 6: Improve iteratively  (ongoing) ✓ Add more training data

Total time to working ML model: ~1 hour
```

**You've learned:**
- ✅ What ML is and why it's useful
- ✅ How to create training data
- ✅ How to train a model
- ✅ How to evaluate performance
- ✅ How to deploy in production
- ✅ How to improve over time

**Congratulations! You're now doing machine learning!** 🎉

Remember: ML is not magic, it's just learning from examples. The more good examples you give it, the better it gets.

---

## Questions?

Common questions:

**Q: Will this slow down my scraper?**
A: No! Regex runs first (microseconds). ML only runs when regex fails (~100ms on CPU).

**Q: How much better will it be?**
A: Typically 10-15% improvement. From 75% success to 85-90% success.

**Q: Can I train on my own computer?**
A: Yes! spaCy works great on CPU. No GPU needed.

**Q: What if I have only 20 examples?**
A: Start with those! You'll get ~70% accuracy. Add more later to improve.

**Q: How often should I retrain?**
A: Once a month, or when you notice the failure rate increasing.

---

Good luck with your ML journey! 🚀
