# ⚠️ Fix spaCy [W030] Warning - Misaligned Entities

## **PROBLÉM:**

```
UserWarning: [W030] Some entities could not be aligned in the text.
Use `spacy.training.offsets_to_biluo_tags(nlp.make_doc(text), entities)`
to check the alignment. Misaligned entities ('-') will be ignored during training.
```

**CO TO ZNAMENÁ:**
- Některé entity annotations mají **ŠPATNÉ POZICE** (start/end offsets)
- spaCy nemůže najít text na těch pozicích
- Tyto entity budou **IGNOROVÁNY** během trainingu! ❌
- **ZTRÁTA TRÉNOVACÍCH DAT!**

---

## **🔍 PŘÍKLAD PROBLÉMU:**

### **Správně:**
```python
text = "Škoda Fabia 2015 benzín 150000km"
entities = [
    [12, 16, "YEAR"],      # "2015"
    [17, 23, "FUEL"],      # "benzín"
    [24, 30, "MILEAGE"]    # "150000"
]

# spaCy check:
text[12:16] = "2015" ✅
text[17:23] = "benzín" ✅
text[24:30] = "150000" ✅
```

### **Špatně (misaligned):**
```python
text = "Škoda Fabia 2015 benzín 150000km"
entities = [
    [13, 17, "YEAR"],      # "015 " ❌ WRONG!
    [18, 24, "FUEL"],      # "enzín" ❌ WRONG!
    [25, 32, "MILEAGE"]    # "50000k" ❌ WRONG!
]

# spaCy check:
text[13:17] = "015 " ❌ Expected "2015" → IGNORED!
text[18:24] = "enzín" ❌ Expected "benzín" → IGNORED!
text[25:32] = "50000k" ❌ Expected "150000" → IGNORED!

RESULT: Model se neučí z těchto entit!
```

---

## **❌ DŮSLEDKY:**

```
1. ❌ Misaligned entities jsou IGNOROVÁNY během trainingu
   → Model se z nich NEUČÍ!

2. ❌ Ztráta trénovacích dat
   → Z 3354 samples můžeš reálně trénovat jen na ~2500-3000

3. ❌ Nižší accuracy
   → Model má méně examples na učení

4. ❌ Unbalanced training
   → POWER má jen 441 entities
   → Když 100 je misaligned → jen 341 zbývá!
   → Model bude ještě slabší na POWER extraction

5. ❌ Klamavé metriky
   → Myslíš že máš 3354 samples
   → Ale reálně trénuješ jen na 2800
```

---

## **🎯 PŘÍČINY:**

### **1. Whitespace Issues** (nejčastější!)
```python
# Extra space na začátku/konci
text = "Škoda Fabia  2015"  # double space!
entity = [13, 17, "YEAR"]    # počítá s jednou mezerou
# text[13:17] = "2015" ale pozice je 14, ne 13!

# Tabs místo spaces
text = "Škoda\tFabia\t2015"  # \t = tab
entity = [12, 16, "YEAR"]     # počítá s mezerou
# \t má jiný offset než space!

# Newlines
text = "Škoda Fabia\n2015"
entity = [12, 16, "YEAR"]
# \n má offset 1, ne 0!
```

### **2. Unicode Issues**
```python
# Czech chars (š, č, ř, ž, ý, á, ...) v Pythonu 3
text = "Škoda"
len(text) = 5  # správně (Python 3 = UTF-8)

# Ale někdy:
text_bytes = text.encode('utf-8')  # b'\xc5\xa0koda'
len(text_bytes) = 6  # Š = 2 bytes!

# Pokud offset calculation použil bytes místo chars:
entity = [0, 6, "BRAND"]  # WRONG! Should be [0, 5]
```

### **3. Auto-Labeling Bugs**
```python
# Claude/script spočítal offset špatně
# Example: Claude použil .find() ale text měl duplicity

text = "Škoda Fabia 2015, původně 2015"
# Claude našel "2015" pomocí text.find("2015")
# Vrátí první výskyt (index 12)
# Ale myslel druhý výskyt (index 27)!

entity = [12, 16, "YEAR"]  # první výskyt
# Ale labeloval druhý výskyt! → misalignment
```

### **4. Text Normalization**
```python
# Text se změnil po uložení/načtení
original = "Škoda  Fabia"  # double space
saved = "Škoda Fabia"       # single space (normalizováno)

entity = [7, 12, "MODEL"]   # offset pro "Fabia" s double space
# Ale text má single space → offset je 6, ne 7!
```

### **5. Copy-Paste Errors**
```python
# Manual labeling: copy-paste z jiného editoru
# → různé line endings (\n vs \r\n)
# → různé encoding (UTF-8 vs Windows-1250)
# → různé whitespace handling
```

---

## **✅ ŘEŠENÍ:**

### **STEP 1: Validate Training Data**

```bash
# Check for misaligned entities
python3 scripts/validate_training_data.py \
    --input temp_combined_training.json \
    --show-errors

# Output:
📊 Overall Statistics:
  Total examples:      3354
  Total entities:      8552
  Valid entities:      7823 (91.5%)  ✅
  Invalid entities:    729 (8.5%)    ❌

⚠️  DATA LOSS: 8.5% of entities will be IGNORED during training!
```

**INTERPRETACE:**
- **< 5% invalid**: ✅ Acceptable, můžeš trénovat
- **5-10% invalid**: ⚠️ Warning, měl bys opravit před trainingem
- **> 10% invalid**: ❌ CRITICAL, training quality severely affected!

---

### **STEP 2: Auto-Fix Issues**

```bash
# Try to automatically fix misaligned entities
python3 scripts/validate_training_data.py \
    --input temp_combined_training.json \
    --output training_data_fixed.json \
    --fix \
    --show-errors

# Output:
  Fixed entities:      612 (84% of invalid)   ✅
  Removed entities:    117 (16% of invalid)   ⚠️

💾 Saving fixed data to training_data_fixed.json...
  ✅ Saved 3354 examples
  ✅ Fixed 612 entities
  ⚠️  Removed 117 unfixable entities
```

**FIXING STRATEGIES:**

1. **Whitespace Trimming**
   ```python
   # Remove leading/trailing spaces
   entity_text = text[start:end].strip()
   ```

2. **Pattern Search Nearby**
   ```python
   # Search for pattern ±10 chars around position
   # YEAR: \b(19\d{2}|20[0-2]\d)\b
   # MILEAGE: \b\d{4,6}\s*km\b
   # POWER: \b\d{2,3}\s*(?:kW|PS)\b
   # FUEL: \b(?:benzín|diesel|lpg)\b
   ```

3. **Entity Type Heuristics**
   ```python
   # If entity_type == "YEAR", look for 4-digit year
   # If entity_type == "MILEAGE", look for km pattern
   ```

---

### **STEP 3: Train on Fixed Data**

```bash
# Train model on FIXED data
python3 -m ml.train_ml_model \
    --data training_data_fixed.json \
    --iterations 30 \
    --output ml/models/v1_fixed

# Should see fewer W030 warnings!
```

---

## **🔍 MANUAL INSPECTION (if auto-fix fails)**

### **Option 1: Use spaCy's Built-in Checker**

```python
import spacy
from spacy.training import offsets_to_biluo_tags

nlp = spacy.blank("cs")

text = "Škoda Fabia 2015 benzín"
entities = [[12, 16, "YEAR"], [17, 23, "FUEL"]]

doc = nlp.make_doc(text)
tags = offsets_to_biluo_tags(doc, entities)

print(tags)
# Output: ['O', 'O', 'B-YEAR', 'L-YEAR', 'B-FUEL', 'L-FUEL']
#          ↑ OK = B/I/L/U tags
#          ↓ ERROR = '-' tags

# If you see '-' anywhere → MISALIGNED!
```

### **Option 2: Visual Inspection Script**

```python
# scripts/inspect_misaligned.py
import json

data = json.load(open('training_data.json'))

for idx, item in enumerate(data):
    text, annotations = item
    entities = annotations['entities']

    for entity in entities:
        start, end, label = entity
        extracted = text[start:end]

        # Manual check
        print(f"\n[{idx}] {label}")
        print(f"  Position: [{start}, {end}]")
        print(f"  Extracted: '{extracted}'")
        print(f"  Context: ...{text[max(0,start-20):end+20]}...")

        # Ask user
        response = input(f"  Correct? (y/n/s=skip): ")
        if response == 'n':
            print("  → MISALIGNED! Mark for fixing")
```

---

## **🛠️ PREVENTION (Future Labeling)**

### **1. Use Validation During Labeling**

```python
# When creating training data, validate immediately
def add_entity(text, start, end, label):
    # Validate before adding
    extracted = text[start:end]

    # Check: not empty
    if not extracted.strip():
        raise ValueError(f"Empty entity at [{start}, {end}]")

    # Check: matches expected pattern
    if label == "YEAR":
        if not re.match(r'^\d{4}$', extracted):
            print(f"⚠️  YEAR entity '{extracted}' doesn't match pattern!")

    return [start, end, label]
```

### **2. Use Claude with Character Positions**

When asking Claude to label, use **character highlighting**:

```
Text: "Škoda Fabia 2015 benzín"
            ^--- YEAR (position 12-16)
                 ^--- FUEL (position 17-23)

Instead of just:
Text: "Škoda Fabia 2015 benzín"
Entities: YEAR=2015, FUEL=benzín
```

### **3. Normalize Text Before Labeling**

```python
def normalize_text(text):
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove leading/trailing space
    text = text.strip()

    # Normalize unicode (NFC)
    import unicodedata
    text = unicodedata.normalize('NFC', text)

    return text

# Always normalize before labeling!
text = normalize_text(raw_text)
```

---

## **📊 IMPACT ANALYSIS:**

### **Example: Your 3354 samples**

```
Scenario A: 5% misaligned (423 entities)
  Valid entities:    8129 (95%)
  Training quality:  ✅ Good (95%+)
  Model accuracy:    ~93-95% (as expected)

Scenario B: 10% misaligned (855 entities)
  Valid entities:    7697 (90%)
  Training quality:  ⚠️ OK but degraded
  Model accuracy:    ~88-92% (3-5% loss!)

Scenario C: 20% misaligned (1710 entities)
  Valid entities:    6842 (80%)
  Training quality:  ❌ Poor
  Model accuracy:    ~80-85% (10-15% loss!)
  POWER entities:    441 → 353 (80%)
  → POWER accuracy drops to 40-50%!
```

**BOTTOM LINE:**
- **< 5% misaligned**: ✅ Train as-is
- **5-10% misaligned**: ⚠️ Fix before training
- **> 10% misaligned**: ❌ MUST fix! Training will fail

---

## **🚀 QUICK START:**

```bash
# 1. Validate your training data
python3 scripts/validate_training_data.py \
    --input temp_combined_training.json \
    --show-errors

# 2. If > 5% invalid, auto-fix
python3 scripts/validate_training_data.py \
    --input temp_combined_training.json \
    --output training_data_fixed.json \
    --fix

# 3. Train on fixed data
python3 -m ml.train_ml_model \
    --data training_data_fixed.json \
    --iterations 30

# 4. Check for W030 warnings
# Should see much fewer (or zero)!
```

---

## **📚 REFERENCES:**

- spaCy Docs: https://spacy.io/usage/training#entity-offsets
- spaCy W030 Warning: https://spacy.io/api/warnings#w030
- offsets_to_biluo_tags: https://spacy.io/api/training#offsets_to_biluo_tags

---

## **💡 KEY TAKEAWAYS:**

```
✅ W030 warning = MISALIGNED entities = DATA LOSS
✅ Misaligned entities are IGNORED during training
✅ Common causes: whitespace, unicode, auto-labeling bugs
✅ Fix with: validate → auto-fix → train on fixed data
✅ Target: < 5% misaligned for good training quality
✅ Prevent: normalize text, validate during labeling

⚠️  DON'T IGNORE W030! It's not just a warning!
⚠️  Fix before training or lose 5-20% of your data!
```
