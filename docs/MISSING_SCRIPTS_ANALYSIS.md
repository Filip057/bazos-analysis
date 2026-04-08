# Missing Scripts in Workflow Manager

## 📊 Status Summary

### ✅ Already in Workflow Manager (Options 1-12):
1. ✅ Scrape Data (scraper/data_scrap.py)
2. ✅ Clean Duplicates (ml/deduplicate_*.py)
3. ✅ Review Disagreements (ml/review_disagreements.py)
4. ✅ Train Initial Model (ml/train_ml_model.py)
5. ✅ Retrain Model (ml/retrain_model.py)
6. ✅ Evaluate Model Quality (ml/train_ml_model.py --evaluate-only)
7. ✅ Check Training Data (ml/train_ml_model.py --analyze-only)
8. ✅ View Statistics (extraction_stats.json)
9. ✅ Normalize Data (ml/normalize_for_db.py)
10. ✅ Reset Workflow
11. ✅ View Documentation
12. ✅ Exit

---

## ❌ Missing from Workflow Manager:

### 🔴 HIGH PRIORITY - Should be added:

#### 1. **labeling/label_data.py** - Manual Labeling Tool
**Purpose:** Create initial training data from scratch
**Use case:** New machine, no labeled data yet
**Command:** `python3 -m labeling.label_data --input filtered_training_skoda.json --output training_data_labeled.json`

**Why important:**
- Essential for bootstrapping ML model on new machine
- Interactive tool to label MILEAGE, YEAR, POWER, FUEL
- Creates the training_data_labeled.json file needed for training

**Should add as:** Option 1 (before current "Scrape Data")

---

#### 2. **labeling/validate_labels.py** - Validate Labeled Data
**Purpose:** Check for labeling errors
**Use case:** After manual labeling, before training
**Command:** `python3 -m labeling.validate_labels training_data_labeled.json`

**Why important:**
- Checks for overlapping entities
- Checks for misaligned entities (text not found)
- Prevents training on bad data

**Should add as:** Option 2 (after "Label New Data")

---

### 🟡 MEDIUM PRIORITY - Nice to have:

#### 3. **utils/analyze_labeled_data.py** - Analyze Data Quality
**Purpose:** Detailed analysis of labeled data
**Use case:** Check data distribution and balance
**Command:** `python3 -m utils.analyze_labeled_data training_data_labeled.json`

**Status:**
- Partially covered by Option 7 (Check Training Data)
- But this gives more detailed output
- **Decision:** Keep current one, not critical to add

---

#### 4. **labeling/scrape_for_training.py** - Scrape Specific Data for Training
**Purpose:** Scrape specific car brands/models for training
**Use case:** Need more examples of specific patterns
**Command:** `python3 -m labeling.scrape_for_training`

**Status:**
- Already covered by Option 1 (Scrape Data)
- This is more specialized
- **Decision:** Not critical, advanced users can run manually

---

### 🟢 LOW PRIORITY - Advanced/Internal tools:

#### 5. **check_training_quality.py** - Quality checker
**Purpose:** Check training data quality
**Status:** Covered by validate_labels.py and train_ml_model.py --analyze-only

#### 6. **utils/check_label_consistency.py** - Check consistency
**Purpose:** Check label consistency across examples
**Status:** Similar to validate_labels.py

#### 7. **labeling/export_descriptions.py** - Export descriptions
**Purpose:** Export descriptions from database for labeling
**Status:** Advanced use case, not needed for normal workflow

---

## 🎯 Recommendation

### Add these 2 options to workflow_manager.py:

```
📝 DATA LABELING (Create Training Data):
  1. Label New Data            - Manual labeling tool
  2. Validate Labels           - Check for labeling errors

📊 DATA COLLECTION:
  3. Scrape Data               - Get car listings with RAW extraction
  4. Clean Duplicates          - Remove duplicate review entries
  5. Review Disagreements      - Label RAW data for training

🎓 MODEL TRAINING & QUALITY:
  6. Train Initial Model       - First time training (from scratch)
  7. Retrain Model             - Retrain with accumulated data
  8. Evaluate Model Quality    - Test model accuracy (F1 score)
  9. Check Training Data       - Analyze data quality & distribution

🔧 TOOLS & UTILITIES:
 10. View Statistics           - Check extraction accuracy
 11. Normalize Data            - Preview normalization (DB format)
 12. Reset Workflow            - Delete all generated files
 13. View Documentation        - Open WORKFLOW.md
 14. Exit
```

---

## 🔧 Implementation

### Functions to add:

```python
def label_new_data(self):
    """Option 1: Manual labeling tool"""
    self.print_header()
    print("📝 LABEL NEW DATA")
    print("-" * 70)
    print()
    print("Create training data by manually labeling car descriptions.")
    print()
    print("You'll need:")
    print("  - Input file: filtered_training_*.json (from scraping)")
    print("  - Output file: training_data_labeled.json")
    print()

    # Check if input files exist
    input_files = list(self.project_root.glob('filtered_training_*.json'))

    if not input_files:
        print("❌ No input files found!")
        print()
        print("First scrape some data for training using:")
        print("  python3 -m labeling.scrape_for_training")
        input("\nPress Enter to continue...")
        return

    print("Available input files:")
    for i, f in enumerate(input_files, 1):
        print(f"  {i}. {f.name}")

    print()
    file_choice = input(f"Choose file (1-{len(input_files)}) or press Enter for default: ").strip()

    if file_choice and file_choice.isdigit():
        idx = int(file_choice) - 1
        if 0 <= idx < len(input_files):
            input_file = input_files[idx]
        else:
            input_file = input_files[0]
    else:
        input_file = input_files[0]

    output_file = input("Output file (default: training_data_labeled.json): ").strip()
    output_file = output_file if output_file else "training_data_labeled.json"

    limit = input("Number of examples to label (default: 50): ").strip()
    limit = limit if limit else "50"

    self.run_command(
        f"python3 -m labeling.label_data --input {input_file} --output {output_file} --limit {limit}",
        "Starting manual labeling"
    )

    input("\nPress Enter to continue...")

def validate_labels(self):
    """Option 2: Validate labeled data"""
    self.print_header()
    print("✅ VALIDATE LABELS")
    print("-" * 70)
    print()

    training_file = self.project_root / 'training_data_labeled.json'
    if not training_file.exists():
        print("❌ training_data_labeled.json not found!")
        print()
        print("Label some data first using 'Label New Data'")
        input("\nPress Enter to continue...")
        return

    print("This will check your labeled data for:")
    print("  - Overlapping entities")
    print("  - Misaligned entities (text not found)")
    print("  - Empty entities")
    print("  - Invalid ranges")
    print()

    self.run_command(
        "python3 -m labeling.validate_labels training_data_labeled.json",
        "Validating labeled data"
    )

    input("\nPress Enter to continue...")
```

---

## 📋 Updated Menu Numbers

After adding options 1-2, all existing options shift by +2:

- Old Option 1 (Scrape) → New Option 3
- Old Option 2 (Clean) → New Option 4
- Old Option 3 (Review) → New Option 5
- ...
- Old Option 12 (Exit) → New Option 14

Need to update the `run()` function accordingly.

---

## 🎯 User Impact

### For NEW machine setup:
**Before:** Had to manually run `python3 -m labeling.label_data ...`
**After:** Just choose Option 1 from menu

### Workflow becomes:
1. ✅ Label New Data (Option 1) - Create 50-200 examples
2. ✅ Validate Labels (Option 2) - Check for errors
3. ✅ Train Initial Model (Option 6) - Train from labeled data
4. ✅ Scrape Data (Option 3) - Start collecting
5. ✅ Review Disagreements (Option 5) - Label more
6. ✅ Retrain Model (Option 7) - Improve model

**Complete end-to-end workflow in one menu!**
