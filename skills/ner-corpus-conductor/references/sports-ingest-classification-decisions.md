# Sports-domain ingest: classification decisions

Decisions made during the 2026-07-10 batch ingest (files 403, 407, 409, 412, 414), 
covering e-sports, sports data analytics, running shoe tech, sports medicine, 
and youth sports education.

## Academic journals as ORG (not WORK_OF_ART)

When an academic journal appears as the **subject of the sentence** — publishing 
articles, cited as a source, described as a platform — classify as **ORG**:

- "Journal of Sports Research ก็ได้ตีพิมพ์บทความ" → ORG (the publishing institution)
- "《中国运动医学杂志》作为国内权威的学术期刊" → WORK_OF_ART (proper handling)

Rule of thumb: if the journal has an editorial board, ISSN, or volume/issue structure,
it's ORG. If referenced as a creative work (title, author, content), it's WORK_OF_ART.

**Edge case — user correction history:**
- 409.zh-th.txt: initially classified `Journal of Sports Research` as WORK_OF_ART,
  user corrected → "ในบริบทนี้ Journal of Sports Research เป็น ORG"
- 414.zh-th.txt: `Journal of Physical Education / 《体育学刊》` — user skipped entirely

## Sports policy/exam system as LAW

`体育中考` (PE exam for high school entrance) — classified as LAW because it is a 
government-mandated examination policy with binding rules, similar to a regulation.
Not an EVENT (it is recurring, not a one-time occurrence) and not an ORG.

## Wearable device domain split

| Chinese | Thai | Domain | Rationale |
|---------|------|--------|-----------|
| 智能穿戴设备 | อุปกรณ์สวมใส่อัจฉริยะ | IT Domain (existing) | Focus on smart/connected tech |
| 可穿戴设备 | อุปกรณ์สวมใส่ได้ (wearable devices) | Healthcare Domain (new) | Focus on physiological monitoring |

Both filed as separate TECHNICAL_TERM entities with cross-references. The domain 
choice follows the document context: 智能穿戴设备 appeared in a sports-tech-IT 
context, 可穿戴设备 appeared in a sports-injury-prevention-and-medicine context.

## Entity types per document

| File | Topic | ORG | PRODUCT | TECH | Other | Skipped |
|------|-------|-----|---------|------|-------|---------|
| 403 | e-sports | 4 | 1 | 1 | 3 EVENT, 2 GPE, 1 DATE, 1 WORK | 0 |
| 407 | sports analytics | 3 | 1 | 1 | 0 | 3 (TECH, ORD) |
| 409 | running shoe tech | 3 | 1 | 1 | 0 | 1 (ORG) |
| 412 | injury prevention | 2 | 0 | 4 | 1 WORK | 1 (TECH) |
| 414 | youth sports ed | 1 | 0 | 0 | 1 LAW | 1 (WORK) |