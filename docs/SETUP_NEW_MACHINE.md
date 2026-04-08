# New Machine Setup Guide

## 🖥️ Setting Up on a New Machine

Follow these steps to set up the complete ML training workflow on a new machine.

---

## Step 1: Clone the Repository

```bash
cd ~/Dokumenty/bazos\ analysis
git clone <repository-url> bazos-analysis
cd bazos-analysis
git checkout claude/refactor-scraper-performance-cSBoN
```

---

## Step 2: Install Python Dependencies

```bash
# Install all required packages
pip3 install -r requirements.txt

# Or with virtual environment (recommended):
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Key packages installed:**
- `spacy` - ML model framework
- `beautifulsoup4` - Web scraping
- `aiohttp` - Async HTTP requests
- `flask` - Web API (optional)
- `sqlalchemy` - Database (optional)

---

## Step 3: Download Czech Language Model (Optional)

If you want to use pre-trained Czech NER:
```bash
python3 -m spacy download cs_core_news_sm
```

**Note:** This is optional! Our custom model doesn't need it.

---

## Step 4: Set Up Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env and set your values:
# - SECRET_KEY (generate with: python3 -c "import secrets; print(secrets.token_hex(32))")
# - MYSQL_* settings (only if using database)
```

---

## Step 5: Verify Installation

```bash
# Test that all imports work
python3 -c "import spacy, bs4, aiohttp, sqlalchemy; print('✅ All dependencies installed!')"
```

---

## Step 6: Check Training Data

```bash
# See if you have labeled training data
ls -lh training_data_labeled.json

# Should show: training_data_labeled.json with your labeled examples
```

---

## Step 7: Run Workflow Manager

```bash
python3 workflow_manager.py
```

Then follow this sequence for first-time setup:

```
1. Choose 7 (Check Training Data Quality)
   → See what training data you have
   → Check entity distribution

2. Choose 4 (Train Initial Model)
   → Option 1 (default 30 iterations)
   → Wait 2-5 minutes for training

3. Choose 6 (Evaluate Model Quality)
   → Check F1 score (target: 70%+ for start)

4. Ready! Now you can:
   → Choose 1 (Scrape Data) to collect new data
   → Choose 3 (Review Disagreements) to label more
   → Choose 5 (Retrain) to improve the model
```

---

## 📦 What You Should Have

After setup, your directory should contain:

```
bazos-analysis/
├── ml/
│   ├── ml_extractor.py          # ML extraction engine
│   ├── production_extractor.py  # Production RAW workflow
│   ├── train_ml_model.py        # Training script
│   └── ...
├── scraper/
│   ├── data_scrap.py            # Main scraper
│   └── ...
├── workflow_manager.py          # ⭐ Your main tool
├── training_data_labeled.json   # Your labeled examples
├── requirements.txt             # Dependencies
├── .env                         # Environment config
└── WORKFLOW.md                  # Complete docs
```

---

## 🎓 First Training Run

When you train for the first time:

**Minimum Requirements:**
- 50+ labeled examples (bare minimum)
- 100+ labeled examples (recommended)
- 200+ labeled examples (ideal)

**Expected Results:**
- With 100 examples: ~60-65% F1 score
- With 200 examples: ~70-75% F1 score
- After retraining with 100+ manual reviews: ~80%+ F1 score

**Training Time:**
- 30 iterations: ~2-3 minutes
- 100 iterations: ~5-10 minutes
- Depends on CPU speed and data size

---

## 🔧 Troubleshooting

### Problem: ModuleNotFoundError

```bash
# Solution: Install dependencies
pip3 install -r requirements.txt
```

### Problem: spacy model not found

```bash
# Solution: Our custom model doesn't need pre-trained Czech
# Just train your own model (Option 4 in workflow_manager)
```

### Problem: training_data_labeled.json not found

```bash
# Solution: You need labeled training data
# Either:
# 1. Copy from another machine
# 2. Create new labeled data using label_data.py
# 3. Or start fresh by labeling disagreements after scraping
```

### Problem: MySQL connection error

```bash
# Solution: Use --skip-db flag when scraping
# In workflow_manager: Choose 1 → Option 1 (without database)
```

---

## 🚀 Quick Start (TL;DR)

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Verify installation
python3 -c "import spacy; print('OK')"

# 3. Run workflow manager
python3 workflow_manager.py

# 4. Train initial model (Option 4)
# 5. Start scraping (Option 1)
```

---

## 📖 Next Steps

After successful setup:

1. **Read WORKFLOW.md** - Complete workflow documentation
2. **Read QUICKSTART.md** - Quick reference guide
3. **Train your model** - Option 4 in workflow manager
4. **Start the cycle:**
   - Scrape → Review → Retrain → Repeat!

---

## 💡 Tips for New Machine

1. **Use virtual environment** - Keeps dependencies isolated
2. **Train locally first** - Verify everything works
3. **Start with small scrape** - Test before large runs
4. **Check F1 score** - Should be 70%+ to start
5. **Backup training data** - Copy training_data_labeled.json to cloud

---

## ✅ Setup Complete!

You're ready to start training! Run:

```bash
python3 workflow_manager.py
```

And choose option 4 (Train Initial Model) to begin! 🎉
