# WORK_OF_ART Overview

## Description
WORK_OF_ART คือชื่อเฉพาะของผลงานสร้างสรรค์ เช่น หนังสือ วรรณกรรม เพลง ภาพยนตร์ ละคร ภาพวาด งานศิลปะ หรือบทประพันธ์ Entity นี้เน้นตัวผลงาน ไม่ใช่ผู้แต่งหรือเหตุการณ์

## เกณฑ์การจำแนก
- ใช้ WORK_OF_ART กับชื่อผลงานสร้างสรรค์ที่มีชื่อเฉพาะ
- ถ้าหมายถึงผู้แต่ง นักร้อง หรือศิลปิน ให้ใช้ PERSON
- ถ้าหมายถึงบริษัทผู้ผลิตหรือสำนักพิมพ์ ให้ใช้ ORG
- ถ้าหมายถึงงานเทศกาลหรือรอบฉายเฉพาะ ให้พิจารณา EVENT

## Case ตัวอย่าง
ประโยค: "นักเรียนอ่านรามเกียรติ์เพื่อศึกษาวรรณคดีไทย"

Entity: "รามเกียรติ์"  
Type: WORK_OF_ART  
เหตุผล: คำนี้เป็นชื่อวรรณคดี/บทประพันธ์ ไม่ใช่ชื่อบุคคลหรือเหตุการณ์ จึงเป็น WORK_OF_ART

## Related Types
- [[Entity_type/PERSON/index]]
- [[Entity_type/ORG/index]]
- [[Entity_type/EVENT/index]]

### 2026-08-19 — ingest session
- `วารสาร Tourism Tribune` (旅游学刊) → no_match_confirm

### 2026-08-20 — ingest session
- `ไม้` (cn=null) → manual_review_confirm

### 2026-08-20 — ingest session
- `Journal of Financial Research` (金融研究) → no_match_confirm
