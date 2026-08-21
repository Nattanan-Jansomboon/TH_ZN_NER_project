# Handling Non-UTF-8 Source Files

Sources from Windows environments (especially Thai/Chinese bilingual documents exported from local apps) often use encodings other than UTF-8. The `read_file` tool cannot handle them directly. This reference covers detection and conversion.

## Detection

Always run `file` on the file first before attempting to read:

```bash
file "/path/to/file.txt"
```

Common results for bilingual TH/ZN documents:

| `file` output | Encoding | Likely source |
|---------------|----------|---------------|
| `Unicode text, UTF-16, little-endian text, with CRLF line terminators` | UTF-16 LE | Windows Notepad "Unicode" save, MS Office export |
| `ISO-8859 text, with CRLF line terminators` | TIS-620 (Thai) | Legacy Thai text, some government databases |
| `Non-ISO extended-ASCII text` | TIS-620 or Windows-874 | Thai-specific encoding |
| `CJK text, with CRLF line terminators` | GBK or Big5 | Chinese documents from older systems |
| `UTF-8 Unicode text` | UTF-8 | Modern documents — can read directly |

## Conversion with iconv

```bash
# UTF-16 LE → UTF-8 (most common on Windows)
iconv -f UTF-16LE -t UTF-8 "source.txt" > "source_utf8.txt"

# UTF-16 BE → UTF-8 (rare on Windows, common on some servers)
iconv -f UTF-16BE -t UTF-8 "source.txt" > "source_utf8.txt"

# TIS-620 (Thai) → UTF-8
iconv -f TIS-620 -t UTF-8 "source.txt" > "source_utf8.txt"

# GBK (Chinese Simplified) → UTF-8
iconv -f GBK -t UTF-8 "source.txt" > "source_utf8.txt"

# Big5 (Chinese Traditional) → UTF-8
iconv -f BIG5 -t UTF-8 "source.txt" > "source_utf8.txt"
```

## One-liner (read + pipe for inspection)

When you don't need to save the converted copy, pipe directly:

```bash
iconv -f UTF-16LE -t UTF-8 "source.txt" | head -50
```

## Pipeline for NER ingest

Full pipeline from receiving a file to ingesting it:

```bash
# 1. Check encoding
file "/mnt/c/Users/.../file.txt"

# 2. Convert if needed
iconv -f UTF-16LE -t UTF-8 "/mnt/c/Users/.../file.txt" > "/tmp/ingest_utf8.txt"

# 3. Read with read_file
# Use the converted copy
```

## Known pitfalls

- **BOM (Byte Order Mark):** UTF-16 files from Windows often start with a BOM (`\uFEFF`). The `file` command shows "with BOM" in the output. Iconv removes it on conversion.
- **CRLF line endings:** Windows files use `\r\n`. After iconv conversion, line endings remain CRLF. This is harmless for NER extraction but can cause cosmetic issues in display — use `dos2unix` if needed.
- **Mixed encoding:** Rarely, a file may contain segments in different encodings (e.g. Chinese in GBK + Thai in TIS-620 in the same file). For these, manual per-segment conversion is needed. Flag as `confidence: low` if the extraction is uncertain.
- **read_file binary detection:** `read_file` can flag UTF-16 content as "Binary file" because it sees null bytes. This is correct — use `iconv` first.
