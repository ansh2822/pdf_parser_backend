# R2 Storage Integration + Cross-Platform Fix — Design Spec
**Date:** 2026-04-10

## Overview

Add optional Cloudflare R2 storage to the PDF parser WebSocket API. When the client passes `?store=true` in the WebSocket URL, the parsed Markdown is uploaded to R2 after streaming completes and the public URL is sent back. If `store` is omitted or false, behaviour is unchanged — stream only.

Also fixes a bug where `get_temp_dir()` returns `None` on Mac/Linux, crashing the parser.

---

## Files Changed

### Modified

| File | Change |
|------|--------|
| `app/services/pdf_parser.py` | Fix `get_temp_dir()` to return `tempfile.gettempdir()` on non-Windows |
| `app/routes/parse.py` | Add `store: bool = False` and `filename: Optional[str] = None` query params; call R2 service after parsing when `store=True`; send `R2_URL:` message |
| `app/config.py` | Add R2 env vars with sensible defaults |
| `requirements.txt` | Add `boto3` |

### New

| File | Purpose |
|------|---------|
| `app/services/r2_storage.py` | Single-responsibility R2 upload service |

---

## WebSocket Protocol

### Connecting

```
# Stream only (no change to existing behaviour)
ws://host/ws/parse-pdf

# Stream + upload to R2 (key = {uuid}.md)
ws://host/ws/parse-pdf?store=true

# Stream + upload with custom filename (key = my-report.md)
ws://host/ws/parse-pdf?store=true&filename=my-report
```

### Message sequence

```
→ [bytes]  PDF file

← LOG: ...                          (progress logs, unchanged)
← PROGRESS: N                       (0-100, unchanged)
← DONE: Parsing completed.          (unchanged)
← MARKDOWN_CONTENT_START            (unchanged)
← CHUNK:n:total:<content>           (unchanged)
← MARKDOWN_CONTENT_END              (unchanged)

← R2_URL: https://...               (NEW — only when store=true, upload succeeded)
← R2_ERROR: <reason>                (NEW — only when store=true, upload failed)
```

The `R2_URL` / `R2_ERROR` message is always sent **after** `MARKDOWN_CONTENT_END`, so clients that don't care about storage can ignore any message starting with `R2_`.

---

## R2 Storage Service (`app/services/r2_storage.py`)

```python
upload_markdown(content: str, key: str) -> str
```

- Uses `boto3` S3-compatible client
- Endpoint: `R2_ENDPOINT` env var (default: `https://f6eeda1379f4bcdf2b7b6dad559cd8a7.r2.cloudflarestorage.com`)
- Bucket: `R2_BUCKET` env var (default: `quantum-bytes`)
- `ContentType: text/markdown`
- Returns public URL: `{R2_PUBLIC_URL}/{key}` if `R2_PUBLIC_URL` is set, else `{R2_ENDPOINT}/{R2_BUCKET}/{key}`
- Raises on failure — caller catches and sends `R2_ERROR:` over WebSocket

---

## Config (`app/config.py`)

```python
R2_ENDPOINT        = os.getenv("R2_ENDPOINT", "https://f6eeda1379f4bcdf2b7b6dad559cd8a7.r2.cloudflarestorage.com")
R2_BUCKET          = os.getenv("R2_BUCKET", "quantum-bytes")
R2_ACCESS_KEY_ID   = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_PUBLIC_URL      = os.getenv("R2_PUBLIC_URL", "")  # optional custom domain
```

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| R2 credentials missing | Sends `R2_ERROR: R2 credentials not configured` — does NOT crash connection |
| Upload fails (network/auth) | Sends `R2_ERROR: <boto3 error message>` — client still has full markdown from chunks |
| `store=true` but parse fails | No upload attempted; existing `FATAL:` error flow unchanged |

---

## Environment Variables

```env
R2_ACCESS_KEY_ID=your_access_key_id
R2_SECRET_ACCESS_KEY=your_secret_access_key
R2_BUCKET=quantum-bytes
R2_ENDPOINT=https://f6eeda1379f4bcdf2b7b6dad559cd8a7.r2.cloudflarestorage.com
R2_PUBLIC_URL=                    # optional: set if bucket has a public custom domain
```

Add all four to Railway → service → Variables for production.

---

## Cross-Platform Fix

`get_temp_dir()` in `pdf_parser.py` currently only handles `os.name == 'nt'` (Windows) and falls through with an implicit `None` return on Mac/Linux. On Linux (Railway), `operation_dir` becomes `"None/docling_<uuid>"` and `os.makedirs` fails.

**Fix:**
```python
def get_temp_dir():
    if os.name == 'nt':
        return os.environ.get('TEMP', tempfile.gettempdir())
    return tempfile.gettempdir()
```
