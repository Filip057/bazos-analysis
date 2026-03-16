# 🎯 Claude Labeling Guide - NEJRYCHLEJŠÍ způsob jak vytvořit training data!

## Workflow (3 kroky, 10-15 minut!)

```
1. Export nabídek → JSON
2. Upload do Claude chat → Claude extrahuje entity
3. Download training_data.json → ML training
```

**⏱️ ČAS: ~10-15 minut (vs. 1-2 hodiny manual labeling!)**

---

## STEP 1: Export nabídek

```bash
python3 scripts/export_for_claude_labeling.py --count 500

# Output: offers_for_labeling.json
# [
#   {
#     "id": 1,
#     "url": "https://...",
#     "text": "Mazda 6 2.0i 114KW,2011,KŮŽE,VÝHŘEV, najeto 193.500km..."
#   },
#   ...
# ]
```

---

## STEP 2: Claude Chat - Extract Entities

### 📤 Upload `offers_for_labeling.json` do Claude chat

### 🤖 Použij tento PROMPT:

```
Extrahuj z těchto Bazos.cz nabídek entity pro ML training.

INPUT: JSON array s car offers
OUTPUT: spaCy training format

ENTITY TYPES:
1. YEAR - rok výroby
   - Formát: YYYY (číslo 1990-2026)
   - Ignoruj: STK datumy, servisní záznamy
   - Příklad: "r.v. 2015" → 2015

2. MILEAGE - nájezd v km
   - Formát: číslo (1000-999999)
   - Varianty: "150 tis km", "150000 km", "najeto 150.000"
   - Příklad: "najeto 193.500km" → 193500

3. FUEL - typ paliva
   - Hodnoty: benzín | diesel | lpg | elektro | hybrid
   - Varianty: "nafta" → diesel, "benzin" → benzín
   - Příklad: "2.0 TDi" → diesel

4. POWER - výkon v kW
   - Formát: číslo (20-500)
   - Ignoruj: HP/PS (ne kW!)
   - Příklad: "114KW" → 114

OUTPUT FORMAT (spaCy training):
[
  [
    "Mazda 6 2.0i 114KW,2011,KŮŽE,VÝHŘEV, najeto 193.500km",
    {
      "entities": [
        [15, 18, "POWER"],      # "114"
        [21, 25, "YEAR"],        # "2011"
        [43, 49, "MILEAGE"]      # "193500" (normalized!)
      ]
    }
  ],
  ...
]

DŮLEŽITÉ:
- Entity positions = character offsets v textu
- Normalizuj hodnoty (odstraň mezery, tečky z čísel)
- Pokud entity NENÍ v textu → prázdný entities array []
- Fuel: normalizuj na lowercase (benzín, diesel, lpg, elektro, hybrid)

PRO KAŽDOU NABÍDKU:
1. Najdi year, mileage, fuel, power v textu
2. Zjisti character positions (start, end)
3. Vytvoř entity tuple: [start, end, "TYPE"]

Vrať CELÝ training array (všech 500 nabídek) jako JSON.
```

---

### 🎯 ALTERNATIVNÍ PROMPT (pokud Claude vrací částečný output):

```
Zpracuj všech 500 nabídek z offers_for_labeling.json.

Pro každou nabídku (id 1-500):
- Najdi entity: YEAR, MILEAGE, FUEL, POWER
- Vrať spaCy format: ["text", {"entities": [[start, end, "TYPE"]]}]

TIPS pro rychlejší zpracování:
- Zpracuj po dávkách (100 nabídek najednou)
- Vrať jen JSON array (bez additional text)
- Pokud entity není v textu → entities: []

Začni s nabídkami 1-100.
```

---

## STEP 3: Download & Train

### 💾 Claude vrátí JSON → ulož jako `training_data.json`

```json
[
  [
    "Mazda 6 2.0i 114KW,2011,KŮŽE,VÝHŘEV, najeto 193.500km",
    {
      "entities": [
        [15, 18, "POWER"],
        [21, 25, "YEAR"],
        [43, 49, "MILEAGE"]
      ]
    }
  ],
  ...
]
```

### 🚀 Train ML model

```bash
# Zkontroluj formát
python3 labeling/validate_labels.py training_data.json

# Train spaCy model
python3 ml/train_model.py --input training_data.json --output ml/models/spacy_model_v2

# Test model
python3 ml/test_extractor.py --model ml/models/spacy_model_v2
```

---

## 📊 EXPECTED RESULTS

### Claude extraction quality:
- **Year**: 95-98% accuracy (easy to find)
- **Mileage**: 90-95% accuracy (various formats)
- **Fuel**: 97-99% accuracy (simple patterns)
- **Power**: 85-90% accuracy (confusion with model numbers)

### Time comparison:
```
Manual labeling:    1-2 hours (500 offers)
Claude labeling:    10-15 minutes (500 offers)
SPEED UP:           6-12× FASTER! 🚀
```

---

## 💡 TIPS & TRICKS

### 1. **Start Small (100 offers)**
```bash
# Test workflow s 100 nabídkami první
python3 scripts/export_for_claude_labeling.py --count 100

# Pokud Claude extraction je dobrá → scale to 500+
```

### 2. **Split Large Batches**
Pokud Claude má problém s 500 offers najednou:
```bash
# Export 500 offers
python3 scripts/export_for_claude_labeling.py --count 500

# Manuálně split JSON na 5× 100 offers
# Nebo použij jq:
jq '.[0:100]' offers_for_labeling.json > batch_1.json
jq '.[100:200]' offers_for_labeling.json > batch_2.json
...

# Upload batch by batch do Claude chat
```

### 3. **Verify Sample Before Training**
```bash
# Po Claude extraction, zkontroluj random sample:
python3 -c "
import json
import random
with open('training_data.json') as f:
    data = json.load(f)
# Print 5 random examples
for item in random.sample(data, 5):
    print(item)
"

# Pokud vypadá OK → train model!
```

### 4. **Compare Old vs New Model**
```bash
# Train new model
python3 ml/train_model.py --input training_data.json --output ml/models/v2

# Compare performance
python3 ml/compare_models.py \
    --old ml/models/spacy_model \
    --new ml/models/v2 \
    --test test_set.json
```

---

## 🔄 ITERATIVE IMPROVEMENT

```bash
# Round 1: Train initial model
python3 scripts/export_for_claude_labeling.py --count 200
# → Claude labels → training_data_v1.json
python3 ml/train_model.py --input training_data_v1.json

# Round 2: Find hard examples
# → Export offers where model fails
# → Claude labels → training_data_v2.json
# → Combine v1 + v2 → re-train

# Round 3: Optimize
# → Focus on specific brands/years
# → More training data for edge cases
```

---

## 🎯 EXAMPLE CLAUDE CONVERSATION

**You:**
```
Hi! Potřebuji extrahovat entity z 500 Bazos.cz car nabídek.

Upload: offers_for_labeling.json

Entity types:
- YEAR: rok výroby (YYYY)
- MILEAGE: nájezd km
- FUEL: benzín/diesel/lpg/elektro/hybrid
- POWER: výkon kW

Vrať spaCy training formát:
[["text", {"entities": [[start, end, "TYPE"]]}], ...]

Zpracuj všech 500 nabídek.
```

**Claude:**
```
Sure! I'll extract entities from all 500 offers.

Processing...

Here's the spaCy training format:

[
  ["Mazda 6 2.0i 114KW,2011,KŮŽE...", {"entities": [[15,18,"POWER"],[21,25,"YEAR"],...]}],
  ...
]

Completed 500/500 offers.
Summary:
- YEAR found: 487/500 (97%)
- MILEAGE found: 465/500 (93%)
- FUEL found: 491/500 (98%)
- POWER found: 423/500 (85%)
```

**You:**
```
Perfect! Ulož to jako training_data.json
```

---

## ⚠️ TROUBLESHOOTING

### Problem: Claude vrací partial output (jen 50 offers)
**Solution:** Split batch nebo ask Claude to continue:
```
Pokračuj s nabídkami 51-100
```

### Problem: Entity positions jsou špatně
**Solution:** Validate s validation script:
```bash
python3 labeling/validate_labels.py training_data.json
```

### Problem: Claude normalizuje text (změní formát)
**Solution:** Explicit v promptu:
```
IMPORTANT: Neměň text! Použij EXACT text z offers_for_labeling.json
Jen přidej entity positions.
```

### Problem: Fuel není normalized
**Solution:** Add to prompt:
```
Fuel normalization:
- nafta/diesel/tdi/naftový → diesel
- benzin/benzín/benz → benzín
- plyn/lpg → lpg
- elektro/ev/electric → elektro
```

---

## 📈 EXPECTED ML MODEL IMPROVEMENT

**Before (regex only):**
```
Accuracy: ~70-80%
Coverage: ~85%
```

**After (500 Claude-labeled examples):**
```
Accuracy: ~90-95%
Coverage: ~95%
Precision: High
```

**After (1000+ examples + iteration):**
```
Accuracy: ~95-98%
Coverage: ~97%
Production ready! ✅
```

---

## 🚀 READY TO START?

```bash
# 1. Export offers
python3 scripts/export_for_claude_labeling.py --count 500

# 2. Upload to Claude chat (claude.ai)
# 3. Use prompt from this guide
# 4. Download training_data.json
# 5. Train model!

python3 ml/train_model.py --input training_data.json
```

**DONE! 🎉**

---

**Questions? Issues?**
- Check validation: `python3 labeling/validate_labels.py training_data.json`
- Test extraction: `python3 ml/test_extractor.py`
- Compare models: `python3 ml/compare_models.py`
