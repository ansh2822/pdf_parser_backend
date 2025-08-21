import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.pdf_parser import parse_pdf_to_md

router = APIRouter()

logger = logging.getLogger(__name__)

@router.websocket("/ws/parse-pdf")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        try:
            data = await asyncio.wait_for(
                websocket.receive_bytes(), 
                timeout=60.0  
            )
        except asyncio.TimeoutError:
            await websocket.send_text("FATAL: Upload timeout - please try again with a smaller file")
            return
        
        pdf_bytes = data
        
        max_size = 50 * 1024 * 1024  
        if len(pdf_bytes) > max_size:
            await websocket.send_text(f"FATAL: File too large ({len(pdf_bytes)} bytes). Maximum size is {max_size} bytes")
            return
        
        if not pdf_bytes.startswith(b'%PDF'):
            await websocket.send_text("FATAL: Invalid file format. Please upload a PDF file")
            return
        
        await websocket.send_text(f"LOG: Processing PDF ({len(pdf_bytes)} bytes)")
        
        try:
            md_content = await asyncio.wait_for(
                parse_pdf_to_md(pdf_bytes, websocket),
                timeout=300.0  
            )
        except asyncio.TimeoutError:
            await websocket.send_text("FATAL: Processing timeout - PDF took too long to process")
            return
        
        await websocket.send_text(f'LOG: Received markdown content: {len(md_content)} characters')
        
        if len(md_content) > 100:
            preview = md_content[:100].replace('\n', ' ').replace('\r', ' ')
            await websocket.send_text(f'LOG: Preview: {preview}...')
        
        await websocket.send_text('DONE: Parsing completed.')
        
        await asyncio.sleep(0.1)  
        
        await websocket.send_text('MARKDOWN_CONTENT_START')
        
        chunk_size = 8192  
        total_chunks = (len(md_content) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(md_content), chunk_size):
            if websocket.client_state.name != "CONNECTED":
                logger.warning("WebSocket disconnected during content transmission")
                break
                
            chunk = md_content[i:i+chunk_size]
            chunk_num = (i // chunk_size) + 1
            
            await websocket.send_text(f"CHUNK:{chunk_num}:{total_chunks}:{chunk}")
            
            await asyncio.sleep(0.01)
        
        await websocket.send_text('MARKDOWN_CONTENT_END')
        await websocket.send_text(f'LOG: Transmitted {len(md_content)} characters in {total_chunks} chunks')
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        
    except Exception as e:
        import traceback
        error_msg = f"FATAL: {repr(e)}"
        logger.error(f"WebSocket error: {error_msg}\n{traceback.format_exc()}")
        
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.send_text(error_msg)
        except:
            pass  
            
    finally:
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.close()
        except Exception as e:
            logger.debug(f"Error closing websocket: {e}")

