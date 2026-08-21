---
name: ner-corpus-conductor
description: >
  Thai–Chinese Simplified NER corpus maintenance via CrewAI Flows.
  Use when running NERExtractionFlow (Stage 1) or NERWriteFlow (Stage 2)
  for ingesting documents, confirming new entities, writing entity pages,
  updating corpus indexes, and returning final JSON output.
  Covers agent roles, tool scoping, schema bootstrap, reclassify loop,
  TECHNICAL_TERM sub-folder handling, frontmatter contracts, and log/summary upkeep.
license: Proprietary
compatibility: crewai>=1.15.6
metadata:
  author: HoneyBadger
  version: "2.0"
allowed-tools: ReadRootTool WriteRootTool ReadOverviewTool ReadIndexTool WriteEntityTool FileReadTool
---

# NER Corpus Conductor — CrewAI Edition

## Trigger

Use this skill whenever the task involves `NERExtractionFlow`, `NERWriteFlow`,
or any of the corpus helper functions (`_count_entities_in_type`, `_update_type_index`,
`_update_log`, `_update_summary`, `_update_root_index`).
Do not bypass this skill and write ad-hoc corpus logic — the skill encodes the
correct sequence, tool scoping rules, and format contracts for this project.

---

## Required Reading

Before executing any task in this skill, read the following reference files
from the skill's `references/` directory using `FileReadTool` (or equivalent):

| File | When to read |
|------|-------------|
| `references/entity-classification-decisions.md` | **Always** — canonical rules for type assignment |
| `references/cross-reference-patterns.md` | **Always** — bidirectional wiring patterns |
| `references/handling-non-utf8-sources.md` | Before every ingest (Stage 1) |
| `references/repeated-a-shortcut.md` | During Stage 2 confirm loop |
| `references/sports-ingest-classification-decisions.md` | When domain is sports / sports-tech |

Resolve paths relative to this skill's directory (available at runtime via the skill's `path`).  
**Do not proceed to Stage 1 or Stage 2 without loading at least the first two files.**

---

## Architecture Overview

```
POST /ingest  →  NERExtractionFlow.kickoff_async()
                    └─ run_pipeline()          @start
                         ├─ Bootstrap corpus context (overview.md + index.md)
                         ├─ Manager scout Task  → ExtractionResult (Pydantic)
                         ├─ _run_specialize_pass()  [loop per candidate]
                         │    └─ Specialized Agent Task → SpecializeResult
                         └─ Reclassify while-loop (max MAX_HOP=2)
                    └─ finalize_extraction()   @listen(run_pipeline)
                         └─ reclassify_request → manual_review
                    → returns List[Candidate]  (FastAPI caches in job store)

POST /confirm →  NERWriteFlow.kickoff_async()
                    └─ apply_and_write()       @start
                         ├─ matched  → WriteEntityTool.write(..., mode="append")
                         └─ confirm/edit → WriteEntityTool.write(..., mode="create")
                    └─ save_json()             @listen(apply_and_write)
                    └─ write_log()             @listen(save_json)
                    └─ update_corpus_files()   @listen(write_log)
                         ├─ _update_type_index()   per changed type
                         ├─ _update_type_overview() per changed type
                         ├─ _update_root_index()
                         └─ _update_summary()
                    → returns list[dict]  (final JSON output)
```

---

## Stage 1 — NERExtractionFlow

### Bootstrap (once per flow instance)

`run_pipeline()` อ่าน 2 ไฟล์ก่อนทำอะไรทั้งสิ้น:

```python
corpus_overview = _read("overview.md")   # ภาพรวม corpus, สถิติ, coverage
corpus_index    = _read("index.md")      # map type → path ใน vault
```

ทั้งสองถูก inject เข้า Task description ของ manager เป็น `CORPUS CONTEXT` block
**ห้ามอ่านซ้ำในรอบ specialize หรือ reclassify** — อ่านแค่ครั้งเดียวต่อ flow instance

### Manager Scout Task

- **Agent**: `manager_agent` (Scout/Manager role)
- **Tools**: `ReadRootTool`, `WriteRootTool`
- **Output schema**: `ExtractionResult` → `List[CandidateExtraction]`
- **Responsibilities**:
  - สกัด named entity ทุกตัวจาก raw text
  - ตั้ง `guessed_type` เป็น CAPS จาก `SPECIALIZED_TYPES` เท่านั้น
  - บันทึก `context_sentence` ต้นฉบับของแต่ละ entity
  - กรองคำทั่วไป/ตำแหน่ง (เช่น "นายก") ออก — เก็บเฉพาะ named entity จริง
  - ใช้ corpus context ช่วย classify ให้แม่นขึ้น

### Specialize Pass (`_run_specialize_pass`)

วนทุก candidate ที่ยังไม่ `matched` หรือ `manual_review`:

- **Agent**: `specialized_agents[entity_type]` — 1 agent ต่อ 1 type
- **Tools ต่อ agent** (scoped เฉพาะ type ของตัวเอง):
  - `ReadOverviewTool(entity_type=T)` — อ่าน `Entity_type/T/overview.md`
  - `ReadIndexTool(entity_type=T)` — อ่าน `Entity_type/T/index.md`
  - `WriteEntityTool(entity_type=T)` — เขียนเฉพาะ `Entity_type/T/`
- **Output schema**: `SpecializeResult`
- **Sequence ที่ agent ต้องทำ**:
  1. เรียก `read_overview` → ยืนยันว่า candidate เข้าเกณฑ์ type นี้จริง (เช็ค exclusion rule)
  2. ถ้าเข้าเกณฑ์ → เรียก `read_index` → fuzzy match ≥ 80% กับรายชื่อที่อ่านได้จริง
  3. ถ้าไม่เข้าเกณฑ์ → ตอบ `status=reclassify_request` พร้อม `inference_reason` ระบุ type ที่เหมาะกว่า

**กฎ matched evidence** — ถ้า `status=matched` ต้อง set `matched_evidence` เป็นบรรทัดที่คัดลอกมาจาก index.md จริง
ถ้า `matched_evidence` ว่าง → code จะ auto-downgrade เป็น `no_match`:

```python
if r.status == "matched" and not (r.matched_evidence or "").strip():
    r.status = "no_match"
```

### Reclassify Loop

```python
for _ in range(MAX_HOP):   # MAX_HOP = 2
    pending = [c for c in candidates if c.status == "reclassify_request" and c.hop_count < MAX_HOP]
    if not pending:
        break
    for c in pending:
        c.hop_count += 1
        c.guessed_type = c.inferred_type or c.guessed_type
    _run_specialize_pass(candidates)
```

- CrewAI Flows ไม่รองรับ circular edge → loop เป็น plain Python while ใน `@start` method เดียว
- เกิน MAX_HOP → `finalize_extraction()` บังคับเป็น `manual_review`

### Candidate Status Values (Stage 1 output)

| status | ความหมาย |
|--------|-----------|
| `matched` | พบใน corpus แล้ว — ใช้ canonical form |
| `no_match` | ไม่พบใน corpus — ส่งไป user confirm |
| `reclassify_request` | agent แนะนำ type อื่น — วน loop ใหม่ |
| `manual_review` | เกิน MAX_HOP หรือ specialize error |

---

## Stage 2 — NERWriteFlow

### apply_and_write()

วนทุก candidate และตัดสินใจตาม status + decision:

```
matched  → WriteEntityTool.write(mode="append")   # append context sentence ทันที ไม่รอ confirm
confirm  → WriteEntityTool.write(mode="create")   # สร้างไฟล์ entity ใหม่
edit     → ใช้ edited_th / edited_type จาก ConfirmDecision แทน
skip     → c.status = f"{c.status}_skipped"       # ไม่เขียนอะไร
```

**ห้ามเรียก `WriteEntityTool._run()` ตรงๆ** — ใช้ `WriteEntityTool.write()` เสมอ
เพราะ `BaseTool._run()` ถูก CrewAI wrap และ argument passing อาจผิดพลาด

### Entity File — Frontmatter Schema (ครบทุก field)

```yaml
---
title: {final_th}
th: {final_th}
cn: {final_cn | null}
entity_type: {CAPS_TYPE}
domain: {domain_value | null}   # null ยกเว้น TECHNICAL_TERM
aliases: []
source_count: 1
first_seen: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [lowercase_type]
confidence: medium
---
```

**กฎ domain field**:
- `entity_type != TECHNICAL_TERM` → `domain: null` เสมอ
- `entity_type == TECHNICAL_TERM` → ต้องระบุ domain (`Engineering Domain` | `Finance Domain` | `Healthcare Domain` | `IT Domain`)

### Entity File — Body Sections (ครบทุก section)

```markdown
# {entity_name}

## ข้อมูลพื้นฐาน
- **ภาษาไทย:** {th}
- **ภาษาจีน:** {cn | -}
- **ประเภท:** {entity_type}
- **Aliases:** -

## บริบทที่พบ
| เอกสาร | ประโยคบริบท | วันที่ ingest |
|--------|-------------|--------------|
| {source_doc} | {context_sentence} | YYYY-MM-DD |

## หมายเหตุ / Comment

## Cross-references
```

### Corpus File Update Order (Stage 2 — ห้ามสลับลำดับ)

```
apply_and_write  →  save_json  →  write_log  →  update_corpus_files
                                                    ├─ _update_type_index()      ← per changed type
                                                    ├─ _update_type_overview()   ← per changed type
                                                    ├─ _update_root_index()      ← rebuild ทั้งไฟล์
                                                    └─ _update_summary()         ← rebuild ทั้งไฟล์
```

**อัปเดต corpus files ที่ปลาย flow เสมอ** — ไม่ใช่ทันทีหลัง write entity แต่ละตัว

---

## TECHNICAL_TERM — Special Handling

TECHNICAL_TERM เก็บ entity ใน **sub-folder** ไม่ใช่ root folder:

```
Entity_type/TECHNICAL_TERM/
├── index.md          ← รวมทุก domain (rebuild จาก 4 sub-folder)
├── overview.md
├── Engineering Domain/
│   ├── index.md      ← เฉพาะ entity ใน domain นี้
│   └── {entity}.md
├── Finance Domain/
├── Healthcare Domain/
└── IT Domain/
```

### การนับ entity (`_count_entities_in_type`)

```python
# ถูก — นับจาก sub-folder รวมกัน
if entity_type == "TECHNICAL_TERM":
    total = sum(len(files_in(domain)) for domain in _TECH_TERM_DOMAINS)

# ผิด — root folder ไม่มี entity .md อยู่เลย
folder = "Entity_type/TECHNICAL_TERM/"
count = len(os.listdir(folder))  # จะได้ 0 เสมอ
```

### การ rebuild index (`_update_type_index`)

TECHNICAL_TERM ต้อง rebuild **2 ระดับ**:
1. `<Domain>/index.md` — แยกทีละ domain เฉพาะ entity ใน domain นั้น
2. `TECHNICAL_TERM/index.md` — รวมทุก domain พร้อม tag `[domain]` ต่อท้าย

### `new_entities` dict ต้องมี field `domain`

```python
changed_types["TECHNICAL_TERM"].append({
    "th": c.th,
    "cn": c.cn,
    "status": c.status,
    "domain": c.domain,    # ← จำเป็นสำหรับ _update_type_index แยก domain
})
```

### TECHNICAL_TERM cross-domain ambiguity

ถ้า candidate อาจอยู่ได้ 2 domain ให้ระบุใน Task description:

```
⚠️ domain: IT Domain (primary) | Healthcare Domain (secondary)
```

- เลือก primary domain จาก context หลักของเอกสาร
- บันทึก secondary domain ใน `aliases` หรือ `Cross-references`
- ถ้าแน่ใจไม่ได้ (50/50) → default `IT Domain` + `confidence: medium`

---

## Log Format Contract

```
## [YYYY-MM-DD] ingest | {source_doc} | {N} new, {N} matched
## [YYYY-MM-DD] confirm | {th} | user: {choice}
```

**ห้ามใส่ skipped count** ใน ingest line — format กำหนดแค่ `new` และ `matched`
`skipped_count` คำนวณได้แต่ไม่เขียนลง log

---

## JSON Output Contract (Stage 2 สุดท้าย)

```json
[
  {
    "th": "...",
    "cn": "... | null",
    "entity_type": "CAPS_TYPE",
    "status": "matched | new | skipped",
    "context_sentence": "..."
  }
]
```

- **ทุก candidate ต้องอยู่ใน JSON** รวม matched และ skipped — ไม่ใช่แค่ new
- เรียงลำดับ: `entity_type` A-Z ก่อน, แล้ว `th` A-Z
- Raw JSON เท่านั้น — ห้ามมี markdown fence หรือ preamble
- `null` เมื่อ language form ไม่มั่นใจและ confidence ไม่ high

---

## Source Encoding — ตรวจก่อน ingest ทุกครั้ง

ไฟล์จาก Windows (NE_Example/) มักไม่ใช่ UTF-8 — `_read()` อ่านเป็น UTF-8 ตรงๆ จะได้ garbage หรือ error

### ลำดับตรวจสอบ

```bash
# 1. ตรวจ encoding ก่อนเสมอ
file "/mnt/c/Users/.../file.txt"

# 2. แปลงถ้าจำเป็น
iconv -f UTF-16LE -t UTF-8 "source.txt" > "/tmp/ingest_utf8.txt"

# 3. ส่ง path ของไฟล์ที่แปลงแล้วเข้า NERExtractionFlow
```

### ตาราง encoding ที่พบบ่อย

| `file` output | Encoding | คำสั่ง iconv |
|---------------|----------|--------------|
| `Unicode text, UTF-16, little-endian` | UTF-16 LE | `-f UTF-16LE` |
| `ISO-8859 text` | TIS-620 (Thai) | `-f TIS-620` |
| `CJK text` | GBK (Chinese) | `-f GBK` |
| `UTF-8 Unicode text` | UTF-8 | อ่านตรงได้เลย |

### Pitfalls encoding

- **BOM:** UTF-16 จาก Windows มี BOM (`\uFEFF`) — `iconv` ลบให้อัตโนมัติ
- **CRLF:** ยังคงอยู่หลัง `iconv` — ใช้ `dos2unix` ถ้า cosmetic issue
- **`read_file` flag binary:** เพราะเห็น null byte ของ UTF-16 — ต้อง convert ก่อนเสมอ
- **Mixed encoding:** ไฟล์บางตัวมี GBK + TIS-620 ในไฟล์เดียว → flag `confidence: low`

---

## Entity Classification Rules

### Journal / Publishing Body

| บริบท | Classify As | เหตุผล |
|--------|-------------|--------|
| `《体育与科学》作为权威学术期刊` (มี 《》, อ้างถึงตัวงาน) | **WORK_OF_ART** | อ้างถึง creative work ที่มีชื่อเฉพาะ |
| `Journal of Sports Research ตีพิมพ์บทความ` (publishing institution) | **ORG** | อ้างถึงองค์กรที่ผลิตงาน |

กฎ: 《》 marks → WORK_OF_ART / "ตีพิมพ์", "รายงาน", "เป็นแพลตฟอร์ม" → ORG

### Brand Product vs Technical Concept

| Candidate | Classify As | เหตุผล |
|-----------|-------------|--------|
| `Nike Vaporfly` | **PRODUCT** | มี brand name + product series |
| `VAR (Video Assistant Referee)` | **PRODUCT** | named technology system เฉพาะ |
| `智能穿戴设备 / อุปกรณ์สวมใส่อัจฉริยะ` | **TECHNICAL_TERM** (IT Domain) | category/concept ไม่มี brand |
| `碳板技术 / เทคโนโลยีแผ่นคาร์บอน` | **TECHNICAL_TERM** (Engineering Domain) | materials concept |

กฎ: brand name + model → PRODUCT / หมวดหมู่/concept ไม่มี brand → TECHNICAL_TERM

### Sports Analytics Metrics

Performance metrics และ statistical measures → **TECHNICAL_TERM (IT Domain)**
ไม่ใช่ Engineering Domain แม้จะดูเป็นตัวเลข:

- `真实命中率 / อัตราการทำประตูที่แท้จริง` → IT Domain (data analytics)
- `每回合得分 / แต้มต่อการครองบอล` → IT Domain (data analytics)

### Recurring Policy vs One-time Event

- `体育中考` (PE exam ที่กำหนดโดยรัฐ) → **LAW** (binding regulation, recurring)
- ไม่ใช่ EVENT (EVENT = one-time หรือ named occurrence เฉพาะครั้ง)

### TECHNICAL_TERM Domain Split — Wearable Example

entity เดียวกันอาจถูก split เป็น 2 entries คนละ domain ตาม context เอกสาร:

| Chinese | Thai | Domain | เหตุผล |
|---------|------|--------|--------|
| 智能穿戴设备 | อุปกรณ์สวมใส่อัจฉริยะ | IT Domain | context sports-tech-IT |
| 可穿戴设备 | อุปกรณ์สวมใส่ได้ | Healthcare Domain | context injury-prevention-medicine |

ทั้งสองเป็น entity แยกกันและต้อง cross-reference กัน

---

## Cross-Reference Wiring Patterns

Wire cross-references ที่ **entity creation time** เสมอ — ไม่ใช่ follow-up pass

### Pattern ที่พบบ่อยในเอกสาร Sports / Tech

| Pattern | ทิศทาง | ตัวอย่าง |
|---------|--------|---------|
| City ↔ Event (host city) | bidirectional | `GPE/หางโจว` ↔ `EVENT/เอเชียนเกมส์หางโจว2023` |
| City ↔ Institution | bidirectional | `GPE/เซี่ยงไฮ้` ↔ `ORG/มหาวิทยาลัยกีฬาเซี่ยงไฮ้` |
| Parent ORG ↔ Subunit ORG | bidirectional | `ORG/มหาวิทยาลัยกีฬาเซี่ยงไฮ้` ↔ `ORG/ศูนย์วิจัยกีฬาอิเล็กทรอนิกส์ฯ` |
| Product ↔ Manufacturer | bidirectional | `PRODUCT/Nike_Vaporfly` ↔ `ORG/ไนกี้` |
| Manufacturer ↔ R&D Lab | bidirectional | `ORG/ไนกี้` ↔ `ORG/ห้องปฏิบัติการวิจัยด้านกีฬาของไนกี้` |
| Product ↔ Event (featuring) | bidirectional | `PRODUCT/League_of_Legends` ↔ `EVENT/LoL World Championship` |
| Generic Event ↔ Specific Instance | bidirectional | `EVENT/เอเชียนเกมส์` ↔ `EVENT/เอเชียนเกมส์หางโจว2023` |
| Team ↔ Event (participant) | bidirectional | `ORG/EDG` ↔ `EVENT/LoL World Championship` |

### รูปแบบ Cross-references ใน entity file

```markdown
## Cross-references
- [[Entity_type/GPE/หางโจว]]              <!-- host city -->
- [[Entity_type/EVENT/เอเชียนเกมส์]]      <!-- parent event -->
- [[Entity_type/DATE/ค.ศ.2023]]
```

### Triangle pattern (Product + Manufacturer + Lab)

เมื่อมีทั้ง 3 ใน batch เดียวกัน ต้อง wire ทุก edge:

```
PRODUCT/Nike_Vaporfly  ↔  ORG/ไนกี้  ↔  ORG/ห้องปฏิบัติการวิจัยด้านกีฬาของไนกี้
```

---

## Pitfalls

### `WriteEntityTool._run()` vs `.write()`
ห้ามเรียก `_run()` ตรงจาก Python — CrewAI wrap argument อาจเสีย
เรียก `.write(entity_name, content, mode)` เสมอเมื่อ call จาก code โดยตรง

### matched แต่ไม่มี matched_evidence
Code จะ auto-downgrade เป็น `no_match` — agent ต้อง copy บรรทัดจาก index.md จริงมาใส่เสมอ
ห้าม claim matched จากความรู้เดิมโดยไม่อ่าน index

### TECHNICAL_TERM count = 0 เสมอ
สาเหตุ: นับจาก root folder แทน sub-folder
แก้: ใช้ `_count_entities_in_type("TECHNICAL_TERM")` ซึ่งวนนับจาก `_TECH_TERM_DOMAINS`

### ลำดับ update corpus files
ต้องทำหลัง `save_json` เสมอ — ถ้า update ก่อน JSON output จะแสดงตัวเลขจาก session ก่อน

### Reclassify loop ไม่ใช้ circular Flow edge
CrewAI Flows ไม่รองรับ — ใช้ plain `while` loop ใน `@start` method เดียว
ห้ามพยายามใช้ `@listen` วนกลับมายัง `@start`

### `WriteEntityTool` path สำหรับ TECHNICAL_TERM
`WriteEntityTool(entity_type="TECHNICAL_TERM")` เขียนไปที่ `Entity_type/TECHNICAL_TERM/{name}.md`
ซึ่ง**ผิด** — entity ควรอยู่ใน sub-folder domain
แก้: ใช้ `WriteEntityTool(entity_type="TECHNICAL_TERM/{domain}")` หรือ patch path ก่อนเขียน

---

## Format Contracts (summary)

| Item | Value |
|------|-------|
| Obsidian cross-reference | `[[path/to/page]]` |
| Date fields | ISO `YYYY-MM-DD` |
| Confidence values | `high` \| `medium` \| `low` |
| Domain field (non-TECHNICAL_TERM) | `null` |
| Log ingest line | `## [YYYY-MM-DD] ingest \| <doc> \| <N> new, <N> matched` |
| Log confirm line | `## [YYYY-MM-DD] confirm \| <th> \| user: <choice>` |
| TECHNICAL_TERM domains | `Engineering Domain` \| `Finance Domain` \| `Healthcare Domain` \| `IT Domain` |
| MAX_HOP | `2` |
| Fuzzy match threshold | `≥ 80%` |
