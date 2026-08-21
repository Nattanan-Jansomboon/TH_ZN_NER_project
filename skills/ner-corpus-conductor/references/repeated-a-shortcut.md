# Repeated-[A] Shortcut UI Template

Use this when the user has answered [A] for 3+ consecutive entities in a single batch. Replace the standard 3-option prompt with this 4-option version.

```
┌──────────────────────────────────────────────────────────────┐
│  ⚠️  (4 of 8) พบ Entity ใหม่ — กรุณายืนยัน                   │
│                                                              │
│  🔤 ภาษาไทย  : <thai form>                                   │
│  🈶 ภาษาจีน  : <chinese form>                                │
│  🏷️  ประเภท   : <entity_type>                                │
│                                                              │
│  📄 ประโยคบริบท:                                             │
│  "<context sentence>"                                        │
│  (จากเอกสาร: <source>)                                       │
│                                                              │
│  คุณตอบ [A] มา 3 ครั้งติด — ต้องการยืนยันทั้งหมดที่เหลือไหม?  │
│                                                              │
│  [A] ยืนยันตามนี้                                            │
│  [S] ยืนยันทั้งหมดที่เหลือทั้งหมด                              │
│      (confirm all remaining as-is)                           │
│  [B] แก้ไขก่อนบันทึก                                         │
│  [C] ข้ามรายการนี้ — ไม่บันทึก                               │
└──────────────────────────────────────────────────────────────┘
```

## Trigger condition (copy this checklist)

```
After user answers [A]:
  consecutive_as += 1
  if consecutive_as >= 3:
     MUST offer [S] on next entity
  if answer == [B] or [C]:
     consecutive_as = 0  # reset
```

## After [S] is chosen

- Auto-confirm all remaining unmatched entities with the same frontmatter template.
- Skip the per-entity loop entirely — go straight to STEP 5 (write & update).
- In the log, note: "Remaining N entities confirmed via [S] shortcut."
- In the JSON output, mark them all as `"status": "new"`.