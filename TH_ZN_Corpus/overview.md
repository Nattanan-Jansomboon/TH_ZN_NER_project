# Overview — TH_ZN NER Corpus

## จุดประสงค์
TH_ZN NER Corpus เป็นคลังความรู้สำหรับงาน Named Entity Recognition ภาษาไทยและภาษาจีน Simplified ใช้เป็น persistent memory ให้ Agent สกัด entity, ตรวจ entity เดิม, สร้าง entity ใหม่, และตอบคำถามจาก corpus ได้อย่างสม่ำเสมอ

ไฟล์นี้เป็นคู่มือการอ่านและดูแล corpus ระดับ root โดยเน้น convention, schema, workflow และหลักการจำแนก ไม่ใช้เป็น dashboard สถิติ เพราะข้อมูลสถิติที่เปลี่ยนบ่อยอยู่ใน [[summary]]

## บทบาทของไฟล์ root
| ไฟล์ | บทบาท |
|------|-------|
| [[overview]] | คู่มือ corpus, schema, convention, workflow และหลักการ classify |
| [[index]] | สารบัญและแผนที่ลิงก์ไปยัง entity type ทั้งหมด |
| [[summary]] | dashboard สถานะล่าสุด จำนวน entity และ coverage |
| [[log]] | บันทึกการเปลี่ยนแปลงแบบ append-only |

## โครงสร้างหลัก
```text
TH_ZN_Corpus/
├── index.md
├── overview.md
├── summary.md
├── log.md
└── Entity_type/
    ├── CARDINAL/
    ├── DATE/
    ├── EVENT/
    ├── FAC/
    ├── GPE/
    ├── LANGUAGE/
    ├── LAW/
    ├── LOC/
    ├── MONEY/
    ├── NORP/
    ├── ORDINAL/
    ├── ORG/
    ├── PERCENT/
    ├── PERSON/
    ├── PRODUCT/
    ├── QUANTITY/
    ├── TECHNICAL_TERM/
    ├── TIME/
    └── WORK_OF_ART/
```

## Entity Page Schema
ทุก entity page ต้องมี YAML frontmatter ตามรูปแบบนี้

```yaml
---
title: <ชื่อ canonical ภาษาไทย>
th: <Thai form>
cn: <Chinese Simplified form>
entity_type: <TYPE>
domain: <TECHNICAL_TERM domain หรือ null>
aliases: [<ชื่อย่อ>, <ชื่อแปรผัน>, <pinyin/English ถ้ามี>]
source_count: <จำนวนเอกสารที่พบ>
first_seen: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [<entity_type>, <domain ถ้ามี>, thai, chinese]
confidence: high | medium | low
---
```

## Naming Convention
- หน้า entity ทั่วไปเก็บที่ `Entity_type/<TYPE>/<entity_name>.md`
- หน้า TECHNICAL_TERM เก็บที่ `Entity_type/TECHNICAL_TERM/<Domain>/<entity_name>.md`
- ใช้ชื่อไฟล์จาก canonical Thai form เมื่อมีภาษาไทยที่เหมาะสม
- ถ้าไม่มีภาษาไทยที่มั่นใจ ใช้ชื่อ canonical จากภาษาที่มั่นใจที่สุดและตั้งอีกภาษาหนึ่งเป็น `null`
- ใช้ Obsidian wiki links เช่น `[[Entity_type/ORG/ธนาคารแห่งประเทศไทย]]`

## Workflow สำหรับ Agent
1. อ่าน [[summary]] เพื่อดูสถานะและ coverage ล่าสุด
2. อ่าน [[index]] เพื่อหา path ของ entity type
3. classify candidate entity เป็น type เดียวก่อน โดยบันทึก type ที่อาจสับสนเป็น cross-reference
4. อ่าน `Entity_type/<TYPE>/index.md` เพื่อหา entity เดิมใน type นั้น
5. ถ้าเจอ candidate ใกล้เคียง ให้เปิด entity page และ fuzzy match จาก `th`, `cn`, `aliases`, และบริบท
6. ถ้าไม่พบ ให้ขอ user ยืนยันก่อนสร้าง entity ใหม่
7. หลังสร้างหรือแก้ entity ต้องอัปเดต index ที่เกี่ยวข้อง, [[summary]], และ [[log]]

## หลักการจำแนกที่มักสับสน
| กลุ่มที่สับสน | หลักตัดสิน |
|---------------|-------------|
| GPE / LOC / FAC | GPE คือหน่วยปกครอง, LOC คือภูมิประเทศธรรมชาติหรือพื้นที่ภูมิศาสตร์, FAC คือสิ่งก่อสร้างหรือสถานที่ที่มนุษย์สร้าง |
| ORG / FAC | ORG คือหน่วยงานที่ทำกริยาได้ เช่น ประกาศ ลงทุน ผลิต ส่วน FAC คืออาคารหรือสถานที่ตั้ง |
| ORG / PRODUCT | ORG คือบริษัทหรือหน่วยงาน ส่วน PRODUCT คือสินค้า แอป แพลตฟอร์ม หรือบริการเฉพาะ |
| CARDINAL / ORDINAL | CARDINAL คือจำนวนนับทั่วไป ส่วน ORDINAL คือลำดับ เช่น ครั้งที่สาม, อันดับหนึ่ง |
| CARDINAL / QUANTITY | CARDINAL ไม่มีหน่วยวัด ส่วน QUANTITY มีหน่วยวัดที่ไม่ใช่เงิน |
| MONEY / QUANTITY | MONEY มีสกุลเงินหรือมูลค่าทางการเงิน ส่วน QUANTITY เป็นปริมาณกายภาพ |
| DATE / TIME | DATE คือวัน เดือน ปี หรือช่วงปฏิทิน ส่วน TIME คือเวลาย่อยกว่าวัน |
| EVENT / WORK_OF_ART | EVENT คือเหตุการณ์หรืองานที่เกิดขึ้น ส่วน WORK_OF_ART คือผลงานสร้างสรรค์ เช่น หนังสือ เพลง ภาพยนตร์ |
| LANGUAGE / NORP | LANGUAGE คือชื่อภาษา ส่วน NORP คือสัญชาติ ศาสนา หรือกลุ่มการเมือง |

## Confidence Guideline
- `high`: มีรูปไทย/จีนชัดเจนและบริบทสนับสนุน type โดยตรง
- `medium`: type ชัดเจนแต่ชื่อแปลหรือ alias อาจมีหลายรูป
- `low`: inference ข้ามภาษาไม่มั่นใจ หรือบริบทไม่พอ ต้องรอ user ยืนยันเพิ่ม

## กฎสำคัญ
- เก็บประโยคบริบทต้นฉบับทุกครั้ง
- ไม่ลบข้อมูลเดิมเมื่อพบความขัดแย้ง ให้เพิ่มหมายเหตุและบันทึกหลักฐานทั้งสองฝั่ง
- ใช้ canonical form จาก corpus เมื่อ fuzzy match ผ่าน
- TECHNICAL_TERM ต้องมี domain เสมอ
- คำอธิบายหลักเขียนเป็นภาษาไทย ยกเว้น technical term ที่ไม่มีคำแปลเหมาะสม
