# Extraction Issues

Sem zapisuj příklady textů kde extrakce selhala nebo vrátila špatný výsledek.
Když budeš připraven, řekni Claude "zpracuj extraction issues" a on:
1. Přečte tento soubor
2. Otestuje každý příklad proti aktuálním regex/ML patternům
3. Navrhne a implementuje opravy
4. Označí vyřešené položky

## Formát zápisu

```
### [POLE] krátký popis
- **Text:** `přesný text z inzerátu`
- **Očekávaná hodnota:** 150000
- **Kontext:** volitelná poznámka (např. URL, co se stalo)
```


Pole: MILEAGE, YEAR, FUEL, POWER

---

## Otevřené

<!-- sem přidávej nové případy -->

### [MODEL] špatně přiřazený model
- **Text:** `Prodám nebo vyměním golfa 1.4ku,na autě nové rozvody,nová STK...`
- **Očekávaná hodnota:** volkswagen golf
- **Kontext:** nadpis: “Prodám nebo vymenim”, je to označeno jako passat. Problém v přiřazení modelu, ne ve filtru — inzerát je legitimní auto, ale model je špatně.

## Vyřešené

### [FILTER] 2026-03-28 — chassis, body parts, interior, camper conversions

Oprava: Rozšířeny `_PARTS_KEYWORDS` a `_DESC_PARTS_PHRASES`:
- `šasi`, `korba` (+ skloňování), `nosný rám` — chassis/body
- `sedačky`, `tapece`, `interiér`, `potahy` — interior parts
- `body kit` — body kit sets
- `autovestavba` — camper conversions
- Přidán `r17"` do wheel spec patternu (inch notation bez mezery)

Vyřešené případy:
- ~~Nosný rám (šasi) LC 150~~ → chyceno "šasi" v popisu
- ~~Alu r17" Soho~~ → chyceno `r17"` wheel spec
- ~~Korba amarok~~ → chyceno "korbu" v nadpisu
- ~~Autovestavba RITWAN~~ → chyceno "autovestavba" v nadpisu
- ~~Sedačky/interiér Golf mk2~~ → chyceno "interiér" v nadpisu
- ~~HOFELE body kit Touareg~~ → chyceno "body kit" v nadpisu

### [YEAR] 2026-03-28 — "94 rok" format (2-digit year + rok suffix)

Oprava: Přidán high confidence pattern `(?<!\d)(\d{2})\s+rok\b` do `YEAR_HIGH_CONFIDENCE`.
- ~~94 rok~~ → 1994 (expand: 94 > 29 → 1900 + 94)

### [FILTER] 2026-03-28 — wheels/parts/projects now filtered

Oprava: Přidány nové filtrovací patterny do `check_if_car()`:
- `_WHEEL_SPEC_PATTERNS` — chytá kola/disky (5x112, 7,5jx18, R16)
- `_HEADING_STARTS_WITH_PART` — nadpis začíná “Motor”, “Převodovka” atd.
- `_DESC_PARTS_PHRASES` — “na díly”, “na opravu”, “nemá papíry”, “bez TP” v popisu

Vyřešené případy:
- ~~7,5jx18 5x112 Škoda Luna 18”~~ → chyceno wheel spec pattern
- ~~Octavie na náhradní díly~~ → chyceno “na díly” v popisu
- ~~Motor Octavia III 1.6 CLHB~~ → chyceno heading starts with “Motor”
- ~~Projekt golf + octavia, nemá papíry~~ → chyceno “nemá papíry” v popisu
- ~~Alu RIDE Octavia 5x100 R16~~ → chyceno wheel spec pattern (5x100, R16)

### [YEAR] 2026-03-28 — rok:2002 format

Oprava: Přidán high confidence pattern `rok\s*[:]\s*(\d{4})` do `YEAR_HIGH_CONFIDENCE`.
- ~~rok:2002~~ → zachyceno jako high confidence

### [MILEAGE] 2026-03-28 — Km: prefix + dot separator

Oprava: Přidány high confidence patterns pro `Km:\s*` prefix v `MILEAGE_HIGH_CONFIDENCE`.
- ~~Km: 469.235~~ → 469235 (high confidence)
- ~~300xxx nájezd~~ → 300000 (medium confidence, již fungovalo)

### [FUEL] 2026-03-28 — engine codes (TDI) now high confidence

Oprava: Engine codes (TDI, HDI, TSI, ...) v `production_extractor.py` mají nyní `regex_confidence='high'` místo `'medium'`. Při ML nepotvrzení dostane confidence 0.80 (nad threshold 0.65) → projde verifikací.
- ~~1.9tdi → diesel~~ → regex najde `tdi`, normalizace → `diesel`, verifikace projde
