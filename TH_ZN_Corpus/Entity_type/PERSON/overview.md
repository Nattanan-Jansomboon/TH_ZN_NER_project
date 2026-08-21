# PERSON Overview

## Description
PERSON คือชื่อเฉพาะของบุคคล ทั้งบุคคลจริง บุคคลสำคัญทางประวัติศาสตร์ หรือบุคคลในข่าว Entity นี้เน้นตัวบุคคล ไม่ใช่ตำแหน่ง องค์กร หรือกลุ่มคน

## เกณฑ์การจำแนก
- ใช้ PERSON เมื่อเป็นชื่อคนเฉพาะเจาะจง
- ถ้าเป็นตำแหน่งอย่าง "นายกรัฐมนตรี" โดยไม่มีชื่อ อาจไม่บันทึกเป็น PERSON
- ถ้าเป็นราชวงศ์หรือกลุ่มคน ให้พิจารณา NORP หรือ ORG ตามบริบท
- ถ้าเป็นตัวละครในผลงาน อาจใช้ PERSON หากระบบต้องการชื่อบุคคล แต่ควร cross-reference WORK_OF_ART

## Case ตัวอย่าง
ประโยค: "สมเด็จพระนเรศวรมหาราชทรงมีบทบาทสำคัญในประวัติศาสตร์ไทย"

Entity: "สมเด็จพระนเรศวรมหาราช"  
Type: PERSON  
เหตุผล: คำนี้เป็นพระนามของบุคคลทางประวัติศาสตร์เฉพาะเจาะจง ไม่ใช่ชื่อราชวงศ์หรือเหตุการณ์ จึงเป็น PERSON

## Related Types
- [[Entity_type/NORP/index]]
- [[Entity_type/ORG/index]]
- [[Entity_type/WORK_OF_ART/index]]

### 2026-08-06 — ingest session
- `ริชาร์ด แบรนสัน` (布兰森) → no_match_confirm

### 2026-08-19 — ingest session
- `เนมอ` (cn=null) → no_match_confirm

### 2026-08-20 — ingest session
- `ปลาเก๋า` (cn=null) → manual_review_confirm
