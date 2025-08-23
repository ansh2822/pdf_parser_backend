import asyncio
import os
import subprocess
import tempfile
import uuid
from fastapi import WebSocket
from PyPDF2 import PdfReader


def get_temp_dir():
    """Get appropriate temp directory for the platform"""
    if os.name == 'nt':
        return os.environ.get('TEMP', tempfile.gettempdir())


async def parse_pdf_to_md(pdf_bytes: bytes, websocket: WebSocket):
    unique_id = str(uuid.uuid4())
    input_filename = f"input_{unique_id}.pdf"

    tmp_dir = get_temp_dir()
    operation_dir = os.path.join(tmp_dir, f"docling_{unique_id}")

    try:
        os.makedirs(operation_dir, exist_ok=True)
        pdf_path = os.path.join(operation_dir, input_filename)

        # Save PDF
        await websocket.send_text("PROGRESS: 5")
        await websocket.send_text("LOG: Saving PDF file...")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        await websocket.send_text("PROGRESS: 10")
        try:
            total_pages = len(PdfReader(pdf_path).pages)
        except Exception:
            total_pages = None
            await websocket.send_text("LOG: ⚠️ Could not count pages, falling back to generic progress")

        await websocket.send_text("LOG: Preparing docling command...")
        docling_cmd = os.environ.get("DOCLING_CMD", "docling")
        cmd = [docling_cmd, "-vv", input_filename, "--to", "md"]

        await websocket.send_text(f"LOG: Command: {' '.join(cmd)}")
        await websocket.send_text("PROGRESS: 15")
        await websocket.send_text("LOG: Starting PDF processing...")
        await websocket.send_text("PROGRESS: 20")

        loop = asyncio.get_running_loop()

        def run_proc():
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            process = subprocess.Popen(
                cmd,
                cwd=operation_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1,
            )

            processed_pages = 0
            base_progress = 20
            max_progress = 85

            while True:
                line = process.stdout.readline()
                if line == "" and process.poll() is not None:
                    break

                if line:
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_text(f"LOG: {line.strip()}"), loop
                    )

                    if "Finished converting page" in line:
                        processed_pages += 1
                        if total_pages:
                            progress = base_progress + int(
                                (processed_pages / total_pages) * (max_progress - base_progress)
                            )
                        else:
                            progress = base_progress + min(processed_pages * 5, max_progress - base_progress)
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_text(f"PROGRESS: {progress}"), loop
                        )
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
        await websocket.send_text("LOG: Processing document with docling...")
        returncode, stdout, stderr = await loop.run_in_executor(None, run_proc)
        await websocket.send_text("PROGRESS: 90")
        await websocket.send_text("LOG: Docling processing completed")
        if stdout:
            await websocket.send_text(f"LOG stdout: {stdout.strip()}")
        if stderr:
            await websocket.send_text(f"LOG stderr: {stderr.strip()}")
        if returncode != 0:
            raise RuntimeError(f"Docling failed: {stderr.strip()}")
        await websocket.send_text("LOG: Reading converted markdown file...")
        await websocket.send_text("PROGRESS: 95")
        md_path = os.path.join(operation_dir, input_filename.replace(".pdf", ".md"))
        if not os.path.exists(md_path):
            raise RuntimeError(f"Markdown file was not created at {md_path}")
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        await websocket.send_text("PROGRESS: 100")
        await websocket.send_text("✅ Parsing completed.")
        return md_content
    except Exception as e:
        import traceback
        try:
            await websocket.send_text(f"FATAL: {repr(e)}\n{traceback.format_exc()}")
        except:
            pass
        raise
    finally:
        try:
            import shutil
            if os.path.exists(operation_dir):
                shutil.rmtree(operation_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temp directory {operation_dir}: {e}")