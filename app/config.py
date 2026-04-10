import os
from dotenv import load_dotenv

load_dotenv()

DOC_PARSER_CMD = os.getenv("DOC_PARSER_CMD", "docling")

R2_ENDPOINT = os.getenv(
    "R2_ENDPOINT",
    "https://f6eeda1379f4bcdf2b7b6dad559cd8a7.r2.cloudflarestorage.com",
)
R2_BUCKET = os.getenv("R2_BUCKET", "quantum-bytes")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")
