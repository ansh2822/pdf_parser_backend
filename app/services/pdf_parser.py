import asyncio
import tempfile
import os
import subprocess

async def parse_pdf_to_md(pdf_bytes: bytes, websocket):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf_path = tmp_pdf.name

    tmp_md = tmp_pdf_path.replace(".pdf", ".md")

    try:
        cmd = ["docling", tmp_pdf_path, "--from", "pdf", "--to", "md", tmp_md]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await websocket.send_text(f"LOG: {line.decode().strip()}")

        await process.wait()

        if process.returncode != 0:
            err = await process.stderr.read()
            await websocket.send_text(f"ERROR: {err.decode()}")
            raise RuntimeError("Docling failed.")

        if not os.path.exists(tmp_md):
            raise RuntimeError("Markdown file was not created.")

        with open(tmp_md, "r", encoding="utf-8") as f:
            md_content = f.read()

        await websocket.send_text("DONE")
        return md_content

    finally:
        if os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)
        if os.path.exists(tmp_md):
            os.remove(tmp_md)
