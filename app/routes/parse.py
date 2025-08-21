import asyncio
from fastapi import APIRouter, WebSocket
from app.services.pdf_parser import parse_pdf_to_md

router = APIRouter()

@router.websocket("/ws/parse-pdf")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_bytes()
        pdf_bytes = data
        md_content = await parse_pdf_to_md(pdf_bytes, websocket)
        
        await websocket.send_text(f'LOG: Received markdown content: {len(md_content)} characters')
        await websocket.send_text(f'LOG: First 100 chars: {md_content[:100]}...')
        
        await websocket.send_text('DONE: Parsing completed.')
        
        await asyncio.sleep(0.2)
        
        await websocket.send_text('MARKDOWN_CONTENT_START')
        
        chunk_size = 4096
        for i in range(0, len(md_content), chunk_size):
            chunk = md_content[i:i+chunk_size]
            await websocket.send_text(chunk)
            await asyncio.sleep(0.05)  
        
        await websocket.send_text('MARKDOWN_CONTENT_END')
        await websocket.send_text(f'LOG: Sent {len(md_content)} characters in {(len(md_content)//chunk_size)+1} chunks')
        
    except Exception as e:
        import traceback
        error_msg = f"FATAL: {repr(e)}\n{traceback.format_exc()}"
        await websocket.send_text(error_msg)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass