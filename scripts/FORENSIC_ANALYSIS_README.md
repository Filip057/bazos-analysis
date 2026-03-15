# Forensic Extraction Analysis Workflow

This workflow helps identify **exactly** what extraction patterns are missing by analyzing real failed examples.

## 🎯 Goal

Instead of blindly re-extracting all 1049 offers, we:
1. Export 100 incomplete offers
2. Scrape FRESH data from these URLs
3. Run improved extraction
4. **Analyze GAPS** - what's in the text but extraction missed
5. Identify missing patterns
6. Fix patterns
7. Repeat until 85%+ completeness

---

## 📋 Workflow

### **STEP 1: Export Incomplete Offers**

```bash
python3 scripts/export_incomplete_offers.py --limit 100

# Output: incomplete_offers.csv
# Columns: id, url, current_year, current_mileage, current_fuel, current_power
```

**What it does:**
- Queries DB for offers where `year_manufacture IS NULL OR mileage IS NULL`
- Exports 100 examples to CSV

---

### **STEP 2: Scrape + Extract Fresh Data**

```bash
python3 scripts/scrape_and_analyze_incomplete.py incomplete_offers.csv

# Output: analysis_results.csv
# Columns: id, url, scraped_title, scraped_description,
#          extracted_year, extracted_mileage, extracted_fuel, extracted_power,
#          current_year, current_mileage, current_fuel, current_power,
#          extraction_improved (YES/NO)
```

**What it does:**
- Scrapes FRESH title + description from each URL
- Runs **IMPROVED** extraction patterns
- Compares extracted vs. current DB values
- Shows which offers improved (extraction_improved column)

**Expected output:**
```
ANALYSIS RESULTS
======================================================================
  Total processed:     100
  Successfully scraped: 98
  Failed scrapes:      2

  IMPROVEMENTS:
    Year improved:     35  (extraction found NEW years!)
    Mileage improved:  28  (extraction found NEW mileage!)
    Fuel improved:     15
    Power improved:    12
======================================================================
```

---

### **STEP 3: Analyze Gaps (What Extraction Missed)**

```bash
python3 scripts/analyze_extraction_gaps.py analysis_results.csv

# Output: gap_analysis.csv
# Columns: id, url, gap_type,
#          missed_year, missed_year_context,
#          missed_mileage, missed_mileage_context,
#          missed_fuel, missed_fuel_context,
#          extracted_year, extracted_mileage, extracted_fuel
```

**What it does:**
- Uses **AGGRESSIVE** regex to find ALL possible years/mileage/fuel in text
- Compares with what extraction found
- Reports what extraction **MISSED** (gap)

**Example output (gap_analysis.csv):**
```csv
id,url,gap_type,missed_year,missed_year_context,missed_mileage,missed_mileage_context,...
113,https://auto.bazos.cz/...,year+mileage,2013,"...první majitel od roku 2013...",142000,"...skutečný nájezd 142000 km...",...
```

**Expected output:**
```
GAP ANALYSIS RESULTS
======================================================================
  Total analyzed:        100
  Year gaps found:       15  (text HAS year, but extraction MISSED!)
  Mileage gaps found:    10  (text HAS mileage, but extraction MISSED!)
  Fuel gaps found:       5
  No gaps (truly empty): 70  (these offers really have no data)
======================================================================
```

---

### **STEP 4: Manual Review + Pattern Identification**

```bash
# Open gap_analysis.csv in Excel/LibreOffice
# Look at "missed_*_context" columns
# Identify missing patterns

# Examples:
#   missed_year_context: "první majitel od roku 2013"
#   → MISSING PATTERN: "od roku YYYY"
#
#   missed_mileage_context: "reálný nájezd je 142000 km"
#   → MISSING PATTERN: "reálný nájezd"
```

---

### **STEP 5: Add Missing Patterns**

Edit `ml/context_aware_patterns.py`:

```python
# Add new patterns you found in gap analysis
YEAR_HIGH_CONFIDENCE = [
    ...existing patterns...,
    re.compile(r'(?:od\s+roku)\s*(\d{4})', re.IGNORECASE),  # NEW!
]

MILEAGE_HIGH_CONFIDENCE = [
    ...existing patterns...,
    re.compile(r'(?:reálný\s+nájezd)\s+(?:je)?\s*((\d{5,6})\s?km)', re.IGNORECASE),  # NEW!
]
```

---

### **STEP 6: Test New Patterns**

```bash
# Re-run STEP 2 with same CSV to test improvements
python3 scripts/scrape_and_analyze_incomplete.py incomplete_offers.csv --output analysis_results_v2.csv

# Compare results:
#   analysis_results.csv     (before new patterns)
#   analysis_results_v2.csv  (after new patterns)

# Did "extraction_improved" increase? ✅
```

---

### **STEP 7: Iterate Until 85%+ Success**

Repeat STEP 3-6 until:
- **Year gaps:** < 5 (from 100 offers)
- **Mileage gaps:** < 5
- **Fuel gaps:** < 10

**Then:** Run full re-extraction on all 1049 offers!

---

## 🎯 Benefits of This Approach

| Traditional Re-extraction | Forensic Analysis |
|--------------------------|-------------------|
| ❌ Blind re-extraction of 1049 offers | ✅ Analyze 100 failed examples first |
| ❌ Don't know what's missing | ✅ See EXACTLY what patterns are missing |
| ❌ Iterate slowly (re-extract all each time) | ✅ Fast iteration (test on 100 only) |
| ❌ Hard to debug failures | ✅ CSV shows exact context where it failed |

---

## 📊 Expected Results

### Before Forensic Analysis:
```
Completeness: 55-62% (year/mileage)
Unknown gaps: ??? (don't know what's missing)
```

### After 2-3 Iterations:
```
Completeness on 100 test samples: 85-90%
Known gaps: < 10% (and we know WHY they fail)
Confidence: HIGH (patterns tested on real examples)
```

### After Full Re-extraction:
```
Completeness on all 1049 offers: 80-85%
Missing data: Truly incomplete offers (no data in text)
```

---

## 🚀 Quick Start

```bash
# Full workflow
python3 scripts/export_incomplete_offers.py --limit 100
python3 scripts/scrape_and_analyze_incomplete.py incomplete_offers.csv
python3 scripts/analyze_extraction_gaps.py analysis_results.csv

# Review gap_analysis.csv
# → Identify missing patterns
# → Add to ml/context_aware_patterns.py

# Test improvements
python3 scripts/scrape_and_analyze_incomplete.py incomplete_offers.csv --output analysis_v2.csv

# Repeat until gaps < 10%
```

---

## 📁 Output Files

```
incomplete_offers.csv      # 100 incomplete offers (from DB)
analysis_results.csv       # Scraped + extracted data
gap_analysis.csv          # What extraction MISSED (gaps)
```

**Send me `gap_analysis.csv` and I'll help identify missing patterns!** 🔍
