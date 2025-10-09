#!/usr/bin/env python3
"""
Cryostat-Style RAG Knowledge Indexer for Secure Email Agent
=========================================================

Privacy-first local indexing system that processes emails and PDFs into
dual-granularity chunks (fine/coarse) with local embeddings and ChromaDB storage.

Features:
- Dual-granularity chunking (350-700 chars fine, 1500-2500 chars coarse)
- Local sentence-transformers embeddings (no cloud dependencies)
- ChromaDB vector storage with metadata
- PDF attachment processing
- Encrypted storage compliance
- Batch processing with progress tracking
"""

import os
import re
import json
import hashlib
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import asyncio
import logging

# Core dependencies
import chromadb
from chromadb.config import Settings
import sentence_transformers
import PyPDF2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Internal imports
from config import config
from email_database import EmailDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeIndexer:
    """
    Privacy-first RAG indexer for email threads and PDF attachments.

    Implements dual-granularity chunking strategy:
    - Fine chunks: 350-700 chars for precise retrieval
    - Coarse chunks: 1500-2500 chars for context/summaries
    """

    def __init__(self,
                 persist_dir: str = None,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 batch_size: int = 100):
        """
        Initialize the knowledge indexer.

        Args:
            persist_dir: Directory for ChromaDB persistence
            embedding_model: Local embedding model name
            batch_size: Batch size for processing
        """
        self.persist_dir = persist_dir or os.path.join(config.data_dir, "vectorstore")
        self.embedding_model_name = embedding_model
        self.batch_size = batch_size

        # Ensure persist directory exists
        os.makedirs(self.persist_dir, exist_ok=True)

        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize embedding model
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = sentence_transformers.SentenceTransformer(
            self.embedding_model_name
        )

        # Initialize collections
        self._init_collections()

        # Chunking parameters
        self.fine_chunk_size = (350, 700)  # min, max
        self.coarse_chunk_size = (1500, 2500)  # min, max

        # Content filters
        self.redaction_patterns = [
            r'\b\d{6}\b',  # OTP codes
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # emails (in signatures)
            r'\b(?:\d{4}[\s-]?){3}\d{4}\b',  # credit cards
            r'\bsecret\s*[:=]\s*\S+\b',  # secrets
        ]

    def _init_collections(self):
        """Initialize ChromaDB collections for fine and coarse chunks."""
        try:
            self.fine_collection = self.chroma_client.get_or_create_collection(
                name="email_fine_chunks",
                metadata={"hnsw:space": "cosine"}
            )
            self.coarse_collection = self.chroma_client.get_or_create_collection(
                name="email_coarse_chunks",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collections initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB collections: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """Clean and redact sensitive information from text."""
        if not text:
            return ""

        # Remove email signatures and boilerplate
        text = re.sub(r'\n--\s*\n.*$', '', text, flags=re.DOTALL)
        text = re.sub(r'\nSent from my \w+.*$', '', text, flags=re.DOTALL)
        text = re.sub(r'\nGet Outlook for \w+.*$', '', text, flags=re.DOTALL)

        # Redact sensitive patterns
        for pattern in self.redaction_patterns:
            text = re.sub(pattern, '[REDACTED]', text, flags=re.IGNORECASE)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _chunk_text(self, text: str, chunk_type: str = "fine") -> List[str]:
        """
        Split text into chunks of appropriate size.

        Args:
            text: Input text to chunk
            chunk_type: "fine" or "coarse"

        Returns:
            List of text chunks
        """
        if chunk_type == "fine":
            min_size, max_size = self.fine_chunk_size
        else:
            min_size, max_size = self.coarse_chunk_size

        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # If adding this sentence would exceed max_size, save current chunk
            if len(current_chunk) + len(sentence) > max_size and len(current_chunk) >= min_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        # Add remaining chunk if it meets minimum size
        if current_chunk and len(current_chunk) >= min_size:
            chunks.append(current_chunk.strip())

        return chunks

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        try:
            embeddings = self.embedding_model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Failed to extract PDF text from {pdf_path}: {e}")
            return ""

    def _get_document_hash(self, content: str, source_id: str) -> str:
        """Generate hash for document deduplication."""
        combined = f"{source_id}:{content}"
        return hashlib.md5(combined.encode()).hexdigest()

    def index_email(self, email_data: Dict) -> bool:
        """
        Index a single email with fine and coarse chunking.

        Args:
            email_data: Email data from SQLite database

        Returns:
            Success status
        """
        try:
            message_id = email_data.get('message_id', '')
            subject = email_data.get('subject', '')
            body = email_data.get('body_text', '')
            sender = email_data.get('sender', '')
            date_received = email_data.get('date_received', '')

            # Create full content
            full_content = f"Subject: {subject}\nFrom: {sender}\nDate: {date_received}\n\n{body}"
            cleaned_content = self._clean_text(full_content)

            if len(cleaned_content) < 50:  # Skip very short emails
                return True

            # Generate document hash for deduplication
            doc_hash = self._get_document_hash(cleaned_content, message_id)

            # Check if already indexed
            existing_fine = self.fine_collection.get(
                where={"doc_hash": doc_hash},
                limit=1
            )
            if existing_fine['ids']:
                logger.debug(f"Email {message_id} already indexed, skipping")
                return True

            # Generate chunks
            fine_chunks = self._chunk_text(cleaned_content, "fine")
            coarse_chunks = self._chunk_text(cleaned_content, "coarse")

            # Process fine chunks
            if fine_chunks:
                fine_embeddings = self._generate_embeddings(fine_chunks)
                fine_ids = [f"email_fine_{message_id}_{i}" for i in range(len(fine_chunks))]
                fine_metadata = [{
                    "source_type": "email",
                    "source_title": subject[:100],
                    "msg_id": message_id,
                    "sender": sender,
                    "date": date_received,
                    "chunk_type": "fine",
                    "chunk_index": i,
                    "doc_hash": doc_hash
                } for i in range(len(fine_chunks))]

                self.fine_collection.add(
                    embeddings=fine_embeddings,
                    documents=fine_chunks,
                    metadatas=fine_metadata,
                    ids=fine_ids
                )

            # Process coarse chunks
            if coarse_chunks:
                coarse_embeddings = self._generate_embeddings(coarse_chunks)
                coarse_ids = [f"email_coarse_{message_id}_{i}" for i in range(len(coarse_chunks))]
                coarse_metadata = [{
                    "source_type": "email",
                    "source_title": subject[:100],
                    "msg_id": message_id,
                    "sender": sender,
                    "date": date_received,
                    "chunk_type": "coarse",
                    "chunk_index": i,
                    "doc_hash": doc_hash
                } for i in range(len(coarse_chunks))]

                self.coarse_collection.add(
                    embeddings=coarse_embeddings,
                    documents=coarse_chunks,
                    metadatas=coarse_metadata,
                    ids=coarse_ids
                )

            logger.debug(f"Indexed email {message_id}: {len(fine_chunks)} fine, {len(coarse_chunks)} coarse chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to index email {email_data.get('message_id', 'unknown')}: {e}")
            return False

    def index_pdf(self, pdf_path: str, source_title: str = None) -> bool:
        """
        Index a PDF file with dual chunking.

        Args:
            pdf_path: Path to PDF file
            source_title: Optional title override

        Returns:
            Success status
        """
        try:
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return False

            # Extract text
            text_content = self._extract_pdf_text(pdf_path)
            if not text_content or len(text_content) < 100:
                logger.warning(f"PDF {pdf_path} has insufficient text content")
                return False

            cleaned_content = self._clean_text(text_content)
            title = source_title or os.path.basename(pdf_path)

            # Generate document hash
            doc_hash = self._get_document_hash(cleaned_content, pdf_path)

            # Check if already indexed
            existing_fine = self.fine_collection.get(
                where={"doc_hash": doc_hash},
                limit=1
            )
            if existing_fine['ids']:
                logger.debug(f"PDF {pdf_path} already indexed, skipping")
                return True

            # Generate chunks
            fine_chunks = self._chunk_text(cleaned_content, "fine")
            coarse_chunks = self._chunk_text(cleaned_content, "coarse")

            # Process fine chunks
            if fine_chunks:
                fine_embeddings = self._generate_embeddings(fine_chunks)
                fine_ids = [f"pdf_fine_{doc_hash}_{i}" for i in range(len(fine_chunks))]
                fine_metadata = [{
                    "source_type": "pdf",
                    "source_title": title,
                    "file_path": pdf_path,
                    "chunk_type": "fine",
                    "chunk_index": i,
                    "doc_hash": doc_hash,
                    "date": datetime.now().isoformat()
                } for i in range(len(fine_chunks))]

                self.fine_collection.add(
                    embeddings=fine_embeddings,
                    documents=fine_chunks,
                    metadatas=fine_metadata,
                    ids=fine_ids
                )

            # Process coarse chunks
            if coarse_chunks:
                coarse_embeddings = self._generate_embeddings(coarse_chunks)
                coarse_ids = [f"pdf_coarse_{doc_hash}_{i}" for i in range(len(coarse_chunks))]
                coarse_metadata = [{
                    "source_type": "pdf",
                    "source_title": title,
                    "file_path": pdf_path,
                    "chunk_type": "coarse",
                    "chunk_index": i,
                    "doc_hash": doc_hash,
                    "date": datetime.now().isoformat()
                } for i in range(len(coarse_chunks))]

                self.coarse_collection.add(
                    embeddings=coarse_embeddings,
                    documents=coarse_chunks,
                    metadatas=coarse_metadata,
                    ids=coarse_ids
                )

            logger.info(f"Indexed PDF {pdf_path}: {len(fine_chunks)} fine, {len(coarse_chunks)} coarse chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to index PDF {pdf_path}: {e}")
            return False

    def batch_index_emails(self, limit: int = None) -> Dict[str, int]:
        """
        Batch index all emails from database.

        Args:
            limit: Optional limit on number of emails to process

        Returns:
            Statistics dictionary
        """
        stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }

        try:
            # Get database connection
            conn = get_connection()
            cursor = conn.cursor()

            # Query emails
            query = """
            SELECT message_id, subject, sender, body_text, date_received
            FROM emails
            WHERE body_text IS NOT NULL AND body_text != ''
            ORDER BY date_received DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            emails = cursor.fetchall()

            logger.info(f"Starting batch indexing of {len(emails)} emails")

            for i, email_row in enumerate(emails):
                stats["processed"] += 1

                # Convert to dict
                email_data = {
                    "message_id": email_row[0],
                    "subject": email_row[1] or "",
                    "sender": email_row[2] or "",
                    "body_text": email_row[3] or "",
                    "date_received": email_row[4] or ""
                }

                # Index email
                if self.index_email(email_data):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

                # Progress logging
                if (i + 1) % 100 == 0:
                    logger.info(f"Processed {i + 1}/{len(emails)} emails")

            conn.close()

            logger.info(f"Batch indexing complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Batch indexing failed: {e}")
            stats["failed"] = stats["processed"] - stats["success"]
            return stats

    def get_index_stats(self) -> Dict[str, int]:
        """Get current index statistics."""
        try:
            fine_count = self.fine_collection.count()
            coarse_count = self.coarse_collection.count()

            # Count by source type
            fine_emails = len(self.fine_collection.get(
                where={"source_type": "email"},
                include=[]
            )['ids'])

            fine_pdfs = len(self.fine_collection.get(
                where={"source_type": "pdf"},
                include=[]
            )['ids'])

            return {
                "total_fine_chunks": fine_count,
                "total_coarse_chunks": coarse_count,
                "email_chunks": fine_emails,
                "pdf_chunks": fine_pdfs,
                "persist_dir": self.persist_dir
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}

    def clear_index(self) -> bool:
        """Clear all indexed data."""
        try:
            self.chroma_client.delete_collection("email_fine_chunks")
            self.chroma_client.delete_collection("email_coarse_chunks")
            self._init_collections()
            logger.info("Index cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False

# Global indexer instance
_indexer_instance = None

def get_indexer() -> KnowledgeIndexer:
    """Get global indexer instance (singleton pattern)."""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = KnowledgeIndexer()
    return _indexer_instance

async def schedule_periodic_indexing():
    """Background task for periodic re-indexing."""
    while True:
        try:
            logger.info("Starting periodic indexing...")
            indexer = get_indexer()
            stats = indexer.batch_index_emails(limit=1000)  # Index recent emails
            logger.info(f"Periodic indexing complete: {stats}")

            # Wait 1 hour before next indexing
            await asyncio.sleep(3600)

        except Exception as e:
            logger.error(f"Periodic indexing failed: {e}")
            await asyncio.sleep(3600)  # Still wait before retrying

if __name__ == "__main__":
    # CLI interface for manual indexing
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Indexer CLI")
    parser.add_argument("--index-emails", action="store_true", help="Index all emails")
    parser.add_argument("--index-pdf", type=str, help="Index specific PDF file")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--clear", action="store_true", help="Clear all indexed data")
    parser.add_argument("--limit", type=int, help="Limit number of emails to index")

    args = parser.parse_args()

    indexer = get_indexer()

    if args.clear:
        if indexer.clear_index():
            print("✅ Index cleared successfully")
        else:
            print("❌ Failed to clear index")

    elif args.index_emails:
        print("🔄 Starting email indexing...")
        stats = indexer.batch_index_emails(limit=args.limit)
        print(f"✅ Email indexing complete: {stats}")

    elif args.index_pdf:
        print(f"🔄 Indexing PDF: {args.index_pdf}")
        if indexer.index_pdf(args.index_pdf):
            print("✅ PDF indexed successfully")
        else:
            print("❌ Failed to index PDF")

    elif args.stats:
        stats = indexer.get_index_stats()
        print("📊 Index Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

    else:
        parser.print_help()