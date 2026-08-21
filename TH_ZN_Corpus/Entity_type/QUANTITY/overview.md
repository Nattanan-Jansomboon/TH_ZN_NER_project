# QUANTITY Overview

## Description
QUANTITY คือปริมาณที่มีหน่วยวัดซึ่งไม่ใช่เงิน เช่น น้ำหนัก ระยะทาง ปริมาตร อุณหภูมิ ความเร็ว หรือจำนวนพร้อมหน่วยนับที่มีความหมายเชิงปริมาณ

## เกณฑ์การจำแนก
- ใช้ QUANTITY เมื่อมีจำนวนพร้อมหน่วยวัด เช่น กิโลกรัม เมตร ลิตร องศา
- ถ้าหน่วยเป็นสกุลเงิน ให้ใช้ MONEY
- ถ้าไม่มีหน่วย ให้ใช้ CARDINAL
- ถ้าหน่วยเป็นเปอร์เซ็นต์ ให้ใช้ PERCENT

## Case ตัวอย่าง
ประโยค: "ตัวอย่างน้ำหนัก 5 กิโลกรัมถูกส่งไปตรวจในห้องปฏิบัติการ"

Entity: "5 กิโลกรัม"  
Type: QUANTITY  
เหตุผล: คำนี้มีจำนวนพร้อมหน่วยวัดน้ำหนัก จึงเป็น QUANTITY ไม่ใช่ CARDINAL หรือ MONEY

## Related Types
- [[Entity_type/CARDINAL/index]]
- [[Entity_type/MONEY/index]]
- [[Entity_type/PERCENT/index]]

### 2026-08-06 — ingest session
- `6 คน` (六人) → no_match_confirm
