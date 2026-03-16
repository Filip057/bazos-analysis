# Claude Chat Prompts for Label Validation

## 🎯 Goal: Fast validation of auto-extracted labels

Instead of manually typing year/mileage/fuel/power for 500 offers, you:
1. Export offers with AUTO-EXTRACTED labels
2. Send CSV to Claude chat
3. Claude validates/corrects extraction
4. Import back as training data

---

## 📋 WORKFLOW:

### **STEP 1: Export auto-labeled data**

```bash
python3 scripts/export_for_auto_labeling.py --count 500

# Output: auto_labeled_sample.csv
# Columns: id, url, text, auto_year, auto_mileage, auto_fuel, auto_power, ...
```

---

### **STEP 2: Prepare for Claude validation**

```bash
# Option A: Send FULL CSV to Claude chat
# (Upload auto_labeled_sample.csv as attachment)

# Option B: Send first 50 rows as text
head -n 51 auto_labeled_sample.csv > sample_50.csv

# Option C: Convert to markdown table (for small samples)
# (Better for Claude chat - easier to read)
```

---

### **STEP 3: Claude Chat Validation Prompt**

**Upload `auto_labeled_sample.csv` to Claude chat, then use this prompt:**

```
Validuj tento CSV soubor s auto-extracted car data z Bazos.cz nabídek.

KONTEXT:
- Auto-extraction použila improved regex patterns
- Potřebuji zkontrolovat jestli extraction je SPRÁVNÁ
- Pro každý řádek: zkontroluj jestli auto_year, auto_mileage, auto_fuel, auto_power odpovídají textu

CSV SLOUPCE:
- id: ID nabídky
- text: Headline + description (truncated)
- auto_year: Auto-extracted rok výroby
- auto_mileage: Auto-extracted nájezd km
- auto_fuel: Auto-extracted palivo
- auto_power: Auto-extracted výkon kW
- verified_*: Prázdné - ZDE doplň správné hodnoty pokud auto_* je špatně
- correct: Prázdné - ZDE doplň: 1=correct, 0=incorrect

ÚKOL:
Pro každý řádek (ID 1-50):

1. **Přečti text** a najdi správné hodnoty:
   - Rok výroby (YYYY)
   - Nájezd (číslo km)
   - Palivo (benzín/diesel/lpg/elektro/hybrid)
   - Výkon (číslo kW)

2. **Porovnej s auto_* sloupci:**
   - Pokud auto_year SPRÁVNĚ → nech verified_year prázdné, correct=1
   - Pokud auto_year ŠPATNĚ → doplň správnou hodnotu do verified_year, correct=0
   - Stejně pro mileage, fuel, power

3. **OUTPUT:**
   Vrať CSV formát s doplněnými sloupci:
   ```csv
   id,verified_year,verified_mileage,verified_fuel,verified_power,correct
   1,,,,,1
   2,2015,,,benzín,0
   3,,,,,1
   ...
   ```

PRAVIDLA:
- Pokud v textu NENÍ year/mileage/fuel/power → nech auto_* prázdné, correct=1
- Ignoruj STK datumy, servisní záznamy (ne rok výroby!)
- Rok výroby: 1990-2026
- Nájezd: rozumné hodnoty (1000-999999 km)
- Fuel: normalizuj na: benzín|diesel|lpg|elektro|hybrid
- Power: jen kW (ne HP/PS)

FORMÁT VÝSTUPU:
Vrať jen CSV s ID + opravy (kde auto_* bylo špatně).
Pro správné rows (correct=1) nemusíš vracet.

PŘÍKLAD:
```csv
id,verified_year,verified_mileage,verified_fuel,verified_power,correct,notes
2,2015,,,benzín,0,Auto extracted 2016 but text says "r.v. 2015"
5,,150000,,,0,Auto extracted 15000 but text says "150 tis km"
7,,,diesel,,0,Auto extracted benzín but text says "naftový motor"
```

Začni s prvními 50 řádky.
```

---

### **STEP 4: Import Claude's corrections**

```bash
# Claude returns CSV with corrections
# Save it as: claude_corrections.csv

# Merge corrections back into original CSV
python3 scripts/merge_corrections.py \
    --original auto_labeled_sample.csv \
    --corrections claude_corrections.csv \
    --output auto_labeled_sample_verified.csv

# Import as training data
python3 scripts/import_verified_labels.py \
    --input auto_labeled_sample_verified.csv
```

---

## 🎯 ALTERNATIVE: Row-by-row validation

For smaller batches (10-20 rows), use this format:

```
Zkontroluj tyto auto-extracted labels:

ROW 1:
Text: "Mazda 6 2.0i 114KW,2011,KŮŽE,VÝHŘEV, najeto 193.500km"
Auto-extracted:
  - year: 2011
  - mileage: 193500
  - fuel: benzín
  - power: 114

Je extraction SPRÁVNÁ? (yes/no/partial)
Pokud ne, co je špatně?

ROW 2:
Text: "Mazda CX-5 2.0 benzin r.v.01/2022 NAVI,LED najeto 72.300 km"
Auto-extracted:
  - year: 2022
  - mileage: 72300
  - fuel: benzín
  - power: None

Je extraction SPRÁVNÁ?

...
```

---

## 📊 EXPECTED RESULTS:

**Auto-extraction accuracy (with IMPROVED patterns):**
- Year: ~90-95% (high confidence patterns work well)
- Mileage: ~85-90% (some edge cases remain)
- Fuel: ~95-98% (simple patterns)
- Power: ~80-85% (confusion with model numbers)

**Manual verification needed:**
- ~10-15% of samples (50-75 out of 500)
- Much faster than typing all 500 manually!

---

## 💡 TIPS:

1. **Start with small batch (50 rows)**
   - Test Claude's validation quality
   - Adjust prompt if needed
   - Then do full 500

2. **Use Claude Projects for continuity**
   - Upload CSV as project knowledge
   - Run validation in multiple sessions
   - Claude remembers context

3. **Split into chunks**
   - 500 rows is LOT for one prompt
   - Better: 50 rows × 10 sessions
   - Or: 100 rows × 5 sessions

4. **Focus on ERRORS, not everything**
   - Only return rows where auto_* is WRONG
   - Saves tokens, faster processing

---

## 🚀 NEXT STEP AFTER VALIDATION:

```bash
# 1. Import verified labels
python3 scripts/import_verified_labels.py

# Output: training_data_verified.json
# Contains: 500 high-quality training examples

# 2. Re-train ML model
python3 ml/train_model.py --input training_data_verified.json

# 3. Compare old vs new model
python3 ml/compare_models.py \
    --old ml/models/spacy_model \
    --new ml/models/spacy_model_v2 \
    --test-data test_set.json

# 4. If new model is better → deploy!
```

---

**🎯 THIS WORKFLOW IS 10× FASTER THAN MANUAL LABELING!** ⚡
