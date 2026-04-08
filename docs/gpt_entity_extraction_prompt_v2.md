# 🤖 GPT Entity Extraction Prompt (v2 - FIXED)

## **🎯 ÚČEL PROMPTU:**

Tento prompt se použije v GPT-4 pro automatické labelování training dat.

**CO DĚLÁ:**
1. Dostane 500 car offers z Bazos.cz (JSON array)
2. Najde v každé nabídce entity: YEAR, MILEAGE, FUEL, POWER
3. Vrátí spaCy training format s přesnými character positions

**KAM TO JDE:**
```
Input: unlabeled_data.json (500 offers)
  ↓
GPT-4 (s tímto promptem)
  ↓
Output: auto_training_data.json (500 labeled examples)
  ↓
ML training pipeline
```

---

## **📝 PROMPT PRO GPT-4:**

```
Extrahuj z těchto Bazos.cz nabídek entity pro ML training.

VSTUP: JSON array s car offers z Bazos.cz
VÝSTUP: spaCy training format s přesnými character positions

🎯 TVŮJ ÚKOl:
Pro každou nabídku najdi entity: YEAR, MILEAGE, FUEL, POWER

---

## 1️⃣ YEAR (rok výroby)

**CO HLEDAT:**
- Rok výroby vozu (YYYY formát, 1990-2026)
- Běžné fráze: "r.v. 2015", "rok 2015", "2015", "z roku 2015"

**CO IGNOROVAT:**
- STK datumy ("STK do 2026")
- Servisní záznamy ("serviska 2023")
- Jiné roky (ne výroba)

**PŘÍKLADY:**
```
"Škoda Fabia r.v. 2015, diesel"
→ Entity: [17, 21, "YEAR"]  # "2015"

"Prodám VW Golf rok 2018"
→ Entity: [20, 24, "YEAR"]  # "2018"
```

---

## 2️⃣ MILEAGE (nájezd v km)

**⚠️ KRITICKY DŮLEŽITÉ: NAJDI EXACT TEXT!**

**CO HLEDAT:**
- Nájezd v kilometrech
- **VŠECHNY možné varianty formátu:**
  ```
  150000 km      ← číslo bez mezer
  150 000 km     ← mezery jako tisíce
  150.000 km     ← tečky jako tisíce
  150,000 km     ← čárky jako tisíce
  150tis km      ← "tis" = tisíc
  150 tis. km    ← "tis." s tečkou
  150kkm         ← "k" = tisíc (150k km)
  najeto 150000  ← slovo "najeto"
  193.500km      ← bez mezery před km
  ```

**🚨 ZÁSADNÍ PRAVIDLO:**
```
❌ NEDĚLÁŠ: Normalizaci čísel!
   Text: "193.500km"
   ŠPATNĚ: Entity value = "193500"  ← NO!

✅ DĚLÁŠ: Najdeš EXACT text včetně teček/mezer!
   Text: "193.500km"
   SPRÁVNĚ: Entity value = "193.500"  ← YES! Exact match!

→ Normalizace se dělá AŽ POZDĚJI v ML preprocessing!
→ TY najdi PŘESNĚ co je napsáno v textu!
```

**PŘÍKLADY:**
```
"najeto 193.500km"
→ Entity: [7, 14, "MILEAGE"]  # "193.500" (včetně tečky!)

"najeto 150 tis km"
→ Entity: [7, 14, "MILEAGE"]  # "150 tis" (včetně mezery!)

"150000km, benzín"
→ Entity: [0, 6, "MILEAGE"]   # "150000" (bez teček)

"nájezd: 120.000 km"
→ Entity: [8, 15, "MILEAGE"]  # "120.000" (s tečkami!)
```

**PROČ JE TO DŮLEŽITÉ:**
```
ML model se musí NAUČIT rozpoznat VŠECHNY varianty:
  ✓ "150.000" s tečkami
  ✓ "150 000" s mezerami
  ✓ "150000" bez formátování
  ✓ "150tis" s "tis"

Když ty normalizuješ → model nikdy neuvidí originální text!
→ Pak model NENAJDE "193.500" protože viděl jen "193500"!
```

---

## 3️⃣ FUEL (typ paliva)

**CO HLEDAT:**
- Typ paliva: benzín, diesel, lpg, elektro, hybrid
- **Varianty:**
  ```
  benzín  ← standard
  benzin  ← bez diakritiky
  nafta   ← diesel variant
  diesel  ← standard
  TDi     ← diesel (Volkswagen Group)
  HDi     ← diesel (Peugeot/Citroën)
  CDi     ← diesel (Mercedes)
  lpg     ← plyn
  cng     ← stlačený plyn → "lpg"
  elektro ← electric
  hybrid  ← hybrid
  ```

**VÝSTUP:**
- Vrať EXACT text jak je v nabídce!
- **NE lowercase, NE normalizace!**

**PŘÍKLADY:**
```
"2.0 TDi, 103kW"
→ Entity: [4, 7, "FUEL"]  # "TDi" (exact case!)

"1.4 benzín"
→ Entity: [4, 10, "FUEL"]  # "benzín" (s diakritikou!)

"diesel, 2015"
→ Entity: [0, 6, "FUEL"]  # "diesel"
```

---

## 4️⃣ POWER (výkon v kW)

**CO HLEDAT:**
- Výkon motoru v kilowatech (kW)
- Formát: číslo 20-500
- **Běžné formáty:**
  ```
  114kW       ← bez mezery
  114 kW      ← s mezerou
  114KW       ← uppercase
  (114kW)     ← v závorkách
  114kw       ← lowercase
  ```

**CO IGNOROVAT:**
- HP/PS (koňské síly) - hledáme JEN kW!
- Objem motoru ("2.0")
- Jiné hodnoty

**PŘÍKLADY:**
```
"2.0 TDi 103kW"
→ Entity: [8, 11, "POWER"]  # "103" (jen číslo!)

"Octavia (110 kW)"
→ Entity: [9, 12, "POWER"]  # "110"

"1.9TDI 66KW"
→ Entity: [7, 9, "POWER"]   # "66"
```

---

## 📤 OUTPUT FORMÁT

**spaCy training format:**

```json
[
  [
    "Mazda 6 2.0i 114KW, r.v. 2011, KŮŽE, VÝHŘEV, najeto 193.500km",
    {
      "entities": [
        [14, 17, "POWER"],      // "114" (positions 14-17)
        [26, 30, "YEAR"],       // "2011" (positions 26-30)
        [50, 57, "MILEAGE"]     // "193.500" (positions 50-57, EXACT text!)
      ]
    }
  ],
  [
    "VW Golf 1.9 TDi 77kW, diesel, 2005, 150 tis km",
    {
      "entities": [
        [16, 18, "POWER"],      // "77"
        [23, 29, "FUEL"],       // "diesel"
        [31, 35, "YEAR"],       // "2005"
        [37, 44, "MILEAGE"]     // "150 tis" (EXACT text s mezerou!)
      ]
    }
  ],
  [
    "Prodám auto",
    {
      "entities": []            // Žádné entity v textu
    }
  ]
]
```

---

## ✅ KONTROLNÍ CHECKLIST:

**PRO KAŽDOU NABÍDKU:**

1. ✅ Přečti celý text
2. ✅ Najdi všechny entity (year, mileage, fuel, power)
3. ✅ Pro každou entitu:
   - Najdi EXACT text v původní nabídce (včetně teček, mezer!)
   - Spočítej character offset (start position)
   - Spočítej end position (start + length)
   - Vytvoř tuple: `[start, end, "TYPE"]`
4. ✅ Pokud entity není → nepřidávej ji!
5. ✅ Vrať JSON array pro VŠECHNY nabídky

---

## 🚨 ČASTÉ CHYBY (VYHNI SE JIM!):

### ❌ CHYBA 1: Normalizace čísel
```
ŠPATNĚ:
  Text: "193.500km"
  Entity value: "193500"  ← normalizováno!
  Positions: [7, 13]      ← pozice pro "193500" (6 chars)

  PROBLÉM: Text má "193.500" (7 chars) ale positions jsou pro 6 chars!
  → MISALIGNED! Model se nenaučí!

SPRÁVNĚ:
  Text: "193.500km"
  Entity value: "193.500"  ← EXACT text!
  Positions: [7, 14]       ← pozice pro "193.500" (7 chars)

  → ALIGNED! Model se naučí rozpoznat "193.500"!
```

### ❌ CHYBA 2: Lowercase normalizace
```
ŠPATNĚ:
  Text: "2.0 TDi"
  Entity: "diesel"  ← změněno na lowercase!

SPRÁVNĚ:
  Text: "2.0 TDi"
  Entity: "TDi"     ← EXACT text!
```

### ❌ CHYBA 3: Špatné positions
```
ŠPATNĚ:
  Text: "VW Golf 2015"
  Entity: [8, 12, "YEAR"]  ← "2015" starts at 8, not 9!

SPRÁVNĚ:
  Text: "VW Golf 2015"
         01234567890123
  Entity: [8, 12, "YEAR"]  ← positions 8-12 = "2015"
```

---

## 📊 OČEKÁVANÝ OUTPUT:

```
Počet nabídek: 500
↓
Expected output:
  ~450-480 with at least one entity
  ~20-50 without entities (empty)

Average entities per offer: 2-3
  (např: year + mileage + fuel)
```

---

## 🎯 FINÁLNÍ INSTRUKCE:

1. **Zpracuj VŠECH 500 nabídek**
2. **Najdi EXACT text** (žádná normalizace!)
3. **Přesné character positions**
4. **Vrať celý JSON array**

**ZAČNI TEĎ! 🚀**
```

---

## **🔧 CO SE ZMĚNILO:**

### **1. Jasný účel promptu:**
```
✅ Vysvětluje KDE a JAK se prompt použije
✅ Ukazuje celý flow: Input → GPT → Output → ML
✅ User ví co očekávat
```

### **2. MILEAGE: Všechny varianty formátu:**
```
✅ Přidány VŠECHNY možné varianty:
   - 150.000 (tečky)
   - 150 000 (mezery)
   - 150tis (tis)
   - 150kkm (k jako tisíc)
   - atd.

✅ ZDŮRAZNĚNO: Najdi EXACT text!
   - Včetně teček, mezer, čárek
   - NO normalization!
```

### **3. Vysvětlení PROČ nechceme normalizovat:**
```
✅ Ukázka problému:
   Text: "193.500km"
   Normalizace: "193500"
   → MISALIGNED positions!
   → Model se NENAUČÍ najít "193.500"!

✅ Vysvětlení kdy se normalizace dělá:
   → AŽ POZDĚJI v ML preprocessing!
   → NE v GPT output!
```

### **4. Kontrolní checklist:**
```
✅ Step-by-step guide co dělat
✅ Časté chyby a jak se jim vyhnout
✅ Příklady SPRÁVNĚ vs ŠPATNĚ
```

### **5. Odstranění matoucích instrukcí:**
```
❌ ODSTRANĚNO: "Normalizuj hodnoty"
❌ ODSTRANĚNO: "Fuel na lowercase"
❌ ODSTRANĚNO: Všechny normalizace

✅ PŘIDÁNO: "Najdi EXACT text jak je napsaný"
✅ PŘIDÁNO: Důraz na přesné positions
```

---

## **📝 POUŽITÍ:**

```bash
# 1. ZKOPÍRUJ prompt z gpt_entity_extraction_prompt_v2.md

# 2. OTEVŘI GPT-4 (nebo Claude with long context)

# 3. POŠLI prompt + data:
"""
[PROMPT Z TOHOTO SOUBORU]

INPUT DATA:
[
  {"text": "Škoda Fabia 1.2 HTP 47kW 2003 180tis km serviska najeto 238500"},
  {"text": "VW Golf 1.9 TDi 77kW diesel 2005"},
  ...  # 500 offers
]
"""

# 4. ZKONTROLUJ OUTPUT:
# - Jsou positions správně?
# - Našel všechny varianty (193.500, 150 tis, atd)?
# - Žádná normalizace?

# 5. ULOŽ jako auto_training_data.json

# 6. POUŽIJ pro trénink:
python3 -m ml.train_ml_model --data auto_training_data.json
```

---

## **🧪 TESTOVÁNÍ:**

```json
// Test examples (use these to verify GPT output):
[
  {
    "text": "Škoda Fabia 2015 najeto 193.500km benzín",
    "expected_entities": [
      [12, 16, "YEAR"],      // "2015"
      [24, 31, "MILEAGE"],   // "193.500" (with dot!)
      [34, 40, "FUEL"]       // "benzín" (with accent!)
    ]
  },
  {
    "text": "VW Golf 1.9 TDi 77kW 2005 150 tis km",
    "expected_entities": [
      [12, 15, "FUEL"],      // "TDi" (exact case!)
      [16, 18, "POWER"],     // "77"
      [21, 25, "YEAR"],      // "2005"
      [26, 33, "MILEAGE"]    // "150 tis" (with space!)
    ]
  },
  {
    "text": "Prodám auto 120000km diesel 103kW",
    "expected_entities": [
      [12, 18, "MILEAGE"],   // "120000" (no dots!)
      [21, 27, "FUEL"],      // "diesel"
      [28, 31, "POWER"]      // "103"
    ]
  }
]
```

Pokud GPT vrátí tyto positions správně → prompt funguje! ✅

---

## **💡 PROČ JE TO LEPŠÍ:**

```
PŘED (v1):
  ❌ Matoucí: "Normalizuj hodnoty"
  ❌ Nejasné: Proč to děláme?
  ❌ Chybějící: Varianty formátu
  ❌ Výsledek: Misaligned entities!

PO (v2):
  ✅ Jasné: "Najdi EXACT text"
  ✅ Vysvětlené: Proč nechceme normalizovat
  ✅ Kompletní: VŠECHNY varianty formátu
  ✅ Výsledek: Aligned entities! Model se naučí!
```

---

**READY TO USE! 🚀**

Chceš to commitnout nebo nejdřív vyzkoušet na sample data?
