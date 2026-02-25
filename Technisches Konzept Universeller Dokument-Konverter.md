# Technisches Konzept: Universeller Dokument-Konverter für LangDock

**Version:** 1.0
**Datum:** 2026-02-25
**Autor:** Equitania Software GmbH
**Zweck:** Technisches Destillat als Grundlage für die Python-Implementierung

---

## 1. Problemstellung

LangDock-Wissensordner akzeptieren ausschließlich **Markdown, PDF, DOCX und TXT**. Die interne RAG-Engine zerlegt Dokumente in Chunks und indexiert sie über Vektorsuche. Damit die Suche präzise funktioniert, muss jeder Chunk **selbstbeschreibend und strukturiert** sein.

Fremddokumente (Word, Excel, CSV, JSON, YAML, XML) liegen in Formaten vor, die von LangDock entweder gar nicht oder mit starken Qualitätseinbußen verarbeitet werden. Der Konverter überbrückt diese Lücke.

---

## 2. Grundsatzentscheidung: KI oder reines Python?

Die Frage ist nicht binär – sie hängt vom **Dokumenttyp und der Anforderung an Qualität** ab.

### 2.1 Was reines Python leisten kann

| Aufgabe | Python-Bibliothek | Qualität |
|---|---|---|
| Word → Text/Struktur | `python-docx` | ✅ Gut (für einfache Dokumente) |
| Excel → Daten | `openpyxl`, `pandas` | ✅ Sehr gut |
| CSV → Daten | `csv`, `pandas` | ✅ Sehr gut |
| JSON → Struktur | `json` (stdlib) | ✅ Perfekt |
| YAML → Struktur | `pyyaml` | ✅ Perfekt |
| XML → Struktur | `lxml`, `xml.etree` | ✅ Gut |
| PDF → Text | `pdfplumber`, `pymupdf` | ⚠️ Gut, aber layout-abhängig |
| PDF (Scan) → Text | `tesseract` + `pdf2image` | ⚠️ OCR-Qualität variiert |
| Tabellenstruktur erkennen | regelbasiert | ⚠️ Nur für bekannte Schemata |
| Semantische Sektionierung | regelbasiert | ❌ Scheitert bei Freitext |
| Kontextverständnis | - | ❌ Nicht möglich |

**Fazit:** Für **strukturierte Formate** (CSV, JSON, YAML, XML, Excel mit bekanntem Schema) leistet reines Python **90–100 %** der Konvertierung deterministisch und ohne KI.

### 2.2 Wo KI zwingend notwendig ist

| Situation | Warum Python nicht ausreicht |
|---|---|
| Unbekannte PDF-Layouts | Keine generische Tabellenstruktur erkennbar |
| Word-Dokumente mit Freitext | Sinnvolle Abschnittsgliederung fehlt |
| Heterogene Excel-Strukturen | Header-Erkennung ohne Schema nicht zuverlässig |
| Mehrsprachige Dokumente | Feldzuordnung DE/EN nicht regelbasiert lösbar |
| Validierung (100 % Korrektheit) | Semantische Prüfung erfordert Sprachverständnis |
| Deduplizierung ähnlicher Inhalte | Bedeutungsbasierter Abgleich nötig |
| Metadaten-Inferenz | Fehlende Angaben aus Kontext erschließen |

### 2.3 Empfohlene Hybrid-Architektur

```
Eingabedatei
     │
     ▼
┌─────────────────────┐
│  STUFE 1: PYTHON    │  ← Deterministisch, schnell, kostenlos
│  Strukturextraktion │    Bibliotheken: docx, openpyxl, pandas,
│  (immer aktiv)      │    pdfplumber, lxml, pyyaml, json
└──────────┬──────────┘
           │
           ▼
      Strukturgüte
      gut genug?
     /           \
   JA             NEIN
    │               │
    │         ┌─────▼──────────────┐
    │         │  STUFE 2: KI       │  ← Optional, kostenpflichtig
    │         │  Analyse & Anreiche│    LangDock/Claude via
    │         │  rung              │    eq-chatbot-core
    │         └─────┬──────────────┘
    │               │
    └───────┬────────┘
            │
            ▼
┌───────────────────────┐
│  STUFE 3: MARKDOWN    │  ← Immer Python
│  Generierung          │    YAML-Frontmatter +
│  (immer aktiv)        │    selbstbeschreibende Abschnitte
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  STUFE 4: VALIDIERUNG │  ← KI empfohlen für 100%-Qualität
│  (KI-gestützt)        │    Vollständigkeits- & Sinnprüfung
└──────────┬────────────┘
           │
           ▼
    Markdown-Datei
```

**Kernprinzip:** Python extrahiert, KI versteht und validiert.

---

## 3. LangDock-Optimierungsanforderungen für Markdown

Diese Anforderungen gelten **für alle Dateitypen** und müssen vom Konverter eingehalten werden.

### 3.1 Pflichtstruktur

Jede erzeugte Markdown-Datei muss folgendes Schema einhalten:

```markdown
---
quelle:           # z.B. "odoo-18", "excel-export", "word-doc"
typ:              # z.B. "technisches-datenblatt", "kundenstamm"
titel: ""
sprache: de                    # oder "en", "de+en"
stand: ""               # Erstellungs- oder Änderungsdatum
konvertiert: ""     # Konvertierungszeitpunkt
quelldatei: ""      # Original-Dateiname mit Extension
---

# Titel des Dokuments

## Abschnitt 1
- **Feld:** Wert
- **Feld:** Wert

## Abschnitt 2
Freitextinhalt hier.
```

### 3.2 Chunking-kompatible Struktur (kritisch)

LangDock zerlegt Dateien beim Indexieren automatisch in Chunks (~500–1000 Tokens). Jeder Chunk muss **ohne Kontext verständlich** sein:

| ❌ Schlecht (tabellen-basiert) | ✅ Gut (selbstbeschreibend) |
|---|---|
| `\| Feld \| Wert \|` in großer Tabelle | `- **Feld:** Wert` als Liste |
| Header geht beim Chunking verloren | Jeder Eintrag trägt seinen Kontext |
| Spaltenname unklar nach Trennung | Bedeutung bleibt im Chunk erhalten |

### 3.3 Verbotene Konstrukte für LangDock

- Keine großen Markdown-Tabellen (>20 Zeilen) – Spaltenkontext geht verloren
- Keine reinen `<html>`-Tags im Markdown
- Keine eingebetteten Base64-Bilder (zu groß für Chunks)
- Keine verschachtelten Listen tiefer als 3 Ebenen
- Keine Codeblöcke für Nutzdaten (nur für echten Code)

---

## 4. Konverter-Konzept: Dateitypen im Detail

### 4.1 Word (DOCX)

**Python-Bibliothek:** `python-docx`

**Extraktionsstrategie:**
```
DOCX-Datei
  ├── Paragraphen → Heading-Level 1-9 → Markdown-Headings (#, ##, ###)
  ├── Tabellen → Key-Value-Erkennung → selbstbeschreibende Listen
  ├── Listen → Markdown-Listen (-, *)
  ├── Bilder → Beschreibungstext (KI) oder [Bild: Dateiname.png]
  └── Metadaten (Autor, Titel, Datum) → YAML-Frontmatter
```

**KI-Trigger:** Wenn Dokument überwiegend Fließtext ohne klare Struktur ist oder Tabellen nicht als Key-Value interpretierbar sind.

**Herausforderungen:**
- Komplexe verschachtelte Tabellen (KI nötig)
- Eingebettete Objekte (OLE, Charts) → beschreibender Platzhalter
- Tracked Changes → nur finale Version übernehmen

```python
# Konzeptueller Extraktor
from docx import Document

def extract_docx(path: str) -> dict:
    doc = Document(path)
    sections = []
    for para in doc.paragraphs:
        level = int(para.style.name[-1]) if para.style.name.startswith("Heading") else 0
        sections.append({"level": level, "text": para.text})
    tables = []
    for table in doc.tables:
        kv = {}
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) == 2 and cells[0]:
                kv[cells[0]] = cells[1]
        tables.append(kv)
    return {"sections": sections, "tables": tables, "metadata": extract_docx_meta(doc)}
```

---

### 4.2 Excel (XLSX)

**Python-Bibliothek:** `openpyxl`, `pandas`

**Extraktionsstrategie:**
```
XLSX-Datei
  ├── Tabellenblatt 1 → eigene Markdown-Sektion
  ├── Tabellenblatt 2 → eigene Markdown-Sektion
  ├── Header-Zeile (Zeile 1) → Feldnamen
  ├── Datenzeilen → self-describing key-value Blöcke
  └── Formeln → berechnete Werte (nicht Formeltext)
```

**Zeilenaufbereitung (chunking-sicher):**

Statt einer großen Tabelle wird jede Zeile als eigenständiger Block aufbereitet:

```markdown
## Produkt: Artikel-12345 (Zeile 7)

- **Artikelnummer:** 12345
- **Bezeichnung:** Klebeband CMC 70115
- **Preis (€):** 4,50
- **Lagerbestand:** 1.250
- **Lieferant:** Mustermann GmbH
```

**KI-Trigger:** Wenn kein eindeutiger Header erkennbar, mehrere Header-Zeilen, oder Daten über mehrere Sheets hinweg verknüpft sind.

**Herausforderungen:**
- Merged Cells → entmergen, Werte propagieren
- Pivot-Tabellen → als Datentabelle lesen
- Charts → Metadaten-Beschreibung, keine Bild-Einbettung
- Mehrere Sheets mit Querverweisen → KI für Kontextzuordnung

```python
# Konzeptueller Extraktor
import pandas as pd

def extract_xlsx(path: str) -> dict:
    sheets = {}
    xl = pd.ExcelFile(path)
    for sheet_name in xl.sheet_names:
        df = xl.parse(sheet_name)
        df = df.dropna(how="all")
        records = df.to_dict(orient="records")
        sheets[sheet_name] = records
    return sheets
```

---

### 4.3 CSV

**Python-Bibliothek:** `csv` (stdlib), `pandas`

**Extraktionsstrategie:** Einfachster Fall – CSV ist bereits strukturiert.

```
CSV-Datei
  ├── Erste Zeile → Header (Feldnamen)
  ├── Folgezeilen → Datensätze
  └── Encoding-Erkennung → chardet oder charsets
```

**Besonderheit:** Bei sehr großen CSVs (>1.000 Zeilen) wird in Batches aufgeteilt – max. 50 Datensätze pro Markdown-Datei (entspricht LangDock-Upload-Limit-Empfehlung).

**KI-Trigger:** Fast nie nötig, außer:
- Kein Header vorhanden (Spaltenbezeichnungen müssen inferiert werden)
- Mehrere Encoding-Varianten unbekannt
- Daten-Bereinigung erforderlich (uneinheitliche Datumsformate etc.)

```python
import csv
import chardet

def extract_csv(path: str) -> dict:
    with open(path, "rb") as f:
        encoding = chardet.detect(f.read())["encoding"] or "utf-8"
    with open(path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        return {"headers": reader.fieldnames, "records": list(reader)}
```

---

### 4.4 JSON

**Python-Bibliothek:** `json` (stdlib)

**Extraktionsstrategie:** JSON ist selbststrukturierend – Konvertierung vollständig ohne KI möglich.

```
JSON-Datei
  ├── Objekt ({}) → Key-Value → selbstbeschreibende Liste
  ├── Array ([{},...]) → jedes Objekt als eigene Sektion
  ├── Verschachtelt → rekursive Abflachung mit Pfad-Präfix
  └── Typen → Integer, Float, Bool, String, null → direkte Übernahme
```

**Abflachungs-Beispiel:**
```json
{"produkt": {"name": "CMC 70115", "eigenschaften": {"temperatur": 180}}}
```
→
```markdown
- **produkt.name:** CMC 70115
- **produkt.eigenschaften.temperatur:** 180
```

**KI-Trigger:** Wenn Feldnamen kryptisch sind und für menschliche Lesbarkeit übersetzt werden sollen (z.B. `tmp_max_c` → `Maximale Temperatur in °C`).

```python
import json

def flatten_json(data, prefix=""):
    items = {}
    if isinstance(data, dict):
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else k
            items.update(flatten_json(v, key))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            items.update(flatten_json(v, f"{prefix}[{i}]"))
    else:
        items[prefix] = data
    return items
```

---

### 4.5 YAML

**Python-Bibliothek:** `pyyaml`

**Extraktionsstrategie:** Identisch zu JSON – YAML ist ebenfalls selbststrukturierend.

```
YAML-Datei
  ├── Einfache Mappings → Key-Value-Listen
  ├── Verschachtelte Mappings → Abschnitte mit ##, ###
  ├── Listen-Werte → Markdown-Listen
  └── Anchors/Aliases (&, *) → aufgelöst vor Konvertierung
```

**Vorteil gegenüber JSON:** YAML erlaubt Kommentare – diese können als Beschreibungstext in den Markdown-Output übernommen werden.

**KI-Trigger:** Praktisch nie nötig.

---

### 4.6 XML

**Python-Bibliothek:** `lxml`, `xml.etree.ElementTree` (stdlib)

**Extraktionsstrategie:** Komplexer als JSON/YAML durch Attribute, Namespaces und Mischinhalt.

```
XML-Datei
  ├── Root-Element → Haupttitel / YAML-Frontmatter-Typ
  ├── Kindelemente → Sektionen oder Key-Value
  ├── Attribute → als Zusatzfelder in Klammern
  ├── Namespaces → bereinigt/ignoriert
  └── Text-Content → direkt übernommen
```

**XML-Beispiel:**
```xml

  Kapton-Klebeband
  180

```
→
```markdown
## Produkt: CMC70115

- **Bezeichnung:** Kapton-Klebeband
- **Temperatur:** 180 °C
```

**KI-Trigger:** Bei komplexen XML-Schemata (z.B. XBRL, SVG, komplexe Industriestandards) zur Semantik-Zuordnung.

```python
import lxml.etree as ET

def extract_xml(path: str) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    return element_to_dict(root)

def element_to_dict(elem):
    result = {}
    for child in elem:
        tag = child.tag.split("}")[-1]  # Namespace entfernen
        result[tag] = child.text or element_to_dict(child)
        result[tag + "_attrs"] = dict(child.attrib) if child.attrib else {}
    return result
```

---

## 5. KI-Validierung: Ansatz für 100 % Korrektheit

Die Validierungsstufe ist **unabhängig vom Eingabeformat** und prüft das fertige Markdown gegen das Original.

### 5.1 Validierungsebenen

```
EBENE 1: Strukturelle Prüfung (Python, immer)
  ├── YAML-Frontmatter vorhanden und valide?
  ├── Mindestens ein H1-Heading?
  ├── Key-Value-Paare vorhanden (- **Key:** Value)?
  └── Datei nicht leer (< 100 Zeichen)?

EBENE 2: Vollständigkeitsprüfung (Python, immer)
  ├── Numerische Werte aus Original in MD vorhanden?
  ├── Datumswerte übernommen?
  ├── Eigennamen/IDs vorhanden?
  └── Coverage-Score (z.B. 97 % der Schlüsselwerte)

EBENE 3: Semantische Prüfung (KI, bei < 95 % Coverage)
  ├── Sind alle inhaltlichen Aussagen korrekt übertragen?
  ├── Wurden keine Werte vertauscht oder falsch zugeordnet?
  ├── Ist die Abschnittsstruktur sinnvoll für RAG?
  └── Sind selbstbeschreibende Chunks gewährleistet?

EBENE 4: Korrektur (KI, bei Fehlern in Ebene 3)
  └── KI korrigiert und ergänzt den Markdown-Output
```

### 5.2 KI-Validierungsprompt-Strategie

```python
VALIDATION_PROMPT = """
Du bist ein Qualitätsprüfer für Markdown-Konvertierungen.

ORIGINALDOKUMENT (Auszug):
{original_text}

KONVERTIERTES MARKDOWN:
{markdown_content}

Prüfe:
1. Sind alle wesentlichen Informationen aus dem Original im Markdown vorhanden?
2. Wurden Werte korrekt und vollständig übernommen?
3. Ist jeder Abschnitt ohne Kontext verständlich (RAG-fähig)?
4. Gibt es Fehler, Auslassungen oder falsche Zuordnungen?

Antworte als JSON:
{
  "status": "ok" | "korrektur_nötig",
  "coverage_score": 0-100,
  "probleme": ["Problem 1", "Problem 2"],
  "korrigiertes_markdown": "..." | null
}
"""
```

### 5.3 Kosten-Nutzen-Kalkulation für Validierung

| Strategie | KI-Aufrufe | Kosten/1000 Dateien | Qualität |
|---|---|---|---|
| Nur Python-Prüfung | 0 | 0,00 € | ~90 % |
| KI nur bei < 95 % Coverage | ~50–100 | ~1,50 € | ~98 % |
| KI für alle Dateien | 1.000 | ~15,00 € | ~100 % |
| KI nur für Fehlerkorrektur | ~10–30 | ~0,50 € | ~99 % |

**Empfehlung:** Schwellenwert-basiert – KI-Validierung nur wenn Python-Coverage < 95 %.

---

## 6. Universeller Konverter: Architektur

### 6.1 Klassenstruktur

```python
# Abstrakte Basis
class BaseConverter(ABC):
    def extract(self, path: str) -> RawDocument: ...
    def generate_markdown(self, doc: RawDocument) -> str: ...
    def validate(self, original: str, markdown: str) -> ValidationResult: ...

# Konkrete Implementierungen
class DocxConverter(BaseConverter): ...
class XlsxConverter(BaseConverter): ...
class CsvConverter(BaseConverter): ...
class JsonConverter(BaseConverter): ...
class YamlConverter(BaseConverter): ...
class XmlConverter(BaseConverter): ...
class PdfConverter(BaseConverter): ...  # pdfplumber + OCR-Fallback

# Orchestrierer
class UniversalConverter:
    CONVERTERS = {
        ".docx": DocxConverter,
        ".xlsx": XlsxConverter,
        ".csv": CsvConverter,
        ".json": JsonConverter,
        ".yaml": YamlConverter,
        ".yml": YamlConverter,
        ".xml": XmlConverter,
        ".pdf": PdfConverter,
    }

    def convert(self, path: str, use_ai: bool = "auto") -> ConversionResult:
        ext = Path(path).suffix.lower()
        converter = self.CONVERTERS.get(ext)
        if not converter:
            raise UnsupportedFormatError(ext)
        return converter().run(path, use_ai=use_ai)
```

### 6.2 Datenmodelle

```python
@dataclass
class RawDocument:
    source_path: str
    source_type: str          # "docx", "xlsx", etc.
    title: str
    language: str             # "de", "en", "de+en"
    date: str | None
    sections: list[Section]
    metadata: dict[str, Any]
    raw_text: str             # Volltext für Validierung

@dataclass
class Section:
    level: int                # 1=H1, 2=H2 etc.
    title: str
    kv_pairs: list[tuple[str, str]]
    free_text: str | None

@dataclass
class ValidationResult:
    status: str               # "ok", "warning", "error"
    coverage_score: float     # 0.0 – 1.0
    issues: list[str]
    ai_used: bool
    corrected_markdown: str | None

@dataclass
class ConversionResult:
    source_path: str
    markdown_path: str
    markdown_content: str
    validation: ValidationResult
    ai_calls: int
    duration_seconds: float
```

### 6.3 YAML-Frontmatter-Schema (universell)

```python
def build_frontmatter(doc: RawDocument, converter_version: str) -> str:
    meta = {
        "quelle": doc.source_type,
        "typ": infer_document_type(doc),     # Regelbasiert
        "titel": doc.title,
        "sprache": doc.language,
        "stand": doc.date or "",
        "konvertiert": date.today().isoformat(),
        "quelldatei": Path(doc.source_path).name,
        "konverter_version": converter_version,
    }
    return "---\n" + yaml.dump(meta, allow_unicode=True) + "---"
```

---

## 7. Python-Bibliotheken (Zusammenfassung)

| Bibliothek | Verwendung | Lizenz | Bemerkung |
|---|---|---|---|
| `python-docx` | DOCX-Extraktion | MIT | Stabil, weit verbreitet |
| `openpyxl` | XLSX-Lesen/Schreiben | MIT | Auch für Formeln |
| `pandas` | Tabellendaten-Verarbeitung | BSD | Optional, aber empfohlen |
| `pdfplumber` | PDF-Textextraktion | MIT | Bewährt aus CMC-Projekt |
| `pymupdf` (fitz) | PDF → Bild (OCR-Vorbereitung) | AGPL/kommerziell | Lizenz beachten! |
| `pytesseract` | OCR für Bild-PDFs | Apache 2.0 | Tesseract muss installiert sein |
| `lxml` | XML-Parsing | BSD | Schneller als stdlib |
| `pyyaml` | YAML-Parsing | MIT | Anchors/Aliases werden aufgelöst |
| `chardet` | Encoding-Erkennung | LGPL | Für CSV/TXT-Dateien |
| `python-magic` | MIME-Type-Erkennung | MIT | libmagic nötig (puremagic als Alternative) |
| `cryptography` | API-Key-Verschlüsselung | Apache 2.0 | Bereits in eq-chatbot-core |
| `eq-chatbot-core` | KI-Analyse + LangDock-Upload | MIT | Eure eigene Library |

---

## 8. Entscheidungsmatrix: KI-Einsatz

```
Eingabeformat     Extraktion   KI-Analyse   KI-Validierung
──────────────────────────────────────────────────────────
JSON              Python ✅    Nie          Nur bei Bedarf
YAML              Python ✅    Nie          Nur bei Bedarf
CSV               Python ✅    Selten       Nur bei Bedarf
XML               Python ✅    Selten       Nur bei Bedarf
XLSX (klar)       Python ✅    Selten       Nur bei Bedarf
XLSX (komplex)    Python ⚠️    Ja           Empfohlen
DOCX (strukturiert) Python ⚠️  Selten       Empfohlen
DOCX (Freitext)   Python ❌    Ja           Ja
PDF (Text)        Python ⚠️    Empfohlen    Ja
PDF (Scan/Bild)   OCR ⚠️       Ja           Ja
```

**Faustregel:** Je strukturierter das Format, desto weniger KI wird gebraucht. KI ist immer sinnvoll für die **abschließende Validierung**, wenn 100 % Korrektheit gefordert ist.

---

## 9. Fazit

Ein reines Python-Programm kann **strukturierte Formate** (JSON, YAML, CSV, XML, einfaches Excel) zu **95–98 % korrekt** in LangDock-optimiertes Markdown konvertieren – ohne KI-Kosten. Für komplexe Dokumente (PDF, Word mit Freitext, heterogenes Excel) ist KI-Unterstützung in der Analysestufe sinnvoll.

Die **KI-Validierungsstufe ist die wichtigste Investition**: Sie stellt unabhängig vom Eingabeformat und Konvertierungsweg sicher, dass das Markdown vollständig, korrekt und RAG-fähig ist. Mit einem Coverage-Schwellenwert von 95 % hält man die KI-Kosten minimal und die Qualität maximal.

Die `eq-chatbot-core`-Library liefert bereits alle nötigen Bausteine: Provider für die KI-Analyse, `LangDockKnowledgeManager` für den Upload und `FernetEncryption` für die sichere API-Key-Verwaltung.