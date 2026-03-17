# 🤖 GPT Labeling Instructions

## 📋 KROK 1: Připrav Prompt

```bash
# Zobraz GPT prompt v2:
cat gpt_entity_extraction_prompt_v2.md

# Nebo otevři v editoru:
code gpt_entity_extraction_prompt_v2.md  # VS Code
nano gpt_entity_extraction_prompt_v2.md  # Terminal
```

**Zkopíruj celý prompt** od sekce:
```
Extrahuj z těchto Bazos.cz nabídek entity pro ML training.
...
```

až po konec instrukčního textu.

---

## 📋 KROK 2: Připrav Data

```bash
# Zobraz unlabeled data:
cat unlabeled_for_gpt.json

# Nebo zkopíruj do schránky:
cat unlabeled_for_gpt.json | pbcopy  # macOS
cat unlabeled_for_gpt.json | xclip -selection clipboard  # Linux
```

---

## 📋 KROK 3: Pošli do GPT-4/Claude

### **OPTION A: GPT-4 (OpenAI)**

1. Otevři: https://chat.openai.com
2. Začni novou konverzaci
3. Pošli prompt:

```
[PASTE CELÝ PROMPT Z gpt_entity_extraction_prompt_v2.md]

INPUT DATA:
[PASTE OBSAH unlabeled_for_gpt.json]
```

4. Počkej na odpověď (~5-10 min pro 193 examples)

---

### **OPTION B: Claude (Anthropic)**

1. Otevři: https://claude.ai
2. Začni novou konverzaci
3. Pošli prompt:

```
[PASTE CELÝ PROMPT Z gpt_entity_extraction_prompt_v2.md]

INPUT DATA:
[PASTE OBSAH unlabeled_for_gpt.json]
```

4. Počkej na odpověď (~5-10 min pro 193 examples)

---

## 📋 KROK 4: Ulož Output

GPT/Claude vrátí formát:

```json
[
  [
    "Škoda Karoq 2.0 TDi,110 kW,DSG,Sportline,4x4,LED,DPH,tažné...",
    {
      "entities": [
        [20, 26, "POWER"],
        ...
      ]
    }
  ],
  ...
]
```

**Ulož jako:**

```bash
# Zkopíruj GPT output (celý JSON array)
# Ulož jako auto_labeled_193.json

# Nebo v terminálu:
cat > auto_labeled_193.json << 'EOF'
[PASTE GPT OUTPUT HERE]
EOF
```

---

## 📋 KROK 5: Zkontroluj Output

```bash
# Check soubor existuje:
ls -lh auto_labeled_193.json

# Check počet examples:
python3 -c "import json; data=json.load(open('auto_labeled_193.json')); print(f'{len(data)} labeled examples')"

# Check sample:
python3 -c "import json; data=json.load(open('auto_labeled_193.json')); print('Sample:', data[0][0][:100]); print('Entities:', data[0][1]['entities'][:3])"

# Expected output:
# 193 labeled examples
# Sample: Škoda Karoq 2.0 TDi,110 kW,DSG,Sportline,4x4,LED,DPH,tažné. Prodám Škoda Karoq 2.0 TDi...
# Entities: [[20, 26, 'POWER'], ...]
```

---

## 📋 KROK 6: Combine + Train

```bash
# Spusť training workflow:
python3 retrain_model.py

# Nebo manuálně:
python3 combine_and_train.py
```

(Scripts ready in next commit!)

---

## ❓ TROUBLESHOOTING

### **GPT vrací chybu "Too long"**

Pokud 193 examples je moc:

```bash
# Split do chunks:
python3 << 'EOF'
import json

data = json.load(open('unlabeled_for_gpt.json'))

# Split to 3 chunks
chunk_size = 65
for i in range(0, len(data), chunk_size):
    chunk = data[i:i+chunk_size]
    with open(f'unlabeled_chunk_{i//chunk_size + 1}.json', 'w', encoding='utf-8') as f:
        json.dump(chunk, f, ensure_ascii=False, indent=2)
    print(f'Created chunk {i//chunk_size + 1}: {len(chunk)} examples')
EOF

# Pak pošli každý chunk zvlášť do GPT
# Merge outputs:
python3 merge_chunks.py
```

### **GPT vrací špatný formát**

Check:
- Je to valid JSON? (zkus parse)
- Je to array of arrays? (correct format)
- Má každý example entities dict?

Fix:
```bash
python3 validate_labeled_data.py auto_labeled_193.json
```

### **Nejsem si jistý jestli GPT udělal dobře**

Spot check:
```bash
python3 << 'EOF'
import json
data = json.load(open('auto_labeled_193.json'))

# Check random example
import random
example = random.choice(data)

text = example[0]
entities = example[1]['entities']

print('Text:', text[:200])
print('\nEntities:')
for start, end, label in entities:
    entity_text = text[start:end]
    print(f'  [{start}, {end}, "{label}"] → "{entity_text}"')
EOF

# Manually verify:
# - Do positions match exact text?
# - Is "193.500" NOT normalized to "193500"?
# - Are all entities relevant?
```

---

## 🎯 EXPECTED RESULT

After GPT labeling:

```
✅ auto_labeled_193.json created
✅ 193 new labeled examples
✅ Ready to combine with existing 240
✅ Total: 433 labeled examples!
✅ Ready to retrain model!

Expected improvement:
  Before: F1 ~78.8%
  After: F1 ~85%+ (with 433 examples!)
```

---

**GOOD LUCK!** 🍀

When done, come back and run:
```bash
python3 retrain_model.py
```
