# Log

## [2026-07-13] ingest | 418.zh-th.txt | 10 new, 1 matched
- แหล่ง: sports stars social media influence / อิทธิพลนักกีฬาบนสื่อสังคมออนไลน์ bilingual article
- รายละเอียด: PRODUCT(3), PERSON(1), EVENT(1), WORK_OF_ART(1), TECHNICAL_TERM(3), TECHNICAL_TERM-IT(1)
- Matched: มหาวิทยาลัยกีฬาปักกิ่ง/北京体育大学 (auto-matched, existing ORG)
- แหล่ง: sports spirit & youth character education / จิตวิญญาณกีฬากับการพัฒนาคุณลักษณะเยาวชน bilingual article
- รายละเอียด: ORG(1), LAW(1)
- ข้าม 1 entity: Journal of Physical Education / 《体育学刊》 (WORK_OF_ART) — user [C] skip

## [2026-07-10] ingest | 412.zh-th.txt | 7 new, 1 matched
- แหล่ง: sports injury prevention technology / เทคโนโลยีป้องกันการบาดเจ็บ bilingual article
- รายละเอียด: ORG(2), TECHNICAL_TERM(4), WORK_OF_ART(1)
- Matched: 人工智能/ปัญญาประดิษฐ์ (auto-matched, existing corpus)
- ข้าม 1 entity: 智能护具/อุปกรณ์ป้องกันอัจฉริยะ — user [C] skip

## [2026-07-10] ingest | 409.zh-th.txt | 5 new, 0 matched
- แหล่ง: high-tech running shoes / รองเท้าวิ่งไฮเทค bilingual article
- รายละเอียด: ORG(3), PRODUCT(1), TECHNICAL_TERM(1)
- ข้าม 1 entity: Journal of Sports Research (ORG) — user [B]→[C] skip

## [2026-07-10] ingest | 407.zh-th.txt | 5 new, 0 matched
- แหล่ง: sports data analytics podcast dialogue (bilingual ZH-TH)
- รายละเอียด: ORG(3), PRODUCT(1), TECHNICAL_TERM(1)
- ข้าม 3 entities: 真实命中率, 每回合得分 (TECHNICAL_TERM), 第四节 (ORDINAL) — user [C] skip

## [2026-07-10] ingest | 403.zh-th.txt | 15 new, 0 matched
- แหล่ง: e-sports / อีสปอร์ต bilingual article
- รายละเอียด: TECHNICAL_TERM(1), GPE(2), ORG(4), EVENT(3), PRODUCT(1), WORK_OF_ART(1), DATE(3)
- #4 แก้ไขจาก GPE(中国/จีน) → ORG(中国战队/ทีมจีน) ตาม user ยืนยัน

## [2026-06-22] update | entity descriptions | 24 updated, 0 new
- เพิ่ม `## Description` ให้ entity pages ทุกหน้า
- อัปเดต root index ให้จำนวน entity รวมตรงกับ corpus ปัจจุบัน

## [2026-06-22] ingest | user input — Messi is Better than Ronaldo | 2 new, 1 matched (สมเด็จพระนเรศวรมหาราจ)

## [2026-06-21] seed | mock_seed_corpus.md | 22 new, 0 matched
- สร้าง mock seed corpus ครบทุก entity type ตามโครงสร้างจริง
- เพิ่ม TECHNICAL_TERM ครบ 4 domains
- เติม root overview/index/summary และ entity type overview/index- 2026-07-13: Scout extraction for sentence "นายกของประเทศไทยตอนนี้คืออนุทิน" — candidates: ประเทศไทย (GPE), อนุทิน (PERSON). Filtered out "นายก" (title/position).

## ingest | text_20260806_115614 | 2 new, 0 matched, 0 skipped
- 2026-07-13: Scout/Manager — coarse-pass extraction จากพอดแคสต์ "พืชผลทางการเกษตรที่เรากินมาจากไหน?" สกัด candidate entities 28 รายการ (PERSON, GPE, PRODUCT, DATE, LOC, FAC, ORG, WORK_OF_ART, EVENT, TECHNICAL_TERM)

## ingest | 531.zh-th | 26 new, 0 matched, 1 skipped
- 2026-07-13: Scout/Manager — coarse-pass extraction on TCM text (中医的历史、理念与当代价值). Dispatched candidates for classification.

- 2026-07-13: Extracted TCM candidates (中医, 黄帝内经, 伤寒杂病论, 本草纲目, 整体观念, 辨证论治, 中药, 针灸, 推拿, 拔罐, 食疗, 气功, 阴阳, 经络, 穴位, 治未病, 中西医结合, 中华民族, 中国).

- 2026-07-13: TCM extraction complete — 21 candidates identified.

- 2026-07-13: Scout coarse-pass extraction on space tourism text — identified 14 candidates (ORG, PRODUCT, PERSON, DATE, TECHNICAL_TERM, CARDINAL). Dispatched for specialized classification.


## [2026-08-06] ingest | 37.zh-th | 13 new, 1 matched, 0 skipped
## [2026-08-06] confirm | เวอร์จิน กาแลกติก | user: no_match_confirm
## [2026-08-06] confirm | บลู ออริจิน | user: no_match_confirm
## [2026-08-06] confirm | ยานอวกาศยูนิตี้ | user: no_match_confirm
## [2026-08-06] confirm | จรวดนิว เชพเพิร์ด | user: no_match_confirm
## [2026-08-06] confirm | อวกาศยุคใหม่ | user: no_match_confirm
## [2026-08-06] confirm | ริชาร์ด แบรนสัน | user: no_match_confirm
## [2026-08-06] confirm | 6 คน | user: no_match_confirm
## [2026-08-06] confirm | การขึ้น-ลงแนวตั้ง | user: no_match_confirm
## [2026-08-06] confirm | ยานอวกาศที่นำกลับมาใช้ใหม่ได้ | user: no_match_confirm
## [2026-08-06] confirm | สมาคมส่งเสริมความปลอดภัยการบินอวกาศระหว่างประเทศ | user: no_match_confirm
## [2026-08-06] confirm | ชั้นโอโซน | user: no_match_confirm
## [2026-08-06] confirm | สิบปีข้างหน้า | user: no_match_confirm
## [2026-08-06] confirm | การบินแบบใต้วงโคจร | user: no_match_confirm

## [2026-08-19] ingest | 438.zh-th | 5 new, 1 matched
## [2026-08-19] confirm | วารสาร Tourism Tribune | user: no_match_confirm
## [2026-08-19] confirm | กรุงปักกิ่ง | user: no_match_confirm
## [2026-08-19] confirm | โอลิมปิกฤดูหนาวปักกิ่ง ค.ศ.2022 | user: no_match_confirm
## [2026-08-19] confirm | คณะการกีฬา นันทนาการ และการท่องเที่ยว มหาวิทยาลัยกีฬาปักกิ่ง | user: no_match_confirm
## [2026-08-19] confirm | การแข่งขันมาราธอน | user: no_match_confirm
- 2026-08-19: Scout coarse-pass extraction จากเอกสาร 438.zh-th (การดูแลผู้สูงอายุจีน) — สกัด candidate ~21 entity, dispatch ไป classify ละเอียด


## [2026-08-19] ingest | text_20260819_211623 | 2 new, 0 matched
## [2026-08-19] confirm | เนมอ | user: no_match_confirm
## [2026-08-19] confirm | marvel | user: no_match_confirm

## [2026-08-20] ingest | text_20260820_003604 | 0 new, 0 matched
## [2026-08-20] confirm | จินนี่ | user: no_match_skipped

## [2026-08-20] ingest | text_20260820_005329 | 2 new, 0 matched
## [2026-08-20] confirm | ปลาเก๋า | user: manual_review_confirm
## [2026-08-20] confirm | ไม้ | user: manual_review_confirm

## [2026-08-20] ingest | text_20260820_005945 | 0 new, 0 matched
## [2026-08-20] confirm | ต้นน้ำ | user: no_match_skipped
## [2026-08-20] confirm | ก้อนเมฆ | user: no_match_skipped

## [2026-08-20] ingest | text_20260820_011054 | 0 new, 0 matched
## [2026-08-20] confirm | ตง | user: no_match_skipped
## [2026-08-20] confirm | ฝน | user: no_match_skipped

## [2026-08-20] ingest | text_20260820_011456 | 0 new, 0 matched

## [2026-08-20] ingest | text_20260820_012546 | 0 new, 0 matched
## [2026-08-20] confirm | น้ำ | user: no_match_skipped
## [2026-08-20] confirm | เสือ | user: no_match_skipped

## [2026-08-20] ingest | 330.zh-th | 15 new, 0 matched
## [2026-08-20] confirm | การเข้าถึงบริการทางการเงินอย่างทั่วถึง | user: no_match_confirm
## [2026-08-20] confirm | การเข้าถึงบริการทางการเงินแบบดิจิทัลอย่างทั่วถึง | user: no_match_confirm
## [2026-08-20] confirm | ธนาคาร MYBank | user: no_match_confirm
## [2026-08-20] confirm | ธนาคาร WeBank | user: no_match_confirm
## [2026-08-20] confirm | ธนาคารอินเทอร์เน็ต | user: no_match_confirm
## [2026-08-20] confirm | ข้อมูลขนาดใหญ่ | user: no_match_confirm
## [2026-08-20] confirm | ปัญญาประดิษฐ์ | user: no_match_confirm
## [2026-08-20] confirm | มหาวิทยาลัยประชาชนแห่งประเทศจีน | user: no_match_confirm
## [2026-08-20] confirm | สถาบันวิจัยการเงินอย่างทั่วถึงจีน | user: no_match_confirm
## [2026-08-20] confirm | Journal of Financial Research | user: no_match_confirm
## [2026-08-20] confirm | การชำระเงินดิจิทัล | user: no_match_confirm
## [2026-08-20] confirm | การเข้าถึงบริการทางการเงินอย่างทั่วถึง | user: no_match_confirm
## [2026-08-20] confirm | การสแกนคิวอาร์โค้ดผ่านสมาร์ทโฟน | user: no_match_confirm
## [2026-08-20] confirm | ความปลอดภัยของข้อมูล | user: no_match_confirm
## [2026-08-20] confirm | ช่องว่างดิจิทัล | user: no_match_confirm

## [2026-08-20] ingest | 317.zh-th | 0 new, 0 matched
## [2026-08-20] confirm | ธนาคารซิงเย่ (Industrial Bank) | user: no_match_skipped
## [2026-08-20] confirm | Journal of Financial Research | user: manual_review_skipped
## [2026-08-20] confirm | คณะกรรมการผู้เชี่ยวชาญด้านการเงินสีเขียวของสมาคมการเงินจีน | user: no_match_skipped
## [2026-08-20] confirm | การจัดอันดับ MSCI ESG | user: no_match_skipped
## [2026-08-20] confirm | จีน | user: no_match_skipped
## [2026-08-20] confirm | พันธบัตรคาร์บอนเป็นศูนย์ (Carbon Neutral Bonds) | user: no_match_skipped
## [2026-08-20] confirm | การลงทุนด้าน ESG | user: no_match_skipped
## [2026-08-20] confirm | สินเชื่อสีเขียว | user: no_match_skipped
## [2026-08-20] confirm | พันธบัตรสีเขียว | user: no_match_skipped
## [2026-08-20] confirm | กองทุนสีเขียว | user: no_match_skipped
## [2026-08-20] confirm | การเงินสีเขียว | user: no_match_skipped
## [2026-08-20] confirm | คาร์บอนคู่ (Dual Carbon) | user: no_match_skipped
