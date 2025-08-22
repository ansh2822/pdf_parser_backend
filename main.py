import asyncio
import sys
import os

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import parse

app = FastAPI(
    title="PDF Parser API",
    description="API for parsing PDF documents to Markdown using docling",
    version="1.0.0"
)

if os.getenv("ENVIRONMENT") == "production":
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(parse.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdf-parser", "port": os.getenv("PORT", "not set")}

@app.get("/")
async def root():
    return {"message": "PDF Parser API is running", "docs": "/docs"}