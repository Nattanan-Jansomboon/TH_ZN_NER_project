# NER Corpus Multi-Agent System

ระบบ multi-agent สำหรับสกัด Named Entity จากข้อความ/เอกสารไทย-จีน แล้วบันทึกลง Obsidian corpus แบบ deduplication-first โดยใช้ **CrewAI** (Scout/Manager Agent + Specialized Agent ต่อ entity type) หุ้มด้วย **FastAPI** และหน้าเว็บ ingest แบบง่าย

## โครงสร้างโปรเจกต์

```
.
├── backend/
│   ├── main.py              # FastAPI app: endpoints ทั้งหมด
│   └── ner_flow_api.py       # Agent/Task/Tool logic (Manager + Specialized Agents)
├── frontend/
│   └── index.html            # หน้าเว็บ ingest (พิมพ์ข้อความ / อัปโหลดไฟล์)
└── README.md
```

## สถาปัตยกรรม

- **Scout/Manager Agent** (1 ตัว) — chunk เอกสาร, coarse-pass extraction, dispatch ไปยัง Specialized Agent, รวมผล, เขียน shared files (`index.md`, `summary.md`, `log.md`)
- **Specialized Agent** (ต่อ entity type เช่น PERSON, ORG, GPE, DATE, MONEY) — อ่าน `overview.md`/`index.md` เฉพาะ folder ตัวเองเพื่อ inference type ที่ถูกต้อง, fuzzy match ≥80%, เขียนไฟล์ entity เฉพาะ scope ตัวเอง
- **Reclassify loop** — ถ้า Specialized Agent เห็นว่า type ที่ได้รับมาไม่ตรง context จะแนะนำ type อื่นกลับไป Manager (จำกัดไม่เกิน `MAX_HOP` รอบ ก่อน fallback เป็น manual review)
- **Human-in-the-loop confirmation** — entity ที่ไม่มีใน corpus ต้องผ่านการยืนยันจาก user ก่อนเขียนไฟล์จริง (ผ่านหน้าเว็บ ไม่ใช่ terminal)

รายละเอียดการออกแบบทั้งหมดอยู่ในบทสนทนาที่ใช้ร่าง flow นี้ขึ้นมา (SOUL.md เดิม + การปรับปรุงเป็น multi-agent)

## การทำงานของ Flow (end-to-end)

1. User ส่งข้อความ/ไฟล์ผ่านหน้าเว็บ → `POST /ingest`
2. Backend แปลงไฟล์เป็น text (ถ้าเป็นไฟล์) → สร้าง job → รัน **Stage 1** (scout → specialize → reclassify) เป็น background task
3. เว็บ poll `GET /jobs/{id}` จนกว่าจะเสร็จ Stage 1
4. ถ้ามี entity ใหม่ (ไม่เจอใน corpus) → เว็บดึง `GET /jobs/{id}/pending` มาแสดงให้ user ยืนยัน/แก้ไข/ข้าม
5. User ส่งผลกลับ → `POST /jobs/{id}/confirm` → backend รัน **Stage 2** (เขียนไฟล์ entity + อัปเดต shared files + save JSON output) เป็น background task
6. เว็บ poll จนเสร็จ → ดึง `GET /jobs/{id}/result` มาแสดงผลลัพธ์

## การติดตั้ง

### ความต้องการของระบบ
- Python 3.10+
- (ถ้าต้องอ่าน `.doc` แบบเก่า) LibreOffice สำหรับแปลงเป็น `.docx` ก่อน — ปัจจุบันยังไม่รองรับในโค้ด

### 1) สร้างและเปิดใช้งาน virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

หลัง activate สำเร็จ จะเห็น `(venv)` นำหน้า prompt ใน terminal — ตรวจสอบว่าอยู่ใน venv ก่อน install ทุกครั้งด้วย:
```bash
python -m pip --version   # path ควรชี้เข้า venv/ ไม่ใช่ Python ระบบ
```

เวลาจะออกจาก venv ใช้คำสั่ง `deactivate`

### 2) ติดตั้ง dependencies

อัปเดต `pip` ก่อน แล้วติดตั้งไลบรารีที่ต้องใช้ทั้งหมด:

```bash
python -m pip install --upgrade pip
pip install fastapi uvicorn python-multipart pypdf python-docx crewai
```

รายการไลบรารีที่ติดตั้งและใช้ทำอะไรบ้าง:

| ไลบรารี | ใช้ทำอะไร |
|---|---|
| `fastapi` | สร้าง API endpoints ทั้งหมด (`main.py`) |
| `uvicorn` | ASGI server สำหรับรัน FastAPI |
| `python-multipart` | จำเป็นสำหรับให้ FastAPI รับ multipart form / file upload ได้ (ไม่มีจะ error ตอนอัปโหลดไฟล์) |
| `pypdf` | อ่าน/สกัดข้อความจากไฟล์ `.pdf` |
| `python-docx` | อ่าน/สกัดข้อความจากไฟล์ `.docx` (import เป็น `docx` ในโค้ด) |
| `crewai` | สร้าง Agent/Task/Crew สำหรับ Manager และ Specialized Agent |
| `langfuse` + `openinference-instrumentation-crewai` *(ไม่บังคับ)* | ส่ง trace การทำงานของทุก Agent ไป monitor ที่ Langfuse — ดูรายละเอียดที่หัวข้อ "ตั้งค่า Langfuse Monitoring" ด้านล่าง |

ถ้าจะใช้ LLM ผ่าน provider ภายนอก (เช่น Together AI, Fireworks, OpenRouter) อาจต้องติดตั้งเพิ่มตาม provider นั้น เช่น:
```bash
pip install litellm   # crewai ใช้ litellm ภายในสำหรับต่อ LLM หลายเจ้า ปกติติดมากับ crewai อยู่แล้ว
```

### 3) บันทึก dependencies ไว้สำหรับเครื่องอื่น (แนะนำ)

หลังติดตั้งเสร็จ ควร freeze เก็บไว้เป็น `requirements.txt` เพื่อให้ setup เครื่องอื่นซ้ำได้ง่าย:

```bash
pip freeze > requirements.txt
```

แล้วครั้งต่อไป (หรือเครื่องอื่น) ติดตั้งด้วยไฟล์เดียว:

```bash
python -m venv venv
source venv/bin/activate   # หรือ venv\Scripts\Activate.ps1 บน Windows
pip install -r requirements.txt
```

### ตั้งค่า LLM (ใช้ OpenRouter)

โปรเจกต์นี้ตั้งค่าให้เรียก LLM ผ่าน **OpenRouter** (endpoint กลางที่รวมหลายโมเดล/หลายค่ายไว้ที่เดียว — OpenAI, Anthropic, Meta, Nous/Hermes ฯลฯ) การตั้งค่าทั้งหมดรวมอยู่จุดเดียวในไฟล์ `backend/ner_flow_api.py` (ส่วน `LLM CONFIG`)

| ตัวแปร | ใช้กับ | ค่า default |
|---|---|---|
| `MANAGER_LLM` | Scout/Manager Agent | `openrouter/openai/gpt-4o` |
| `DEFAULT_SPECIALIST_LLM` | Specialized Agent ทุก type ที่ไม่ได้ override | `openrouter/openai/gpt-4o-mini` |
| `SPECIALIST_LLM_OVERRIDES` | Specialized Agent เฉพาะ type ที่ต้องการโมเดลพิเศษ | ว่างเปล่า (ไม่ override) |

#### 1) สมัคร OpenRouter และขอ API key

ไปที่ [openrouter.ai](https://openrouter.ai) → สมัครสมาชิก → สร้าง API key ที่หน้า Keys (จะขึ้นต้นด้วย `sk-or-`)

#### 2) ตั้ง API key เป็น environment variable

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

บน Windows PowerShell:
```powershell
$env:OPENROUTER_API_KEY="sk-or-..."
```

#### 3) เลือกโมเดล (ไม่ต้องแก้โค้ด — ตั้งผ่าน env var)

```bash
export MANAGER_MODEL="openrouter/openai/gpt-4o"
export SPECIALIST_MODEL="openrouter/openai/gpt-4o-mini"
```

ถ้าไม่ตั้ง `MANAGER_MODEL`/`SPECIALIST_MODEL` ระบบจะใช้ค่า default ตามตารางด้านบนโดยอัตโนมัติ

> **รูปแบบชื่อโมเดลของ OpenRouter** ต้องเป็น `openrouter/<provider>/<model-name>` เสมอ (ไม่ใช่แค่ `gpt-4o` เฉยๆ) เช่น `openrouter/anthropic/claude-3.5-sonnet`, `openrouter/nousresearch/hermes-3-llama-3.1-70b`, `openrouter/meta-llama/llama-3.1-70b-instruct` — ดูรายชื่อโมเดลและราคาทั้งหมดได้ที่ [openrouter.ai/models](https://openrouter.ai/models)

#### 4) ถ้าต้องการให้บาง entity type ใช้โมเดลพิเศษ

แก้ที่ `SPECIALIST_LLM_OVERRIDES` ใน `ner_flow_api.py` โดยตรง (เช่น type ที่ classify ยากกว่าอยากได้โมเดลที่แม่นกว่า หรืออยากลอง Hermes เฉพาะบาง type):

```python
SPECIALIST_LLM_OVERRIDES: dict[str, LLM] = {
    "TECHNICAL_TERM": LLM(
        model="openrouter/openai/gpt-4o",
        api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL, temperature=0.1,
    ),
    "PERSON": LLM(
        model="openrouter/nousresearch/hermes-3-llama-3.1-70b",
        api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL,
    ),
}
```

type ที่ไม่ได้ระบุใน dict นี้จะ fallback ไปใช้ `DEFAULT_SPECIALIST_LLM` โดยอัตโนมัติ

> **ข้อควรเช็คก่อนเลือกโมเดล:** ระบบพึ่ง structured output (`output_pydantic`) ค่อนข้างมากในทั้ง extraction และ specialize step โมเดลที่เลือกต้องรองรับ JSON mode / function calling ได้ดี ไม่งั้น parse ผลลัพธ์จะพังบ่อย — โมเดลตระกูล GPT-4o ผ่าน OpenRouter รองรับดี ส่วน Hermes ต้องเลือกรุ่น Hermes 2 Pro ขึ้นไปถึงจะรองรับ tool calling ได้เสถียร

### ตั้งค่า path สำคัญก่อนรัน

แก้ค่าคงที่ 2 ตัวใน `backend/ner_flow_api.py`:

```python
JSON_OUTPUT_DIR = "/home/hp/hermes-nectec-project/NER_th-zn/JSON_OUTPUT"  # ที่เก็บผลลัพธ์ JSON แต่ละครั้งที่ ingest
VAULT_ROOT      = "/home/hp/hermes-nectec-project/NER_th-zn/CORPUS"        # root ของ Obsidian vault (Entity_type/, index.md, summary.md, log.md)
```

> ถ้ารันบน Windows โดยตรง (ไม่ใช่ผ่าน WSL) ให้ใช้ raw string แทน เช่น `r"C:\path\to\JSON_OUTPUT"`

vault ต้องมีโครงพื้นฐานตั้งต้นอยู่ก่อน (อย่างน้อยแต่ละ `Entity_type/<TYPE>/overview.md` และ `index.md`) มิฉะนั้น Specialized Agent จะ inference ผิดพลาดเพราะไม่มี guidance

### ตั้งค่า Langfuse Monitoring (ไม่บังคับ)

ระบบมี built-in hook สำหรับส่ง trace ของทุก Agent (Manager + Specialized Agent ทุกตัว) ไปที่ [Langfuse](https://langfuse.com) เพื่อดู log การทำงานแบบ end-to-end ได้ — **ถ้าไม่ตั้งค่าอะไรเลย ระบบจะรันปกติโดยไม่มี monitoring** ไม่ error ไม่ต้อง comment โค้ดออก

#### 1) ติดตั้ง dependencies เพิ่ม

```bash
pip install langfuse openinference-instrumentation-crewai
```

#### 2) สมัคร Langfuse และขอ API key

ไปที่ [cloud.langfuse.com](https://cloud.langfuse.com) → สมัครสมาชิก → สร้างโปรเจกต์ → คัดลอก Public key (`pk-lf-...`) และ Secret key (`sk-lf-...`) จากหน้า Settings (หรือจะ self-host Langfuse เองก็ได้)

#### 3) ตั้ง environment variable

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"   # หรือ URL ของ self-host instance
```

บน Windows PowerShell:
```powershell
$env:LANGFUSE_PUBLIC_KEY="pk-lf-..."
$env:LANGFUSE_SECRET_KEY="sk-lf-..."
$env:LANGFUSE_HOST="https://cloud.langfuse.com"
```

#### 4) รันตามปกติ — ไม่ต้องแก้โค้ดเพิ่ม

ตอน `uvicorn` สตาร์ทขึ้นมา ถ้าเช็ค key + connection ผ่าน จะเห็น log:
```
[Langfuse] instrumentation เปิดใช้งานแล้ว -> https://cloud.langfuse.com
```
ถ้า key ไม่ครบ หรือต่อ Langfuse ไม่ได้ (เน็ตล่ม/host ผิด) จะเห็น log แจ้งเตือนแทน แต่ **backend ยังรันต่อได้ปกติ** ไม่ crash:
```
[Langfuse] ไม่พบ LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY -> รันโดยไม่มี monitoring
```

#### สิ่งที่จะเห็นใน Langfuse dashboard

- แต่ละเอกสารที่ ingest จะถูก group เป็น **session เดียวกัน** (ใช้ `source_doc` เป็น session id) เห็นทั้ง flow ตั้งแต่ scout → specialize → reclassify → confirm → write ต่อเนื่องกันในหน้าเดียว ไม่กระจัดกระจายเป็น trace แยกของแต่ละ Agent
- แต่ละ trace ติด tag `stage1-extract-specialize` หรือ `stage2-confirm-write` แยกตามว่าเป็นช่วงก่อนหรือหลัง user confirm
- ดูได้ทั้ง input/output ของแต่ละ LLM call, token usage, latency ของ Manager Agent และ Specialized Agent แยกเป็นตัวๆ

## วิธีรัน

### 1) รัน backend

> ตรวจสอบก่อนว่า activate virtual environment แล้ว (เห็น `(venv)` นำหน้า prompt) ถ้ายังไม่ได้ activate ให้กลับไปทำตามขั้นตอนในหัวข้อ "การติดตั้ง" ก่อน

```bash
cd backend
uvicorn main:app --reload --port 8000
```

ตรวจว่า API พร้อมใช้งาน: เปิด `http://localhost:8000/docs` (Swagger UI ของ FastAPI จะขึ้นอัตโนมัติ)

### 2) เปิด frontend

เปิดไฟล์ `frontend/index.html` ตรงๆ ในเบราว์เซอร์ (ไม่ต้อง build ใดๆ)

> ถ้า backend รันอยู่คนละเครื่อง/คนละ port ให้แก้ค่า `API_BASE` ในบรรทัดต้นๆ ของ `<script>` ในไฟล์ `index.html`

### 3) ทดสอบ

- พิมพ์ข้อความไทยลงในกล่อง หรืออัปโหลดไฟล์ `.txt` / `.pdf` / `.docx`
- กด "เริ่มสกัด entity" แล้วรอผล
- ถ้ามี entity ใหม่จะมีการ์ดขึ้นมาให้ยืนยัน/แก้ไข/ข้าม
- ผลลัพธ์สุดท้ายจะแสดงเป็นตาราง และถูกบันทึกเป็นไฟล์ `.json` ใน `JSON_OUTPUT_DIR` ด้วย

## API Reference คร่าวๆ

| Method | Path | คำอธิบาย |
|---|---|---|
| POST | `/ingest` | ส่ง `raw_text` (form field) หรือ `file` (multipart) → คืน `job_id` |
| GET | `/jobs/{job_id}` | เช็คสถานะ: `running` / `pending_confirmation` / `done` / `error` |
| GET | `/jobs/{job_id}/pending` | รายการ entity ใหม่ที่รอ user ยืนยัน (เฉพาะตอน status = `pending_confirmation`) |
| POST | `/jobs/{job_id}/confirm` | ส่งผลการยืนยัน `{decisions: [{candidate_id, choice, edited_th?, edited_type?}]}` |
| GET | `/jobs/{job_id}/result` | ผลลัพธ์ JSON สุดท้าย (เฉพาะตอน status = `done`) |

## ข้อจำกัดที่รู้อยู่แล้ว (ต้องแก้ก่อนขึ้น production)

- **In-memory job store** (`JOBS` dict ใน `main.py`) — job หายเมื่อ restart server หรือรันแบบ multi-worker ควรเปลี่ยนเป็น Redis/DB
- **CORS เปิดกว้าง** (`allow_origins=["*"]`) — เฉพาะ dev เท่านั้น ต้องระบุ origin จริงตอน deploy
- **`.doc` (Word เก่า)** ยังไม่รองรับ ต้องแปลงเป็น `.docx` ก่อน หรือเพิ่ม LibreOffice conversion step
- **`SPECIALIZED_TYPES`** ตอนนี้มีแค่ 5 ตัวอย่าง (`PERSON, ORG, GPE, DATE, MONEY`) ต้องขยายให้ครบ 20 ประเภทตาม schema เดิม พร้อมสร้าง `overview.md` ตั้งต้นที่มี exclusion rule ชัดเจนสำหรับแต่ละ type
- **Auth** — ยังไม่มีระบบยืนยันตัวตนใดๆ บน endpoint เลย ถ้าจะเปิดใช้งานจริงต้องเพิ่ม API key หรือ session auth
- **Langfuse เป็น optional** — ถ้าไม่ตั้ง `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` ระบบจะรันโดยไม่มี monitoring เฉยๆ (ไม่ error) แต่ถ้าอยากเห็น trace การทำงานของ Agent ทั้งหมดควรตั้งค่าไว้ตั้งแต่ dev เพื่อ debug ง่ายขึ้น
