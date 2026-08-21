# PERCENT Overview

## Description
PERCENT คือค่าร้อยละหรือเปอร์เซ็นต์ Entity นี้ใช้กับตัวเลขที่มีเครื่องหมาย %, คำว่า เปอร์เซ็นต์, ร้อยละ หรือรูปภาษาจีนอย่าง 百分之

## เกณฑ์การจำแนก
- ใช้ PERCENT เมื่อจำนวนแสดงสัดส่วนต่อ 100
- ถ้าเป็นจำนวนธรรมดาไม่มีสัญญาณร้อยละ ให้ใช้ CARDINAL
- ถ้าเป็นมูลค่าเงิน ให้ใช้ MONEY
- ถ้าเป็นอัตราดอกเบี้ยหรือผลตอบแทนเป็นเปอร์เซ็นต์ ยังคงเป็น PERCENT และอาจ cross-reference TECHNICAL_TERM Finance

## Case ตัวอย่าง
ประโยค: "ยอดส่งออกเพิ่มขึ้นร้อยละ 30 เมื่อเทียบกับปีก่อน"

Entity: "ร้อยละ 30"  
Type: PERCENT  
เหตุผล: คำนี้แสดงสัดส่วนต่อ 100 อย่างชัดเจนด้วยคำว่า "ร้อยละ" จึงเป็น PERCENT

## Related Types
- [[Entity_type/CARDINAL/index]]
- [[Entity_type/MONEY/index]]
- [[Entity_type/TECHNICAL_TERM/Finance Domain/index]]
