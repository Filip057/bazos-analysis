# Quick Start Guide - RAW Data Workflow

## 🚀 Get Started in 3 Steps

### Step 1: Pull Latest Changes
```bash
cd ~/Dokumenty/bazos\ analysis/bazos-analysis
git pull origin claude/refactor-scraper-performance-cSBoN
```

### Step 2: Run Workflow Manager
```bash
python3 workflow_manager.py
```

### Step 3: Follow the Menu!
```
1. Scrape Data (choose option 1 - without database)
2. Clean Duplicates (option 3 - clean both)
3. Review Disagreements (start labeling RAW data!)
4. Retrain Model (when you have enough labeled data)
5. View Statistics (check your improvements!)
```

---

## 🎯 What Changed in This Session

### ✅ Major Architecture Improvement: RAW Data Workflow

**BEFORE (Wrong):**
- Normalized before comparison → many false disagreements
- "benzín" vs "benzin" → DISAGREEMENT (but both are same!)
- Training data didn't match actual text
- Fuel accuracy: 22%

**AFTER (Correct):**
- Compare RAW values → only real disagreements
- "dieselový" vs "diesel" → DISAGREEMENT (you want to see this!)
- Training data matches exact text
- Expected fuel accuracy: 60-70%+

---

## 📦 New Files Created

1. **workflow_manager.py** - Interactive menu (no more terminal commands!)
2. **ml/normalize_for_db.py** - Separate normalization tool
3. **WORKFLOW.md** - Complete documentation
4. **ml/deduplicate_*.py** - Scripts to clean duplicates

---

## 🔧 Fixed Files

1. **ml/production_extractor.py** - Removed normalization from comparison
2. **scraper/data_scrap.py** - Already includes heading ✓
3. **ml/review_disagreements.py** - Added quit/skip everywhere
4. **.gitignore** - Excludes generated files

---

## 📊 Complete Workflow

```
┌─────────────────────────────────────┐
│  1. Scrape Data (RAW extraction)    │
│     ↓                                │
│  2. Clean Duplicates (if needed)    │
│     ↓                                │
│  3. Review Disagreements (label!)   │
│     ↓                                │
│  4. Retrain Model (improve!)        │
│     ↓                                │
│  5. View Statistics (check!)        │
│     ↓                                │
│  Repeat! (continuous improvement)   │
└─────────────────────────────────────┘
```

---

## 💡 Pro Tips

### Fresh Start (Recommended)
```bash
python3 workflow_manager.py
# Choose option 7 (Reset Workflow)
# Then option 1 (Scrape Data)
```

This deletes old normalized data and generates fresh RAW data!

### Why Reset?
Your current `review_queue.json` has **normalized** values from before the fix.
New workflow needs **RAW** values for proper training!

### What You'll See After Reset:
```
OLD: "benzín" vs "benzin" (false disagreement)
NEW: "benzínový" vs "diesel" (real disagreement!)
```

---

## 📖 Documentation

- **WORKFLOW.md** - Complete workflow explanation
- **workflow_manager.py** - Interactive tool with built-in help
- **ml/normalize_for_db.py** - Normalization examples

---

## 🎓 Training Philosophy

**Label what you SEE in the text:**
- ✅ "benzínový" (appears in text!)
- ✅ "145 KW" (with unit!)
- ✅ "187.000 km" (with dots!)

**NOT what you want in database:**
- ❌ "benzín" (normalized, not in text)
- ❌ "145" (lost context)
- ❌ "187000" (normalized)

**Normalization happens separately** - only for database, not for training!

---

## 🔥 Expected Improvements

After re-scraping with RAW workflow:

**Extraction Quality:**
- Fewer false disagreements (no more "benzín" vs "benzin")
- Clear view of ML strengths/weaknesses
- Better training data (matches actual text)

**ML Model:**
- Learns real variations: "benzínový", "dieselový", "TDI"
- Learns with context: "145 KW", "187.000 km"
- Expected accuracy boost: 22% → 60-70%+

**Your Work:**
- Less manual review (fewer false disagreements)
- Better insights (see what ML actually catches)
- Faster improvement (better training data)

---

## ⚠️ Important Notes

1. **Delete old review_queue.json before scraping!**
   - Old file has normalized data
   - New workflow needs RAW data
   - Use workflow_manager option 7 (Reset)

2. **Always use workflow_manager.py**
   - No need to remember commands
   - Visual feedback on progress
   - Guided workflow

3. **Database is optional for testing**
   - Use `--skip-db` flag (option 1 in scraper menu)
   - Test extraction without MySQL
   - Perfect for development

---

## 🎉 You're All Set!

Just run:
```bash
python3 workflow_manager.py
```

And follow the menu! The tool will guide you through everything.

**Questions? Check WORKFLOW.md for detailed explanations!**
