# PROMPTS PRO CLAUDE CHAT (s CSV screenshot)

## 📋 PROMPT 1: Analýza gap_analysis.csv

**Kdy použít:** Po spuštění `analyze_extraction_gaps.py` - chceš identifikovat missing patterns

**Jak připravit screenshot:**
1. Otevři `gap_analysis.csv` v Excel/LibreOffice
2. Vyfiltruj sloupce: `id`, `gap_type`, `missed_year_context`, `missed_mileage_context`, `missed_fuel_context`
3. Screenshot prvních 20-30 řádků
4. Upload do Claude chat

**PROMPT:**

```
Analyzuj tento CSV soubor s extraction gaps z Bazos.cz auto nabídek.

KONTEXT:
- Scraper stahuje nabídky aut z Bazos.cz
- Extraction extrahuje: year (rok výroby), mileage (nájezd km), fuel (palivo), power (výkon kW)
- Tento CSV obsahuje GAPS - co je v textu, ale extraction to nenašlo

CSV SLOUPCE:
- id: ID nabídky
- gap_type: Co chybí (year/mileage/fuel)
- missed_year_context: Text kde extraction NENAŠLO rok
- missed_mileage_context: Text kde extraction NENAŠLO nájezd
- missed_fuel_context: Text kde extraction NENAŠLO palivo

ÚKOL:
1. **Analyzuj "missed_*_context" sloupce**
   - Najdi COMMON PATTERNS které se opakují
   - Identifikuj regex patterns které extraction CHYBÍ

2. **Pro YEAR gaps:**
   - Hledej formáty datumů: "r.v. MM/YYYY", "rok výroby 2020", "1.reg.2015", atd.
   - Ignoruj: STK datumy, servisní záznamy, výměny dílů

3. **Pro MILEAGE gaps:**
   - Hledej formáty: "najeto 150000", "150.000 km", "150 tis", "nájezd 200tis", atd.
   - POZOR: Neplést kW (kilowatty výkon) s km (kilometry)!
   - Ignoruj: servisní záznamy "servis při 150000km", dosah elektromobilu

4. **Pro FUEL gaps:**
   - Hledaj: "benzin", "nafta", "diesel", "lpg", "cng", "hybrid", "elektro"
   - Různé tvary: "benzinový", "naftový", "dieselový"

VÝSTUP:
Pro každý gap type mi dej:
- **Missing pattern** (regex nebo description)
- **Příklady** z CSV kde tento pattern chybí (3-5 příkladů)
- **Priorita** (high/medium/low) - jak často se opakuje

FORMÁT ODPOVĚDI:

### YEAR MISSING PATTERNS

**Pattern 1:** [popis pattern]
- Regex: `...`
- Příklady:
  - ID 27: "..."
  - ID 47: "..."
- Priorita: HIGH (vyskytuje se 15× z 20 gaps)

**Pattern 2:** ...

### MILEAGE MISSING PATTERNS

**Pattern 1:** [popis pattern]
- Regex: `...`
- Příklady: ...
- Priorita: ...

### SUMMARY

Top 3 priority patterns to add:
1. ...
2. ...
3. ...
```

---

## 📊 PROMPT 2: Analýza analysis_results.csv

**Kdy použít:** Po spuštění `scrape_and_analyze_incomplete.py` - chceš vidět co extraction NAŠLO vs. co je v DB

**Jak připravit screenshot:**
1. Otevři `analysis_results.csv` v Excel/LibreOffice
2. Vyfiltruj sloupce: `id`, `scraped_title`, `extracted_year`, `current_year`, `extracted_mileage`, `current_mileage`, `extraction_improved`
3. Screenshot prvních 20-30 řádků
4. Upload do Claude chat

**PROMPT:**

```
Analyzuj tento CSV soubor s extraction results z Bazos.cz auto nabídek.

KONTEXT:
- Scraper stáhl FRESH data z 100 incomplete nabídek
- Extraction extrahoval year/mileage/fuel/power z fresh data
- Tento CSV porovnává extracted values vs. current DB values

CSV SLOUPCE:
- id: ID nabídky
- scraped_title: FRESH title z Bazos
- scraped_description: FRESH description (truncated)
- extracted_year: Rok výroby (NEW extraction)
- current_year: Rok výroby (current DB value)
- extracted_mileage: Nájezd km (NEW extraction)
- current_mileage: Nájezd km (current DB value)
- extraction_improved: YES/NO/year/mileage/fuel/power

ÚKOL:
1. **Spočítej IMPROVEMENT RATE:**
   - Kolik nabídek mělo extraction_improved = YES nebo obsahuje "year"/"mileage"?
   - Improvement rate = (improved offers / total offers) × 100%

2. **Identifikuj STILL FAILING offers:**
   - Kde extraction_improved = NO
   - Kde extracted_year = None AND current_year = None (stále chybí)
   - Kde extracted_mileage = None AND current_mileage = None

3. **Analyzuj STILL FAILING examples:**
   - Podívej se na scraped_title pro failed offers
   - Jsou tam YEAR/MILEAGE ale extraction to nenašlo?
   - Jaké patterns chybí?

4. **Najdi FALSE POSITIVES (pokud jsou):**
   - Kde extracted_year ≠ current_year (a current_year není NULL)
   - Kde extracted_mileage ≠ current_mileage (a current_mileage není NULL)
   - Je to improvement nebo chyba?

VÝSTUP:
- **Improvement rate:** X% (Y/Z offers improved)
- **Still failing:** N offers (list IDs)
- **Missing patterns** (top 3-5 z failing offers)
- **False positives** (if any)
- **Recommendation:** Re-extract all 1049 offers? Or iterate more?

FORMÁT ODPOVĚDI:

### IMPROVEMENT SUMMARY
- Total offers: 100
- Improved (extraction_improved != NO): X offers (X%)
- Still failing: Y offers (Y%)
- Scrape failed: Z offers

### STILL FAILING EXAMPLES
ID | scraped_title | Missing
---|---------------|----------
27 | "Mazda 6 2016..." | year (pattern: "2016" at end)
...

### MISSING PATTERNS (from failing offers)
1. [Pattern description]
2. ...

### RECOMMENDATION
- ✅ Re-extract all 1049 offers (if improvement > 20%)
- 🔄 Iterate more (if improvement < 20% or many gaps remain)
- 🎯 Add patterns: [list]
```

---

## 🎯 PROMPT 3: Quick Pattern Validation

**Kdy použít:** Chceš rychle zkontrolovat jestli pattern matchuje text

**PROMPT:**

```
Otestuj tento regex pattern na těchto příkladech z Bazos.cz:

**Pattern (Python regex):**
`r'(?:r\.?\s?v\.?)\s*[:.]?\s*\d{1,2}/(\d{4})'`

**Test cases:**
1. "Mazda 6 r.v.01/2022 NAVI"
   → Očekávám: 2022

2. "Škoda Octavia r.v. 8/2015"
   → Očekávám: 2015

3. "Ford Focus rok výroby 2018"
   → Očekávám: NE MATCH (jiný pattern)

Projdi každý test case a řekni:
- ✅ MATCH / ❌ NO MATCH
- Captured group: hodnota
- Je pattern správně? Pokud ne, navrhni fix.
```

---

## 📸 JAK UDĚLAT DOBRÝ SCREENSHOT CSV:

### Excel/LibreOffice:
```
1. Otevři CSV
2. Filter/Sort podle gap_type nebo extraction_improved
3. Skryj nepotřebné sloupce (url, atd.)
4. Zvětši řádky aby se vešel text
5. Screenshot 20-30 řádků
6. Pokud je to dlouhé → udělej 2-3 screenshoty
```

### Alternativa - Markdown table:
```
Pokud CSV není moc velký, můžeš ho zkopírovat jako markdown tabulku:

| id | gap_type | missed_year_context |
|----|----------|---------------------|
| 27 | year     | "08/2016 (Německo)" |
| 47 | year     | "Rok výroby 07/2020"|
...

A vložit přímo do promptu (bez screenshotu).
```

---

## 💡 TIPY:

1. **Pro gap_analysis.csv:**
   - Focus na "missed_*_context" columns
   - Hledej COMMON patterns (ne edge cases)
   - Prioritizuj patterns co se opakují 5+ krát

2. **Pro analysis_results.csv:**
   - Focus na "extraction_improved = NO" rows
   - Porovnej scraped_title s extracted_* values
   - Hledej co extraction MĚLO najít ale nenašlo

3. **Iterace:**
   - 1st iteration: Add obvious missing patterns
   - 2nd iteration: Test na 100 samples
   - 3rd iteration: Add edge cases
   - Full re-extraction když improvement > 80%

---

**🚀 POUŽITÍ:**

```bash
# 1. Vygeneruj CSV
python3 scripts/analyze_extraction_gaps.py analysis_results.csv

# 2. Otevři gap_analysis.csv v Excel
# 3. Screenshot prvních 30 řádků
# 4. Upload do Claude chat s PROMPT 1
# 5. Claude ti identifikuje missing patterns
# 6. Přidej patterns do ml/context_aware_patterns.py
# 7. Re-run analysis
# 8. Repeat!
```

---

**Uloženo do:** `scripts/CLAUDE_CHAT_PROMPTS.md`
