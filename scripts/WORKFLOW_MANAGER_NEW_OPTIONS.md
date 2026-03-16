# 🛠️ Workflow Manager - NEW Training Data Tools

## **ADDED: Options 18-20**

---

## **📋 MENU UPDATE:**

```
🛠️  TRAINING DATA TOOLS:
 18. Fix Misaligned Entities   - Fix [W030] warnings (auto-fix 80-90%)
 19. Merge Training Data       - Merge old + new data (deduplication)
 20. Export for Claude         - Export offers for Claude labeling
```

Plus **updated Option 12** with quick alignment check!

---

## **✅ OPTION 18: Fix Misaligned Entities**

**Purpose:** Fix [W030] warnings during training

**What it does:**
- Validates all entity positions
- Auto-fixes misaligned entities (80-90% success rate)
- Removes unfixable entities
- Creates clean training data

**Fixing strategies:**
1. Whitespace trimming (remove extra spaces)
2. Pattern search nearby (±10 chars)
3. Entity-type heuristics (YEAR/MILEAGE/POWER/FUEL patterns)

**Workflow:**
```
1. Choose training file (or use temp_combined_training.json)
2. Choose: Analyze only OR Analyze + Fix
3. If fixing → creates training_data_fixed.json
4. Use fixed data for training!
```

**Example:**
```
Input:  temp_combined_training.json (3354 samples, 8552 entities)
Output: training_data_fixed.json (3354 samples, 8435 entities)

Result:
  ✅ Fixed: 612 entities (80-90% recovery)
  ⚠️  Removed: 117 unfixable entities (10-20%)

Training loss:
  Before fix: 8.5% data loss (729 misaligned)
  After fix:  1.4% data loss (117 unfixable)
```

---

## **✅ OPTION 19: Merge Training Data**

**Purpose:** Merge old + new training data (incremental approach!)

**What it does:**
- Combines multiple training data sources
- Deduplicates (avoids training on same offer twice)
- Normalizes different formats → spaCy format
- Shows statistics & analysis

**Use case:**
```
You have:
  - training_data_labeled.json (500 samples)
  - auto_training_data.json (2000 samples)

Claude labeled:
  - training_data_new.json (300 samples)

Merge:
  → training_data_merged.json (2800 samples after dedup)
```

**Workflow:**
```
1. Enter EXISTING files (space-separated)
   Example: training_data_labeled.json auto_training_data.json

2. Enter NEW file (to be added)
   Example: training_data_new.json

3. Choose output filename
   Default: training_data_merged.json

4. Script merges, deduplicates, analyzes!
```

**Deduplication:**
- Uses first 100 chars of text as key
- Keeps first occurrence
- Removes duplicates
- Reports how many duplicates found

**Example output:**
```
======================================================================
MERGE TRAINING DATA
======================================================================

📥 Loading EXISTING training data...
  ✅ training_data_labeled.json: 500 samples
  ✅ auto_training_data.json: 2000 samples

  Total existing: 2500 samples

📥 Loading NEW training data...
  ✅ training_data_new.json: 300 samples

🔍 Deduplicating...
  Before: 2800 samples
  Removed 150 duplicates
  After:  2650 samples

📊 Analyzing combined data...
  Total samples:       2650
  With entities:       2580 (97.4%)
  Empty (no entities): 70 (2.6%)

  Entity counts:
    YEAR:     2450 (0.9 per example)
    FUEL:     2380 (0.9 per example)
    MILEAGE:  1850 (0.7 per example)
    POWER:    520 (0.2 per example)

💾 Writing to training_data_merged.json...

======================================================================
MERGE COMPLETE
======================================================================
  Existing samples:  2500
  New samples:       300
  Combined (dedup):  2650

  Output file:       training_data_merged.json
======================================================================
```

---

## **✅ OPTION 20: Export for Claude Labeling**

**Purpose:** Export car offers for Claude to label

**What it does:**
- Exports unlabeled offers from scraped data
- Creates JSON format for Claude chat
- Provides workflow for Claude labeling

**Workflow:**
```
1. Export offers (this tool)
   → creates offers_for_labeling.json

2. Upload to Claude chat

3. Use prompt from scripts/CLAUDE_LABELING_GUIDE.md

4. Claude labels → download training_data_new.json

5. Merge with existing data (Option 19)

6. Train model!
```

**Options:**
- Export from scraped data (if available)
- Scrape fresh offers (specify brand)

**Example:**
```
How many offers to export? 300
Output filename: offers_for_labeling.json

Options:
  1. Export from scraped data
  2. Scrape fresh offers

Choose: 1

✅ Exported 300 offers to offers_for_labeling.json

Next steps:
  1. Upload offers_for_labeling.json to Claude chat
  2. Use prompt from scripts/CLAUDE_LABELING_GUIDE.md
  3. Download training_data_new.json from Claude
  4. Run Option 19 (Merge Training Data)
```

---

## **✅ OPTION 12 UPDATE: Check Training Data Quality**

**NEW: Sub-option 3 - Quick check for misaligned entities**

```
Options:
  1. Check original labeled data
  2. Check all training data sources combined
  3. Quick check for misaligned entities  ← NEW!
  4. Back to main menu
```

**What option 3 does:**
- Combines all training data sources
- Runs quick_check_alignment.py
- Shows first 10 misaligned entities
- Reports total % data loss

**Example output:**
```
🔍 Checking 3354 examples for misaligned entities...

❌ Example 42 - YEAR
   Position: [13, 17]
   Extracted: '015 '
   Problem: Wrong offset (should be [12, 16])
   Context: ...Fabia 2015 benzín...

❌ Example 108 - MILEAGE
   Position: [25, 32]
   Extracted: '50000k'
   Problem: Wrong offset
   Context: ...najeto 150000km...

... (8 more examples)

======================================================================
SUMMARY:
  Total entities:      8552
  Misaligned:          729 (8.5%)
  Valid:               7823 (91.5%)
======================================================================

⚠️  WARNING: 8.5% data loss
   Consider fixing: Option 18 (Fix Misaligned Entities)
```

---

## **📊 COMPLETE WORKFLOW EXAMPLE**

### **Scenario: Adding 300 new training samples**

```
STEP 1: Export offers for Claude
  → Run Option 20 (Export for Claude)
  → Export 300 offers
  → Upload to Claude chat

STEP 2: Claude labels
  → Claude creates training_data_new.json (300 samples)
  → Download from Claude

STEP 3: Check for misaligned entities (optional)
  → Run Option 12, sub-option 3 (Quick check)
  → If > 5% misaligned → fix before merging

STEP 4: Fix misaligned entities (if needed)
  → Run Option 18 (Fix Misaligned Entities)
  → Input: training_data_new.json
  → Output: training_data_new_fixed.json

STEP 5: Merge with existing data
  → Run Option 19 (Merge Training Data)
  → Existing: auto_training_data.json manual_review_data.json
  → New: training_data_new_fixed.json
  → Output: training_data_merged.json

STEP 6: Check quality
  → Run Option 12, sub-option 2 (Check all combined)
  → Creates temp_combined_training.json
  → Analyzes entity distribution

STEP 7: Train model
  → Run Option 9 or 10 (Train/Retrain)
  → Use temp_combined_training.json
  → iterations=20 (NOT 100!)
```

---

## **💡 KEY BENEFITS**

```
✅ All tools in ONE PLACE
   - No need to remember script names
   - No need to type long commands
   - Interactive, guided workflow

✅ INCREMENTAL training approach
   - Start with 500 samples
   - Add 300 → merge → 800 total
   - Add 500 → merge → 1300 total
   - Never lose existing work!

✅ AUTO-FIX misaligned entities
   - 80-90% recovery rate
   - Save hours of manual fixing
   - Clean data = better model

✅ DEDUPLICATION
   - Avoid training on duplicates
   - Merge multiple sources safely
   - Track combined entity counts

✅ CLAUDE LABELING workflow
   - Export → Upload → Download → Merge
   - Guided step-by-step
   - Much faster than manual labeling
```

---

## **🎯 RECOMMENDED WORKFLOW**

### **First Time Setup:**
```
1. Run Option 6 (Scrape Data) → get raw extractions
2. Run Option 8 (Review Disagreements) → create training data
3. Run Option 12 (Check Training Data Quality)
4. Run Option 18 (Fix Misaligned) if needed
5. Run Option 9 (Train Initial Model)
```

### **Adding More Data:**
```
1. Run Option 20 (Export for Claude) → 300 samples
2. Claude labels → training_data_new.json
3. Run Option 18 (Fix Misaligned) on new data
4. Run Option 19 (Merge) with existing data
5. Run Option 10 (Retrain Model)
```

### **Quality Check:**
```
1. Run Option 12, sub-option 3 (Quick check misaligned)
2. If > 5% loss → Run Option 18 (Fix)
3. Run Option 12, sub-option 2 (Analyze combined)
4. Check entity distribution (POWER weak? Add more POWER samples!)
```

---

## **📈 EXPECTED RESULTS**

```
Round 1: 500 samples
  → Model v1, 75-85% accuracy

Round 2: +300 samples (merged → 800 total)
  → Model v2, 85-90% accuracy

Round 3: +500 samples (merged → 1300 total)
  → Model v3, 90-93% accuracy

Round 4: +500 samples (merged → 1800 total)
  → Model v4, 93-95% accuracy
  → PRODUCTION READY! 🎉

Beyond 2000 samples:
  → Diminishing returns (<1% gain per 500 samples)
  → Focus on quality, not quantity
```

---

## **🚀 QUICK REFERENCE**

```
Option 12: Check Training Data Quality
  ↓
  Sub-option 3: Quick check misaligned
    ↓
    If > 5% misaligned
      ↓
      Option 18: Fix Misaligned Entities
        ↓
        training_data_fixed.json

Option 20: Export for Claude
  ↓
  Claude labels → training_data_new.json
    ↓
    Option 18: Fix (if needed)
      ↓
      Option 19: Merge with existing
        ↓
        training_data_merged.json
          ↓
          Option 10: Retrain Model
```
