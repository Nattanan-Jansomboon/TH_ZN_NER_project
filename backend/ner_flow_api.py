"""
ner_flow_api.py
────────────────────────────
Logic / workflow เดียวกับ ner_flow_api.py ทุกประการ
แต่เปลี่ยนจากการ hardcode function call มาใช้ CrewAI Flows อย่างถูกต้อง

Flow แบ่งเป็น 2 stage เหมือนเดิม:
  Stage 1  (HTTP POST /ingest)   -> scout -> specialize -> reclassify loop
  Stage 2  (HTTP POST /confirm)  -> apply decisions -> write -> save json

การใช้งาน:
  stage1_flow = NERExtractionFlow(source_doc=..., raw_text=...)
  candidates  = await stage1_flow.kickoff_async()   # คืน List[Candidate]

  stage2_flow = NERWriteFlow(source_doc=..., candidates=candidates, decisions_map=...)
  output      = await stage2_flow.kickoff_async()   # คืน list[dict]
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from crewai import Agent, Crew, Task, Process, LLM
from crewai.flow.flow import Flow, start, listen, router
from crewai.tools import BaseTool
from pydantic import BaseModel, Field



# ─────────────────────────────────────────────
# Paths — อ่านจาก env var เสมอ ไม่ hardcode
# ─────────────────────────────────────────────
#
# ตั้งค่าใน .env หรือ export ก่อนรัน uvicorn:
#
#   Linux / WSL (Obsidian vault mount ผ่าน WSL):
#     export VAULT_ROOT="/mnt/c/Users/HP/Desktop/NER_project/TH_ZN_Corpus"
#
#   Windows path (รันตรงบน Windows Python — ไม่ใช่ WSL):
#     set VAULT_ROOT=C:\Users\HP\Desktop\NER_project\TH_ZN_Corpus
#
#   JSON output dir:
#     export JSON_OUTPUT_DIR="/mnt/c/Users/HP/Desktop/NER_project/JSON_OUTPUT"

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _path_from_env(name: str, default: Path) -> str:
    value = os.getenv(name)
    if value:
        return str(Path(value).expanduser())
    return str(default)


JSON_OUTPUT_DIR = _path_from_env(
    "JSON_OUTPUT_DIR",
    PROJECT_ROOT / "JSON_OUTPUT",
)

_VAULT_ROOT_RAW = os.getenv(
    "VAULT_ROOT",
    str(PROJECT_ROOT / "TH_ZN_Corpus"),
)

def _resolve_vault_root(raw: str) -> str:
    """
    แปลง path ให้ถูกต้องตาม OS ที่รันจริง
    - Windows path (C:/...) บน Linux -> แปลงเป็น /mnt/c/... (WSL convention)
    - path ที่ถูกแล้ว -> คืนตรงๆ
    """
    import re
    # จับ pattern "C:/..." หรือ "C:\..." (Windows path บน Linux)
    win_match = re.match(r'^([A-Za-z]):[/\\](.*)', raw)
    if win_match and os.name != "nt":
        drive  = win_match.group(1).lower()
        rest   = win_match.group(2).replace("\\", "/").replace("//", "/")
        wsl    = f"/mnt/{drive}/{rest}"
        print(f"[VAULT_ROOT] Windows path ถูก map ไปยัง WSL: {raw!r} -> {wsl!r}")
        return wsl
    return raw

VAULT_ROOT = _resolve_vault_root(_VAULT_ROOT_RAW)

# ตรวจสอบว่า path ใช้งานได้จริงตอน import — เตือนล่วงหน้าถ้า vault ไม่เจอ
if not os.path.exists(VAULT_ROOT):
    print(
        f"[VAULT_ROOT] ⚠️  ไม่พบ path: {VAULT_ROOT!r}\n"
        f"  -> ตั้ง env var VAULT_ROOT ให้ถูกต้องก่อนรัน uvicorn\n"
        f"  -> WSL: export VAULT_ROOT=\"/mnt/c/Users/HP/Desktop/...\"\n"
        f"  -> ไฟล์จะยังเขียนไม่ได้จนกว่า path จะถูกต้อง"
    )
else:
    print(f"[VAULT_ROOT] ✓ {VAULT_ROOT!r}")

# ─────────────────────────────────────────────
# Langfuse monitoring (optional — เหมือนเดิม)
# ─────────────────────────────────────────────
LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
langfuse = None

if LANGFUSE_ENABLED:
    try:
        from langfuse import get_client, propagate_attributes
        from openinference.instrumentation.crewai import CrewAIInstrumentor

        langfuse = get_client()
        try:
            is_authenticated = langfuse.auth_check()
        except Exception as auth_err:
            print(f"[Langfuse] auth_check ต่อไม่ได้ ({auth_err}) -> รันต่อโดยไม่มี monitoring")
            is_authenticated = False

        if is_authenticated:
            CrewAIInstrumentor().instrument(skip_dep_check=True)
            print(f"[Langfuse] instrumentation เปิดแล้ว -> {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
        else:
            print("[Langfuse] auth_check ไม่ผ่าน -> เช็ค keys อีกครั้ง")
            langfuse = None
    except ImportError:
        print("[Langfuse] ยังไม่ได้ติดตั้ง -> ข้าม monitoring")
        langfuse = None
else:
    print("[Langfuse] ไม่พบ keys -> รันโดยไม่มี monitoring")

# ─────────────────────────────────────────────
# LLM config (เหมือนเดิม)
# ─────────────────────────────────────────────
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MANAGER_LLM = LLM(
    model=os.getenv("MANAGER_MODEL", "deepseek/deepseek-v4-flash-0731"),
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    temperature=0.2,
)

DEFAULT_SPECIALIST_LLM = LLM(
    model=os.getenv("SPECIALIST_MODEL", "deepseek/deepseek-v4-flash-0731"),
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    temperature=0.2,
)

SPECIALIST_LLM_OVERRIDES: dict[str, LLM] = {
    # "TECHNICAL_TERM": LLM(model="openrouter/openai/gpt-4o", ...),
}


def get_llm_for_type(entity_type: str) -> LLM:
    return SPECIALIST_LLM_OVERRIDES.get(entity_type, DEFAULT_SPECIALIST_LLM)


# ─────────────────────────────────────────────
# Corpus helpers (เหมือนเดิม)
# ─────────────────────────────────────────────

def _read(path: str) -> str:
    full_path = os.path.join(VAULT_ROOT, path)
    if not os.path.exists(full_path):
        return f"[ยังไม่มีไฟล์: {path}]"
    with open(full_path, encoding="utf-8") as f:
        return f.read()


def _write(path: str, content: str, append: bool = False) -> None:
    full_path = os.path.join(VAULT_ROOT, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    mode = "a" if append else "w"
    with open(full_path, mode, encoding="utf-8") as f:
        f.write(content + "\n")


# ─────────────────────────────────────────────
# Corpus metadata helpers (ตาม SOUL.md STEP 5d-f)
# ─────────────────────────────────────────────

_TECH_TERM_DOMAINS = ["Engineering Domain", "Finance Domain", "Healthcare Domain", "IT Domain"]
_SKIP_MD = {"index.md", "overview.md"}

def _count_entities_in_type(entity_type: str) -> int:
    """นับจำนวน entity .md files ใน folder ของ type นั้น (ไม่นับ index.md / overview.md)
    TECHNICAL_TERM: นับจาก sub-folder ทั้ง 4 domain รวมกัน ไม่ใช่ root folder
    """
    if entity_type == "TECHNICAL_TERM":
        total = 0
        for domain in _TECH_TERM_DOMAINS:
            sub = os.path.join(VAULT_ROOT, "Entity_type", "TECHNICAL_TERM", domain)
            if not os.path.isdir(sub):
                continue
            total += sum(
                1 for f in os.listdir(sub)
                if f.endswith(".md") and f not in _SKIP_MD
            )
        return total

    folder = os.path.join(VAULT_ROOT, "Entity_type", entity_type)
    if not os.path.isdir(folder):
        return 0
    return sum(
        1 for f in os.listdir(folder)
        if f.endswith(".md") and f not in _SKIP_MD
    )


def _count_all_entities() -> dict[str, int]:
    """นับ entity ทุก type คืน {type: count}"""
    counts: dict[str, int] = {}
    for t in SPECIALIZED_TYPES:
        counts[t] = _count_entities_in_type(t)
    return counts


def _update_type_index(entity_type: str, new_entities: list[dict]) -> None:
    """
    อัปเดต Entity_type/<TYPE>/index.md
    ตาม SOUL.md STEP 5-d: rebuild รายชื่อ entity ทั้งหมดใน type นั้น
    new_entities: list of {th, cn, status, domain?} ที่เพิ่งเพิ่ม/อัปเดตในรอบนี้

    TECHNICAL_TERM: rebuild root TECHNICAL_TERM/index.md โดยรวมรายชื่อจากทุก domain sub-folder
                    พร้อม rebuild แต่ละ <Domain>/index.md แยกกัน
    """
    today = datetime.now().strftime("%Y-%m-%d")

    if entity_type == "TECHNICAL_TERM":
        # ── rebuild แต่ละ domain/index.md ────────────────────────────────────
        total_count = 0
        domain_counts: dict[str, int] = {}
        for domain in _TECH_TERM_DOMAINS:
            sub_folder = os.path.join(VAULT_ROOT, "Entity_type", "TECHNICAL_TERM", domain)
            os.makedirs(sub_folder, exist_ok=True)
            existing_in_domain = sorted(
                f[:-3] for f in os.listdir(sub_folder)
                if f.endswith(".md") and f not in _SKIP_MD
            )
            count_d = len(existing_in_domain)
            domain_counts[domain] = count_d
            total_count += count_d

            domain_lines = [
                f"# {domain} Index",
                f"",
                f"อัปเดตล่าสุด: {today} | จำนวน entity: {count_d}",
                f"",
                f"## รายชื่อ Entity",
            ]
            for name in existing_in_domain:
                domain_lines.append(f"- [[{name}]]")

            # เพิ่มล่าสุด — เฉพาะ entity ที่ domain ตรง
            new_in_domain = [e for e in new_entities if e.get("domain") == domain]
            if new_in_domain:
                domain_lines.append("")
                domain_lines.append(f"## เพิ่มล่าสุด ({today})")
                for e in new_in_domain:
                    th   = e.get("th", "")
                    cn   = e.get("cn") or ""
                    stat = e.get("status", "")
                    domain_lines.append(f"- [[{th}]] {('/ ' + cn) if cn else ''} `{stat}`")

            _write(f"Entity_type/TECHNICAL_TERM/{domain}/index.md", "\n".join(domain_lines), append=False)
            print(f"[update_type_index] อัปเดต TECHNICAL_TERM/{domain}/index.md ({count_d} entities)")

        # ── rebuild root TECHNICAL_TERM/index.md ─────────────────────────────
        root_lines = [
            f"# สารบัญ — TECHNICAL_TERM",
            f"",
            f"อัปเดตล่าสุด: {today} | จำนวน entity: {total_count}",
            f"",
            f"## รายชื่อ Entity",
        ]
        for domain in _TECH_TERM_DOMAINS:
            sub_folder = os.path.join(VAULT_ROOT, "Entity_type", "TECHNICAL_TERM", domain)
            if not os.path.isdir(sub_folder):
                continue
            for name in sorted(
                f[:-3] for f in os.listdir(sub_folder)
                if f.endswith(".md") and f not in _SKIP_MD
            ):
                root_lines.append(f"- [[{name}]]")

        if new_entities:
            root_lines.append("")
            root_lines.append(f"## เพิ่มล่าสุด ({today})")
            for e in new_entities:
                th   = e.get("th", "")
                cn   = e.get("cn") or ""
                stat = e.get("status", "")
                domain_tag = e.get("domain", "")
                root_lines.append(
                    f"- [[{th}]] {('/ ' + cn) if cn else ''} `{stat}`"
                    + (f" [{domain_tag}]" if domain_tag else "")
                )

        _write("Entity_type/TECHNICAL_TERM/index.md", "\n".join(root_lines), append=False)
        print(f"[update_type_index] อัปเดต TECHNICAL_TERM/index.md (total={total_count})")
        return

    # ── non-TECHNICAL_TERM types ──────────────────────────────────────────────
    folder = os.path.join(VAULT_ROOT, "Entity_type", entity_type)
    if not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)

    existing = sorted(
        f[:-3] for f in os.listdir(folder)
        if f.endswith(".md") and f not in _SKIP_MD
    )
    count = len(existing)

    lines = [
        f"# สารบัญ — {entity_type}",
        f"",
        f"อัปเดตล่าสุด: {today} | จำนวน entity: {count}",
        f"",
        f"## รายชื่อ Entity",
    ]
    for name in existing:
        lines.append(f"- [[{name}]]")

    if new_entities:
        lines.append("")
        lines.append(f"## เพิ่มล่าสุด ({today})")
        for e in new_entities:
            th   = e.get("th", "")
            cn   = e.get("cn") or ""
            stat = e.get("status", "")
            lines.append(f"- [[{th}]] {('/ ' + cn) if cn else ''} `{stat}`")

    _write(f"Entity_type/{entity_type}/index.md", "\n".join(lines), append=False)
    print(f"[update_type_index] อัปเดต {entity_type}/index.md ({count} entities)")


def _update_type_overview(entity_type: str, new_entities: list[dict]) -> None:
    """
    อัปเดต Entity_type/<TYPE>/overview.md
    ตาม SOUL.md: ภาพรวมและแนวทางการจำแนก — append session summary ต่อท้าย
    ถ้ายังไม่มีไฟล์จะสร้าง skeleton ใหม่
    """
    path = f"Entity_type/{entity_type}/overview.md"
    full_path = os.path.join(VAULT_ROOT, path)
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(full_path):
        # สร้าง skeleton overview ครั้งแรก
        skeleton = (
            f"# Overview — {entity_type}\n\n"
            f"## คำอธิบาย\n<!-- กรอกคำอธิบาย type นี้ -->\n\n"
            f"## Inclusion criteria\n<!-- เกณฑ์ว่า entity ไหนเข้า type นี้ -->\n\n"
            f"## Exclusion criteria\n<!-- เกณฑ์ว่า entity ไหนไม่เข้า type นี้ -->\n\n"
            f"## ตัวอย่าง entity\n<!-- ตัวอย่างที่ดี -->\n\n"
            f"## Session log\n"
        )
        _write(path, skeleton, append=False)

    if new_entities:
        session_note = (
            f"\n### {today} — ingest session\n"
            + "\n".join(
                f"- `{e.get('th','')}` ({e.get('cn') or 'cn=null'}) → {e.get('status','')}"
                for e in new_entities
            )
        )
        _write(path, session_note, append=True)
        print(f"[update_type_overview] append session log ไปยัง {entity_type}/overview.md")


def _update_root_index(counts: dict[str, int]) -> None:
    """
    อัปเดต root index.md ตาม SOUL.md STEP 5-e
    rebuild ทั้งไฟล์เพื่อให้ตัวเลขถูกต้องเสมอ
    """
    today = datetime.now().strftime("%Y-%m-%d")
    total = sum(counts.values())

    lines = [
        "# สารบัญ — TH_ZN NER Corpus",
        "",
        "## สถิติ",
        f"- จำนวน entity ทั้งหมด: {total}",
        f"- อัปเดตล่าสุด: {today}",
        "",
        "## Entity Types",
    ]
    for t in SPECIALIZED_TYPES:
        n = counts.get(t, 0)
        if t == "TECHNICAL_TERM":
            lines.append(f"- [[Entity_type/TECHNICAL_TERM/index|TECHNICAL_TERM]] — คำศัพท์เทคนิค ({n} entries รวมทุก domain)")
            for domain in ["Engineering Domain", "Finance Domain", "Healthcare Domain", "IT Domain"]:
                lines.append(f"  - [[Entity_type/TECHNICAL_TERM/{domain}/index|{domain}]]")
        else:
            desc_map = {
                "CARDINAL": "จำนวนนับ", "DATE": "วันที่/ช่วงเวลา", "EVENT": "งาน/เหตุการณ์",
                "FAC": "สิ่งก่อสร้าง", "GPE": "หน่วยภูมิรัฐศาสตร์", "LANGUAGE": "ภาษา",
                "LAW": "กฎหมาย/นโยบาย", "LOC": "สถานที่ทางภูมิศาสตร์", "MONEY": "มูลค่าเงิน",
                "NORP": "สัญชาติ/กลุ่ม", "ORDINAL": "ลำดับที่", "ORG": "องค์กร",
                "PERCENT": "ร้อยละ", "PERSON": "บุคคล", "PRODUCT": "ผลิตภัณฑ์/แพลตฟอร์ม",
                "QUANTITY": "ปริมาณ", "TIME": "เวลา", "WORK_OF_ART": "งานศิลปะ/สื่อ",
            }
            desc = desc_map.get(t, t)
            lines.append(f"- [[Entity_type/{t}/index|{t}]] — {desc} ({n} entries)")

    _write("index.md", "\n".join(lines), append=False)
    print(f"[update_root_index] อัปเดต root index.md (total={total})")


def _update_summary(counts: dict[str, int], source_doc: str, session_new: int, session_matched: int) -> None:
    """
    อัปเดต summary.md ตาม SOUL.md STEP 5-e
    rebuild ทั้งไฟล์ให้แสดงสถิติล่าสุดเสมอ
    """
    today = datetime.now().strftime("%Y-%m-%d")
    total = sum(counts.values())
    non_empty = sum(1 for n in counts.values() if n > 0)

    # ตาราง coverage
    table_rows = ["| entity_type | entries |", "|-------------|---------|"]
    for t in SPECIALIZED_TYPES:
        table_rows.append(f"| {t} | {counts.get(t, 0)} |")

    lines = [
        "# ภาพรวม Corpus — TH_ZN NER",
        "",
        "## สถิติรวม",
        f"- จำนวน entity ทั้งหมด: **{total}**",
        f"- จำนวน type ที่มีข้อมูล: {non_empty} / {len(SPECIALIZED_TYPES)}",
        f"- อัปเดตล่าสุด: {today}",
        f"- เอกสารล่าสุดที่ ingest: `{source_doc}`",
        "",
        "## สถิติ session ล่าสุด",
        f"- entity ใหม่: {session_new}",
        f"- entity ที่ match corpus เดิม: {session_matched}",
        "",
        "## Coverage ต่อ Type",
        *table_rows,
    ]

    _write("summary.md", "\n".join(lines), append=False)
    print(f"[update_summary] อัปเดต summary.md (total={total})")


def _update_log(source_doc: str, new_count: int, matched_count: int,
                skipped_count: int, decisions: list[dict]) -> None:
    """
    append log.md ตาม SOUL.md STEP 5-f
    format: ## [YYYY-MM-DD] ingest | <ชื่อเอกสาร> | N new, N matched
    + บรรทัด confirm ต่อ entity ที่ user ตัดสินใจ
    """
    today = datetime.now().strftime("%Y-%m-%d")
    entries = [
        f"\n## [{today}] ingest | {source_doc} | "
        f"{new_count} new, {matched_count} matched"
    ]
    for d in decisions:
        th     = d.get("th", "")
        choice = d.get("choice", "")
        entries.append(f"## [{today}] confirm | {th} | user: {choice}")

    _write("log.md", "\n".join(entries), append=True)
    print(f"[update_log] append {len(entries)} entries ไปยัง log.md")


# ─────────────────────────────────────────────
# Scoped tools (เหมือนเดิม)
# ─────────────────────────────────────────────

class ReadOverviewTool(BaseTool):
    name: str = "read_overview"
    description: str = "อ่านไฟล์ overview.md ของ entity type ที่ตัวเองรับผิดชอบเท่านั้น"
    entity_type: str

    def _run(self) -> str:
        return _read(f"Entity_type/{self.entity_type}/overview.md")


class ReadIndexTool(BaseTool):
    name: str = "read_index"
    description: str = "อ่านไฟล์ index.md ของ entity type ที่ตัวเองรับผิดชอบเท่านั้น"
    entity_type: str

    def _run(self) -> str:
        return _read(f"Entity_type/{self.entity_type}/index.md")


class WriteEntityTool(BaseTool):
    name: str = "write_entity"
    description: str = "สร้าง/append ไฟล์ entity เฉพาะใน folder ของ type ตัวเอง"
    entity_type: str

    def _run(self, entity_name: str, content: str, mode: str = "create") -> str:
        path = f"Entity_type/{self.entity_type}/{entity_name}.md"
        _write(path, content, append=(mode == "append"))
        return f"เขียน {path} สำเร็จ (mode={mode})"

    def write(self, entity_name: str, content: str, mode: str = "create") -> str:
        """
        เรียกตรงจาก Python code (ไม่ผ่าน LLM/CrewAI tool dispatch)
        BaseTool._run() ถูก wrap โดย CrewAI — การเรียก _run() ตรงๆ จาก code
        อาจไม่ได้ส่ง args เข้าถูกต้องในบางเวอร์ชัน ใช้ method นี้แทนเสมอ
        """
        path = f"Entity_type/{self.entity_type}/{entity_name}.md"
        full_path = os.path.join(VAULT_ROOT, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        mode_flag = "a" if mode == "append" else "w"
        with open(full_path, mode_flag, encoding="utf-8") as f:
            f.write(content + "\n")
        print(f"[WriteEntityTool] เขียนสำเร็จ: {full_path} (mode={mode})")
        return f"เขียน {path} สำเร็จ (mode={mode})"


class ReadRootTool(BaseTool):
    name: str = "read_root"
    description: str = "อ่าน root index.md หรือ summary.md ของ corpus ทั้งระบบ"

    def _run(self, filename: str) -> str:
        return _read(filename)


class WriteRootTool(BaseTool):
    name: str = "write_root"
    description: str = "เขียน/append log.md, index.md, summary.md ระดับ root (Manager เท่านั้น)"

    def _run(self, filename: str, content: str, append: bool = True) -> str:
        _write(filename, content, append=append)
        return f"เขียน root {filename} สำเร็จ"


# ─────────────────────────────────────────────
# Pydantic schemas (เหมือนเดิม)
# ─────────────────────────────────────────────

class CandidateExtraction(BaseModel):
    candidate_id: str
    th: str
    cn: Optional[str] = None
    guessed_type: str
    context_sentence: str


class ExtractionResult(BaseModel):
    candidates: List[CandidateExtraction] = Field(default_factory=list)


class SpecializeResult(BaseModel):
    candidate_id: str
    status: str
    inferred_type: Optional[str] = None
    match_score: Optional[float] = None
    inference_reason: Optional[str] = None
    matched_evidence: Optional[str] = None


class Candidate(BaseModel):
    candidate_id: str
    th: str
    cn: Optional[str] = None
    guessed_type: str
    inferred_type: Optional[str] = None
    context_sentence: str
    status: Optional[str] = None
    hop_count: int = 0
    match_score: Optional[float] = None
    inference_reason: Optional[str] = None


class ConfirmDecision(BaseModel):
    choice: str          # "confirm" | "skip" | "edit"
    edited_th: Optional[str] = None
    edited_type: Optional[str] = None


# ─────────────────────────────────────────────
# Agents (เหมือนเดิม)
# ─────────────────────────────────────────────

_SKILL_DIR = _path_from_env("SKILL_DIR", PROJECT_ROOT / "skills")


# ── โหลด skill ก่อนสร้าง agent ทุกตัว ────────────────────────────────────
from pathlib import Path
from crewai.skills import discover_skills, activate_skill

_SKILL_MD = os.path.join(_SKILL_DIR, "ner-corpus-conductor", "SKILL.md")

print("\n" + "="*60)
print("[Skill Check] เริ่มตรวจสอบ skill")
print(f"  _SKILL_DIR  : {_SKILL_DIR}")
print(f"  SKILL.md    : {_SKILL_MD}")
print(f"  มีไฟล์ไหม  : {os.path.exists(_SKILL_MD)}")

_skills_found = discover_skills(Path(_SKILL_DIR))
print(f"  discover    : พบ {len(_skills_found)} skill(s) → {[s.name for s in _skills_found]}")

if _skills_found:
    _activated_skill = activate_skill(_skills_found[0])
    _body_preview = (_activated_skill.instructions or "")[:200].replace("\n", " ")
    print(f"  body preview: {_body_preview}...")
    print("  ✅ skill โหลดสำเร็จ — จะ inject เข้า agent ทุกตัว (manager + specialized)")
else:
    _activated_skill = None
    print("  ❌ ไม่พบ skill — เช็ค path และ frontmatter name field")
    print(f"     ต้องการ: {_SKILL_DIR}/ner-corpus-conductor/SKILL.md")
    print(f"     frontmatter name: ต้องเป็น 'ner-corpus-conductor'")

print("="*60 + "\n")

# _skill_arg: ส่งเข้า skills= ของทุก agent — ถ้าโหลดไม่ได้ fallback เป็น path
# (CrewAI จะ discover ใหม่เอง แต่จะไม่ยืนยันได้ว่าโหลดสำเร็จ)
_skill_arg = [_SKILL_DIR]
manager_agent = Agent(
    role="Scout/Manager Agent",
    goal="chunk เอกสาร, coarse-pass extraction, dispatch ไปยัง specialized agent, รวมผล, เขียน shared files",
    backstory="orchestrator กลาง รู้ภาพรวม corpus แต่ไม่ classify ละเอียดเอง",
    tools=[ReadRootTool(), WriteRootTool()],
    skills=_skill_arg,
    llm=MANAGER_LLM,
    verbose=True,
)

# ─────────────────────────────────────────────────────────────────────────

SPECIALIZED_TYPES = [
    "PERSON", "ORG", "GPE", "DATE", "MONEY",
    "PRODUCT", "WORK_OF_ART", "NORP", "FAC", "EVENT",
    "CARDINAL", "LANGUAGE", "LAW", "LOC", "ORDINAL",
    "PERCENT", "QUANTITY", "TECHNICAL_TERM", "TIME",
]

specialized_agents: dict[str, Agent] = {}
for _t in SPECIALIZED_TYPES:
    specialized_agents[_t] = Agent(
        role=f"Specialized Agent - {_t}",
        goal=(
            f"อ่าน overview.md ของ {_t} เพื่อยืนยัน candidate เข้าเกณฑ์จริงไหม (เช็ค exclusion rule), "
            f"ถ้าเข้าเกณฑ์ lookup index.md แล้ว fuzzy match ≥80%, ถ้าไม่เข้าเกณฑ์แนะนำ type อื่นที่เหมาะกว่า"
        ),
        backstory=f"เชี่ยวชาญเฉพาะ {_t} เขียนไฟล์ได้เฉพาะ Entity_type/{_t}/",
        tools=[ReadOverviewTool(entity_type=_t), ReadIndexTool(entity_type=_t), WriteEntityTool(entity_type=_t)],
        #skills=_skill_arg,
        llm=get_llm_for_type(_t),
        verbose=True,
    )

MAX_HOP = 2


# ─────────────────────────────────────────────
# Flow State schemas
# ─────────────────────────────────────────────

class ExtractionFlowState(BaseModel):
    """State สำหรับ Stage 1 Flow"""
    source_doc: str = ""
    raw_text: str = ""
    candidates: List[Candidate] = Field(default_factory=list)
    hop: int = 0


class WriteFlowState(BaseModel):
    """State สำหรับ Stage 2 Flow"""
    source_doc: str = ""
    candidates: List[Candidate] = Field(default_factory=list)
    decisions_map: dict = Field(default_factory=dict)
    output: list = Field(default_factory=list)


# ─────────────────────────────────────────────
# STAGE 1 FLOW — NERExtractionFlow
# ─────────────────────────────────────────────

class NERExtractionFlow(Flow[ExtractionFlowState]):
    """
    Stage 1: Scout -> Specialize -> Reclassify loop -> Finalize

    CrewAI Flows ไม่รองรับ circular edge (method listen ตัวเอง) ดังนั้น
    reclassify loop จึงเป็น plain Python while loop ใน @start method เดียว
    Flow graph จึงมีแค่ 2 node: run_pipeline -> finalize
    ซึ่งสะอาดและ Pydantic validate ผ่านแน่นอน
    """

    def __init__(self, source_doc: str, raw_text: str):
        super().__init__()
        self.state.source_doc = source_doc
        self.state.raw_text = raw_text

    # ── Step 1: Scout + Specialize + Reclassify loop (Phase 0-2) ──────────────
    @start()
    def run_pipeline(self) -> List[Candidate]:
        """
        SOUL.md STEP 1 — โหลด Corpus schema (summary.md + root index.md)
        SOUL.md STEP 2 — สกัด candidate entities (scout)
        SOUL.md STEP 3-A/B — ส่ง corpus context ให้ manager ก่อน classify
        Phase 1 — Specialize pass
        Phase 2 — Reclassify loop
        """
        # ── STEP 1: โหลด Corpus Schema (SOUL.md STEP 1 + 3-A + 3-B) ──────────
        # อ่าน summary.md (3-A) และ root index.md (3-B) ก่อนทำอะไรทั้งสิ้น
        # เพื่อให้ manager agent รู้ภาพรวม corpus และ map ของแต่ละ type
        corpus_overview = _read("overview.md")
        corpus_index   = _read("index.md")

        corpus_context = (
            f"=== CORPUS CONTEXT (STEP 1: โหลดก่อนสกัด) ===\n\n"
            f"--- overview.md (3-A: ภาพรวม corpus, สถิติ, coverage ต่อ type) ---\n"
            f"{corpus_overview}\n\n"
            f"--- root index.md (3-B: map type -> path ใน corpus) ---\n"
            f"{corpus_index}\n"
            f"=== END CORPUS CONTEXT ===\n"
        )
        print(f"[run_pipeline] โหลด corpus context: overview.md + index.md")

        # ── STEP 2/3-C: Scout พร้อม corpus context (SOUL.md STEP 2 + 3-C) ────
        supported_types = ", ".join(SPECIALIZED_TYPES)
        task = Task(
            description=(
                f"{corpus_context}\n\n"
                f"ใช้ข้อมูลใน CORPUS CONTEXT ข้างต้น (summary + index) เพื่อ:\n"
                f"1) เข้าใจ type ที่มีอยู่แล้วใน corpus และจำนวน entry แต่ละ type\n"
                f"2) ช่วย classify guessed_type ได้แม่นขึ้นโดยอ้างอิง context จริงจาก corpus\n\n"
                f"จากนั้นสกัด candidate entity ทุกตัวจากข้อความต่อไปนี้:\n\n{self.state.raw_text}\n\n"
                f"guessed_type ต้องเป็นตัวพิมพ์ใหญ่ทั้งหมด และเลือกจากรายการนี้เท่านั้น: {supported_types}\n"
                f"กรองคำทั่วไป/ตำแหน่ง (เช่น 'นายก') ออก — เก็บเฉพาะ named entity จริงเท่านั้น\n"
                f"ถ้า entity ไม่เข้าเกณฑ์ type ไหนเลย ให้ใส่ type ที่ใกล้เคียงที่สุดจากรายการ"
            ),
            expected_output="รายการ candidate ตาม schema ที่กำหนด ครบทุก entity ที่พบในข้อความ",
            agent=manager_agent,
            output_pydantic=ExtractionResult,
        )
        crew = Crew(agents=[manager_agent], tasks=[task], process=Process.sequential)
        crew.kickoff()

        parsed: ExtractionResult = task.output.pydantic
        self.state.candidates = [Candidate(**c.model_dump()) for c in parsed.candidates]

        # ── Phase 1: Specialize (รอบแรก) ──────────────────────────────────────
        self._run_specialize_pass(self.state.candidates)

        # ── Phase 2: Reclassify loop (plain while — ไม่ใช้ circular Flow edge) ─
        for _ in range(MAX_HOP):
            pending = [
                c for c in self.state.candidates
                if c.status == "reclassify_request" and c.hop_count < MAX_HOP
            ]
            if not pending:
                break
            for c in pending:
                c.hop_count += 1
                c.guessed_type = c.inferred_type or c.guessed_type
            self._run_specialize_pass(self.state.candidates)

        return self.state.candidates

    # ── Step 2: Finalize — บังคับ manual_review ที่เกิน hop ──────────────────
    @listen(run_pipeline)
    def finalize_extraction(self, candidates: List[Candidate]) -> List[Candidate]:
        """Phase 2 สุดท้าย — candidate ที่ยัง reclassify_request อยู่ -> manual_review"""
        for c in self.state.candidates:
            if c.status == "reclassify_request":
                c.status = "manual_review"
        return self.state.candidates

    # ── Helper: specialize pass ────────────────────────────────────────────────
    def _run_specialize_pass(self, candidates: List[Candidate]) -> None:
        for c in candidates:
            if c.status in ("matched", "manual_review"):
                continue

            agent_type = (c.inferred_type or c.guessed_type or "").strip().upper()
            c.guessed_type = agent_type

            agent = specialized_agents.get(agent_type)
            if not agent:
                c.status = "manual_review"
                c.inference_reason = f"ไม่รู้จัก entity_type '{agent_type}'"
                continue

            task = Task(
                description=(
                    f"candidate: '{c.th}' | context: '{c.context_sentence}'\n"
                    f"1) เรียก read_overview เช็คก่อนว่าเข้าเกณฑ์ {agent_type} จริงไหม\n"
                    f"2) ถ้าเข้าเกณฑ์: **ต้องเรียก read_index จริงๆ ก่อนเสมอ** แล้วเทียบชื่อ candidate กับ"
                    f"รายชื่อที่อ่านได้ทีละบรรทัด ห้ามตอบ matched จากความรู้เดิม/ความคุ้นเคยกับชื่อนี้เด็ดขาด "
                    f"ถ้าไม่เห็นชื่อที่ใกล้เคียง ≥80% อยู่ใน index.md ที่อ่านได้จริง ต้องตอบ no_match เท่านั้น "
                    f"ถ้าตอบ matched ต้องระบุ matched_evidence เป็นบรรทัดที่คัดลอกมาจาก index.md จริง "
                    f"(ห้ามเว้นว่างถ้า status=matched)\n"
                    f"3) ถ้าไม่เข้าเกณฑ์: แนะนำ type ที่เหมาะกว่า -> status=reclassify_request พร้อม inference_reason"
                ),
                expected_output="ผลลัพธ์ตาม schema ที่กำหนด พร้อม matched_evidence ถ้า status=matched",
                agent=agent,
                output_pydantic=SpecializeResult,
            )

            try:
                crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
                crew.kickoff()
                r: SpecializeResult = task.output.pydantic

                # กันหลุด: matched แต่ไม่มีหลักฐาน -> downgrade เป็น no_match
                if r.status == "matched" and not (r.matched_evidence or "").strip():
                    r.status = "no_match"
                    r.inference_reason = (r.inference_reason or "") + " [auto-downgrade: ไม่มี matched_evidence]"

                c.status = r.status
                c.inferred_type = r.inferred_type or agent_type
                c.match_score = r.match_score
                c.inference_reason = r.inference_reason

            except Exception as e:
                c.status = "manual_review"
                c.inference_reason = f"specialize error: {e}"


# ─────────────────────────────────────────────
# STAGE 2 FLOW — NERWriteFlow
# ─────────────────────────────────────────────

class NERWriteFlow(Flow[WriteFlowState]):
    """
    Stage 2: Apply decisions -> Write entities -> Save JSON -> Update log

    kickoff() คืน list[dict] (output สุดท้าย)
    FastAPI background task เรียกหลัง user confirm ผ่าน POST /jobs/{id}/confirm
    """

    def __init__(self, source_doc: str, candidates: List[Candidate], decisions_map: dict):
        super().__init__()
        self.state.source_doc    = source_doc
        self.state.candidates    = candidates
        self.state.decisions_map = decisions_map

    # ── Step 1: Apply decisions & write entity files (Phase 3 + 4) ────────────
    @start()
    def apply_and_write(self) -> List[Candidate]:
        """
        Phase 3 — ดู decision ของแต่ละ candidate แล้วเขียน entity file ตาม choice
        Phase 4 — candidate ที่ status=matched เขียน context append ทันที (ไม่ต้อง confirm)
        """
        candidates    = self.state.candidates
        decisions_map = self.state.decisions_map
        source_doc    = self.state.source_doc

        for c in candidates:
            try:
                agent_type = (c.inferred_type or c.guessed_type or "").strip().upper()

                if agent_type not in specialized_agents:
                    c.status = f"{c.status or 'unknown'}_unsupported_type"
                    print(f"[apply_and_write] SKIP {c.th!r}: agent_type {agent_type!r} ไม่รู้จัก")
                    continue

                write_tool: WriteEntityTool = next(
                    (t for t in specialized_agents[agent_type].tools if isinstance(t, WriteEntityTool)),
                    None,
                )
                if write_tool is None:
                    c.status = f"{c.status or 'unknown'}_no_write_tool"
                    print(f"[apply_and_write] SKIP {c.th!r}: ไม่เจอ WriteEntityTool ใน {agent_type}")
                    continue

                # matched -> append context โดยตรง ไม่ต้องรอ confirm
                if c.status == "matched":
                    print(f"[apply_and_write] MATCHED append: {c.th!r} -> {agent_type}")
                    write_tool.write(
                        entity_name=c.th,
                        content=f"context: {c.context_sentence} | source: {source_doc}",
                        mode="append",
                    )
                    continue

                # decisions_map value มาจาก main.py เป็น ConfirmDecision object อยู่แล้ว
                # (dict.candidate_id: ConfirmDecision) — ไม่ต้องแปลงซ้ำ
                decision: ConfirmDecision | None = decisions_map.get(c.candidate_id)
                if not decision:
                    print(f"[apply_and_write] SKIP {c.th!r}: ไม่มี decision (candidate_id={c.candidate_id!r})")
                    print(f"  decisions_map keys: {list(decisions_map.keys())}")
                    continue

                if decision.choice == "skip":
                    c.status = f"{c.status}_skipped"
                    print(f"[apply_and_write] SKIPPED by user: {c.th!r}")
                    continue

                final_th   = decision.edited_th or c.th
                final_type = (decision.edited_type or agent_type).strip().upper()

                if final_type not in specialized_agents:
                    c.status = f"{c.status}_unsupported_edited_type"
                    print(f"[apply_and_write] SKIP {c.th!r}: edited_type {final_type!r} ไม่รู้จัก")
                    continue

                final_tool: WriteEntityTool = next(
                    (t for t in specialized_agents[final_type].tools if isinstance(t, WriteEntityTool)),
                    None,
                )
                if final_tool is None:
                    c.status = f"{c.status}_no_write_tool"
                    continue

                print(f"[apply_and_write] WRITE {decision.choice}: {final_th!r} -> {final_type}")
                today_str = datetime.now().strftime("%Y-%m-%d")
                final_cn  = decision.edited_cn if hasattr(decision, "edited_cn") and decision.edited_cn else c.cn
                domain_val = (
                    decision.edited_domain
                    if hasattr(decision, "edited_domain") and decision.edited_domain
                    else (c.domain if hasattr(c, "domain") and c.domain else "null")
                ) if final_type == "TECHNICAL_TERM" else "null"

                frontmatter = (
                    f"---\n"
                    f"title: {final_th}\n"
                    f"th: {final_th}\n"
                    f"cn: {final_cn or 'null'}\n"
                    f"entity_type: {final_type}\n"
                    f"domain: {domain_val}\n"
                    f"aliases: []\n"
                    f"source_count: 1\n"
                    f"first_seen: {today_str}\n"
                    f"updated: {today_str}\n"
                    f"tags: [{final_type.lower()}]\n"
                    f"confidence: medium\n"
                    f"---\n"
                )
                body = (
                    f"# {final_th}\n\n"
                    f"## ข้อมูลพื้นฐาน\n"
                    f"- **ภาษาไทย:** {final_th}\n"
                    f"- **ภาษาจีน:** {final_cn or '-'}\n"
                    f"- **ประเภท:** {final_type}\n"
                    f"- **Aliases:** -\n\n"
                    f"## บริบทที่พบ\n"
                    f"| เอกสาร | ประโยคบริบท | วันที่ ingest |\n"
                    f"|--------|-------------|--------------|\n"
                    f"| {source_doc} | {c.context_sentence} | {today_str} |\n\n"
                    f"## หมายเหตุ / Comment\n\n"
                    f"## Cross-references\n"
                )
                final_tool.write(
                    entity_name=final_th,
                    content=frontmatter + body,
                    mode="create",
                )
                c.status = f"{c.status}_{decision.choice}"

            except Exception as e:
                c.status = f"{c.status or 'unknown'}_write_error"
                c.inference_reason = f"{c.inference_reason or ''} [write error: {e}]"
                import traceback
                traceback.print_exc()

        self.state.candidates = candidates
        return candidates

    # ── Step 2: Save JSON output (Phase 5) ────────────────────────────────────
    @listen(apply_and_write)
    def save_json(self, candidates: List[Candidate]) -> list:
        """Phase 5 — รวม output เป็น JSON แล้วเซฟลงดิสก์"""
        output = [
            {
                "th": c.th,
                "cn": c.cn,
                "entity_type": c.inferred_type or c.guessed_type,
                "status": c.status,
                "context_sentence": c.context_sentence,
            }
            for c in self.state.candidates
        ]

        os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name    = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in self.state.source_doc) or "output"
        full_path    = os.path.join(JSON_OUTPUT_DIR, f"{safe_name}_{timestamp}.json")
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        self.state.output = output
        return output

    # ── Step 3: Update log.md (SOUL.md STEP 5-f) ─────────────────────────────
    @listen(save_json)
    def write_log(self, output: list) -> list:
        """SOUL.md STEP 5-f — append log entry ต่อ ingest session"""
        candidates    = self.state.candidates
        new_count     = sum(1 for c in candidates if "confirm" in (c.status or ""))
        matched_count = sum(1 for c in candidates if c.status == "matched")
        skipped_count = sum(1 for c in candidates if "skip" in (c.status or ""))

        # รวบรวม decision log ต่อ entity ที่ user ตัดสินใจ
        decision_log = [
            {"th": c.th, "choice": c.status}
            for c in candidates
            if c.status and any(x in c.status for x in ("confirm", "skip", "edit"))
        ]
        _update_log(self.state.source_doc, new_count, matched_count, skipped_count, decision_log)
        return output

    # ── Step 4: Update index/overview per type + root files (SOUL.md STEP 5d-e) ─
    @listen(write_log)
    def update_corpus_files(self, output: list) -> list:
        """
        SOUL.md STEP 5-d: อัปเดต index.md และ overview.md ของแต่ละ type ที่มีการเปลี่ยนแปลง
        SOUL.md STEP 5-e: อัปเดต root index.md และ summary.md
        """
        candidates = self.state.candidates

        # จัดกลุ่ม entity ที่เพิ่ม/อัปเดตในรอบนี้ตาม type
        changed_types: dict[str, list[dict]] = {}
        for c in candidates:
            # เฉพาะ entity ที่มีการ write จริง (ไม่ใช่ skip หรือ error)
            if not c.status or "skip" in c.status or "error" in c.status or "unsupported" in c.status:
                continue
            final_type = (c.inferred_type or c.guessed_type or "").strip().upper()
            if final_type not in SPECIALIZED_TYPES:
                continue
            changed_types.setdefault(final_type, []).append({
                "th": c.th,
                "cn": c.cn,
                "status": c.status,
            })

        # STEP 5-d: อัปเดต per-type index.md และ overview.md
        for entity_type, entities in changed_types.items():
            try:
                _update_type_index(entity_type, entities)
            except Exception as e:
                print(f"[update_corpus_files] ERROR update {entity_type}/index.md: {e}")
            try:
                _update_type_overview(entity_type, entities)
            except Exception as e:
                print(f"[update_corpus_files] ERROR update {entity_type}/overview.md: {e}")

        # STEP 5-e: อัปเดต root index.md และ summary.md
        try:
            counts      = _count_all_entities()
            new_count   = sum(1 for c in candidates if "confirm" in (c.status or ""))
            matched_count = sum(1 for c in candidates if c.status == "matched")
            _update_root_index(counts)
            _update_summary(counts, self.state.source_doc, new_count, matched_count)
        except Exception as e:
            print(f"[update_corpus_files] ERROR update root files: {e}")

        print(f"[update_corpus_files] อัปเดต corpus files เสร็จสิ้น "
              f"({len(changed_types)} types affected)")
        return output


# ─────────────────────────────────────────────
# Langfuse-wrapped entry points (ใช้ใน FastAPI background tasks)
# ─────────────────────────────────────────────

async def run_extraction_and_specialize(source_doc: str, raw_text: str) -> List[Candidate]:
    """
    Stage 1 entry point — FastAPI background task เรียกตอน POST /ingest
    คืน List[Candidate] พร้อมส่งไป Langfuse ถ้าเปิดใช้งาน
    """
    flow = NERExtractionFlow(source_doc=source_doc, raw_text=raw_text)

    async def _run():
        await flow.kickoff_async()
        return flow.state.candidates

    if not langfuse:
        return await _run()

    with propagate_attributes(session_id=source_doc, tags=["ner-corpus", "stage1-extract-specialize"]):
        with langfuse.start_as_current_observation(
            name="ner_ingest_stage1",
            as_type="span",
            input={"source_doc": source_doc, "raw_text_preview": raw_text[:200]},
        ) as span:
            candidates = await _run()
            span.update(output={
                "candidate_count": len(candidates),
                "statuses": [c.status for c in candidates],
            })
            return candidates


async def resume_write_and_finalize(
    source_doc: str,
    candidates: List[Candidate],
    decisions_map: dict,
) -> list[dict]:
    """
    Stage 2 entry point — FastAPI background task เรียกตอน POST /jobs/{id}/confirm
    คืน list[dict] output สุดท้าย
    """
    flow = NERWriteFlow(source_doc=source_doc, candidates=candidates, decisions_map=decisions_map)

    async def _run():
        await flow.kickoff_async()
        return flow.state.output

    if not langfuse:
        return await _run()

    with propagate_attributes(session_id=source_doc, tags=["ner-corpus", "stage2-confirm-write"]):
        with langfuse.start_as_current_observation(
            name="ner_ingest_stage2",
            as_type="span",
            input={"source_doc": source_doc, "decision_count": len(decisions_map)},
        ) as span:
            output = await _run()
            span.update(output={"result_count": len(output)})
            return output
