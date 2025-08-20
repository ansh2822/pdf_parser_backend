import os
from dotenv import load_dotenv

load_dotenv()

DOC_PARSER_CMD = os.getenv("DOC_PARSER_CMD", "docling")
