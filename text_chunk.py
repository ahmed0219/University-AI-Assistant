"""
Text Chunking Utilities
Extracts text from PDFs and splits into chunks for embedding.
"""
import os
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_and_chunk_pdf(file, chunk_size=None, chunk_overlap=None):
    """Extract text from a single PDF and split into chunks."""
    reader = PdfReader(file)
    text = "\n".join(
        page.extract_text() for page in reader.pages if page.extract_text()
    )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or CHUNK_SIZE,
        chunk_overlap=chunk_overlap or CHUNK_OVERLAP,
    )
    return splitter.split_text(text)


def extract_and_chunk_pdfs_from_dir(directory_path):
    """Extract and chunk all PDFs in a directory."""
    all_chunks = []
    for filename in sorted(os.listdir(directory_path)):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, "rb") as file:
                chunks = extract_and_chunk_pdf(file)
                all_chunks.extend(chunks)
    return all_chunks

