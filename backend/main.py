"""
FastAPI backend สำหรับ Multi-agent NER Corpus Flow
====================================================

Endpoints:
  POST /ingest              -> รับ raw_text หรือไฟล์ (.txt/.pdf/.docx) -> สร้าง job แล้วรันเบื้องหลัง
  GET  /jobs/{job_id}        -> เช็คสถานะ job (running / pending_confirmation / done / error)
  GET  /jobs/{job_id}/pending -> ดึงรายการ candidate ที่รอ user ยืนยัน
  POST /jobs/{job_id}/confirm -> ส่งผลการยืนยัน (confirm/edit/skip) ต่อ candidate กลับไป -> resume การเขียนไฟล์
  GET  /jobs/{job_id}/result  -> ดึงผลลัพธ์ JSON สุดท้าย (พร้อม path ไฟล์ที่ save ไว้)

รัน:
  pip install fastapi uvicorn python-multipart pypdf python-docx crewai
  uvicorn main:app --reload --port 8000
"""

import os
import io
import json
import uuid
from datetime import datetime
from typing import Optional, List, Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Encoding detection helper
# ---------------------------------------------------------------------------

def _detect_encoding(raw: bytes) -> Optional[str]:
    """
    ลองใช้ chardet/charset-normalizer ตรวจ encoding ของ bytes
    ถ้าไม่ได้ติดตั้งไว้จะ return None แล้ว fallback chain ข้างล่างจัดการต่อ
    pip install chardet   # หรือ charset-normalizer ก็ได้
    """
    try:
        import chardet
        result = chardet.detect(raw)
        enc = result.get("encoding")
        confidence = result.get("confidence", 0)
        # confidence < 0.7 มักผิด โดยเฉพาะ TIS-620 vs CP874 — ปล่อยให้ fallback chain เลือกแทน
        return enc if enc and confidence >= 0.7 else None
    except ImportError:
        pass
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(raw).best()
        return str(best.encoding) if best else None
    except ImportError:
        return None

from ner_flow_api import (
    run_extraction_and_specialize,   # phase 0-2: scout -> specialize -> reclassify
    resume_write_and_finalize,       # phase 3-5: apply user decisions -> write -> save json
    JSON_OUTPUT_DIR,
)

app = FastAPI(title="NER Corpus Ingest API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev เท่านั้น — เวลาขึ้น production ให้ระบุ origin ของหน้าเว็บจริง
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- serve index.html ที่ GET / ---
_STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
_INDEX_HTML  = os.path.join(_STATIC_DIR, "index.html")

@app.get("/", include_in_schema=False)
async def serve_index():
    if not os.path.exists(_INDEX_HTML):
        return {"message": "NER Corpus Ingest API", "docs": "/docs"}
    return FileResponse(_INDEX_HTML, media_type="text/html")

# --- In-memory job store (dev เท่านั้น — production ควรใช้ Redis/DB) ---
JOBS: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class JobStatus(BaseModel):
    job_id: str
    status: Literal["running", "pending_confirmation", "done", "error"]
    error: Optional[str] = None


class PendingCandidate(BaseModel):
    candidate_id: str
    th: str
    cn: Optional[str] = None
    entity_type: str
    context_sentence: str


class ConfirmDecision(BaseModel):
    candidate_id: str
    choice: Literal["confirm", "edit", "skip"]
    edited_th: Optional[str] = None
    edited_type: Optional[str] = None

    def to_flow_decision(self):
        """แปลงเป็น ConfirmDecision format ของ ner_flow_api (ไม่มี candidate_id)"""
        from ner_flow_api import ConfirmDecision as FlowDecision
        return FlowDecision(
            choice=self.choice,
            edited_th=self.edited_th,
            edited_type=self.edited_type,
        )


class ConfirmPayload(BaseModel):
    decisions: List[ConfirmDecision]


# ---------------------------------------------------------------------------
# Helper: แปลงไฟล์อัปโหลดเป็น raw_text
# ---------------------------------------------------------------------------

def extract_text_from_upload(filename: str, content: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        # ตรวจ encoding จริงก่อน decode — ไฟล์ภาษาไทยมักบันทึกเป็น TIS-620 / CP874 / UTF-8-BOM
        # errors="ignore" ของเดิมทำให้อักขระที่ decode ไม่ตรง encoding ถูกทิ้งเงียบๆ โดยไม่แจ้งเตือน
        detected = _detect_encoding(content)
        for enc in [detected, "utf-8-sig", "tis-620", "cp874", "utf-8", "latin-1"]:
            if not enc:
                continue
            try:
                return content.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        # ถ้า fallback ทุกตัวพัง ให้ replace แทน ignore เพื่อยังเห็น text ส่วนที่อ่านได้
        return content.decode("utf-8", errors="replace")

    if ext == ".pdf":
        import unicodedata
        from pypdf import PdfReader
        # visitor_text ช่วยดึง text ตามลำดับ layout จริง ลด กระโดด ข้ามบรรทัด ของ PDF ภาษาไทย/จีน
        # NFC normalize แก้ปัญหา composed/decomposed form ของ Unicode ที่ทำให้อักขระแสดงผิด
        reader = PdfReader(io.BytesIO(content))
        pages_text: list[str] = []
        for page in reader.pages:
            parts: list[str] = []

            def _visitor(text, *_):  # noqa: ANN001
                if text and text.strip():
                    parts.append(text)

            page.extract_text(visitor_text=_visitor)
            raw = "".join(parts) if parts else (page.extract_text() or "")
            pages_text.append(unicodedata.normalize("NFC", raw))
        return "\n".join(pages_text)

    if ext == ".docx":
        import unicodedata
        import docx
        doc = docx.Document(io.BytesIO(content))
        lines: list[str] = []
        # paragraph ปกติ
        for p in doc.paragraphs:
            if p.text.strip():
                lines.append(unicodedata.normalize("NFC", p.text))
        # table cells — ภาษาไทย/จีนในเอกสาร TH-ZN มักอยู่ใน table แต่โค้ดเดิมข้ามไป
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        lines.append(unicodedata.normalize("NFC", cell_text))
        return "\n".join(lines)

    if ext == ".doc":
        # .doc (binary format เก่า) ต้องใช้ antiword หรือ libreoffice แปลงก่อน — python lib ตรงๆ ไม่รองรับดี
        raise HTTPException(
            status_code=400,
            detail=".doc (Word เก่า) ยังไม่รองรับตรงๆ — กรุณาแปลงเป็น .docx ก่อนอัปโหลด",
        )

    raise HTTPException(status_code=400, detail=f"ไม่รองรับไฟล์นามสกุล {ext}")


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _run_job_phase1(job_id: str, source_doc: str, raw_text: str):
    """
    BackgroundTasks ของ FastAPI รัน task นี้ใน threadpool (sync thread)
    run_extraction_and_specialize เป็น async def -> ต้องใช้ asyncio.run() เพื่อ drive coroutine
    ห้ามใช้ await ตรงๆ เพราะไม่มี event loop ใน sync thread นี้
    """
    import asyncio
    try:
        JOBS[job_id]["status"] = "running"
        candidates = asyncio.run(run_extraction_and_specialize(source_doc, raw_text))
        JOBS[job_id]["candidates"] = candidates
        JOBS[job_id]["status"] = "pending_confirmation"
    except Exception as e:
        import traceback
        traceback.print_exc()
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/ingest", response_model=JobStatus)
async def ingest(
    background_tasks: BackgroundTasks,
    raw_text: Optional[bytes] = Form(default=None),   # รับเป็น bytes ก่อน แล้ว decode เอง
    file: Optional[UploadFile] = File(default=None),
):
    if not raw_text and not file:
        raise HTTPException(status_code=400, detail="ต้องส่ง raw_text หรือแนบไฟล์อย่างใดอย่างหนึ่ง")

    if file:
        content = await file.read()
        text = extract_text_from_upload(file.filename, content)
        # filename ใน multipart header อาจถูก encode ผิดโดย browser เก่า (latin-1 แทน utf-8)
        # re-encode กลับเพื่อให้ชื่อไฟล์ภาษาไทย/จีนแสดงถูกต้องใน source_doc
        raw_filename = file.filename or "upload"
        try:
            raw_filename = raw_filename.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass  # ชื่อไฟล์เป็น ASCII หรือ encode ถูกแล้ว ไม่ต้องแปลง
        source_doc = os.path.splitext(raw_filename)[0]
    else:
        # Form field ส่งมาเป็น bytes — detect encoding แล้ว decode ให้ถูกต้อง
        detected = _detect_encoding(raw_text)
        decoded: Optional[str] = None
        for enc in [detected, "utf-8-sig", "utf-8", "tis-620", "cp874", "latin-1"]:
            if not enc:
                continue
            try:
                decoded = raw_text.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        text = decoded or raw_text.decode("utf-8", errors="replace")
        source_doc = f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="ไม่พบข้อความให้ประมวลผล (ไฟล์ว่าง หรืออ่านไม่ออก)")

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "running", "source_doc": source_doc, "candidates": None, "result": None, "error": None}

    background_tasks.add_task(_run_job_phase1, job_id, source_doc, text)

    return JobStatus(job_id=job_id, status="running")


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบ job นี้")
    return JobStatus(job_id=job_id, status=job["status"], error=job.get("error"))


@app.get("/jobs/{job_id}/pending", response_model=List[PendingCandidate])
def get_pending(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบ job นี้")
    if job["status"] != "pending_confirmation":
        raise HTTPException(status_code=409, detail=f"job อยู่ในสถานะ {job['status']} ยังไม่พร้อมให้ confirm")

    pending = [
        PendingCandidate(
            candidate_id=c.candidate_id,
            th=c.th,
            cn=c.cn,
            entity_type=c.inferred_type or c.guessed_type,
            context_sentence=c.context_sentence,
        )
        for c in job["candidates"]
        if c.status in ("no_match", "manual_review")
    ]
    return pending


@app.post("/jobs/{job_id}/confirm", response_model=JobStatus)
def confirm_job(job_id: str, payload: ConfirmPayload, background_tasks: BackgroundTasks):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบ job นี้")
    if job["status"] != "pending_confirmation":
        raise HTTPException(status_code=409, detail=f"job อยู่ในสถานะ {job['status']} ยัง confirm ไม่ได้")

    decisions_map = {d.candidate_id: d.to_flow_decision() for d in payload.decisions}

    def _resume():
        import asyncio
        try:
            JOBS[job_id]["status"] = "running"
            result = asyncio.run(resume_write_and_finalize(job["source_doc"], job["candidates"], decisions_map))
            JOBS[job_id]["result"] = result
            JOBS[job_id]["status"] = "done"
        except Exception as e:
            import traceback
            traceback.print_exc()
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = str(e)

    background_tasks.add_task(_resume)
    JOBS[job_id]["status"] = "running"
    return JobStatus(job_id=job_id, status="running")


@app.get("/jobs/{job_id}/result")
def get_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบ job นี้")
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail=f"job อยู่ในสถานะ {job['status']} ยังไม่มีผลลัพธ์")
    return job["result"]