#!/usr/bin/env python3
"""
Cryostat-Style RAG Retrieval Layer for Secure Email Agent
=========================================================

High-performance retrieval system with hybrid dense+sparse search,
intelligent query routing, and sub-150ms latency targeting.

Features:
- Hybrid dense vector + BM25 sparse retrieval
- Intelligent query routing (fine vs coarse chunks)
- Query preprocessing and signature removal
- Relevance scoring and result fusion
- Privacy-compliant result formatting
- Performance optimization for <150ms retrieval
"""

import re
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# Core dependencies
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np

# Internal imports
from knowledge_indexer import get_indexer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """Structured result from retrieval operation."""
    text: str
    source_title: str
    source_type: str  # 'email' or 'pdf'
    msg_id: Optional[str] = None
    file_path: Optional[str] = None
    sender: Optional[str] = None
    date: Optional[str] = None
    relevance_score: float = 0.0
    chunk_type: str = "fine"  # 'fine' or 'coarse'
    citation_id: int = 1

class QueryRouter:
    """Intelligent routing for query types to optimize retrieval strategy."""

    def __init__(self):
        # Keywords that indicate fine-grained search needs
        self.fine_keywords = {
            'policy', 'policies', 'document', 'documents', 'doc', 'docs',
            'contract', 'contracts', 'agreement', 'agreements',
            'pdf', 'attachment', 'attachments', 'file', 'files',
            'procedure', 'procedures', 'specification', 'specifications',
            'requirement', 'requirements', 'detail', 'details',
            'clause', 'clauses', 'section', 'sections'
        }

        # Keywords that indicate coarse-grained search needs
        self.coarse_keywords = {
            'timeline', 'timelines', 'summary', 'summaries', 'overview',
            'update', 'updates', 'progress', 'status', 'history',
            'background', 'context', 'discussion', 'conversation',
            'thread', 'threads', 'overall', 'general', 'broad'
        }

        # Question words that often need comprehensive context
        self.context_question_words = {
            'what', 'why', 'how', 'when', 'where', 'who',
            'explain', 'describe', 'tell', 'show'
        }

    def route_query(self, query: str) -> Tuple[str, float]:
        """
        Determine optimal chunk type and confidence for query.

        Args:
            query: Search query string

        Returns:
            Tuple of (chunk_type, confidence_score)
        """
        query_lower = query.lower()
        words = set(re.findall(r'\b\w+\b', query_lower))

        # Calculate scores
        fine_score = len(words.intersection(self.fine_keywords))
        coarse_score = len(words.intersection(self.coarse_keywords))

        # Check for question patterns that need context
        has_context_question = any(
            word in query_lower for word in self.context_question_words
        )

        # Decision logic
        if fine_score > coarse_score:
            return "fine", min(0.9, 0.6 + fine_score * 0.1)
        elif coarse_score > fine_score:
            return "coarse", min(0.9, 0.6 + coarse_score * 0.1)
        elif has_context_question:
            return "coarse", 0.7  # Questions often need broader context
        else:
            return "fine", 0.6  # Default to fine-grained

class QueryPreprocessor:
    """Preprocess queries for optimal retrieval performance."""

    def __init__(self):
        # Common email signature patterns
        self.signature_patterns = [
            r'\n--\s*\n.*$',
            r'\nSent from my \w+.*$',
            r'\nGet Outlook for \w+.*$',
            r'\nBest regards,.*$',
            r'\nThanks,.*$',
            r'\nRegards,.*$',
        ]

        # Date patterns to normalize
        self.date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',
            r'\b\w+\s+\d{1,2},?\s+\d{4}\b',
        ]

        # Stop words for query cleaning
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'among', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can'
        }

    def clean_query(self, query: str) -> str:
        """Clean and normalize query text."""
        if not query:
            return ""

        # Remove signatures
        for pattern in self.signature_patterns:
            query = re.sub(pattern, '', query, flags=re.DOTALL | re.IGNORECASE)

        # Normalize dates to generic tokens
        for pattern in self.date_patterns:
            query = re.sub(pattern, '[DATE]', query)

        # Remove excessive whitespace
        query = re.sub(r'\s+', ' ', query).strip()

        return query

    def extract_keywords(self, query: str, max_keywords: int = 10) -> List[str]:
        """Extract important keywords from query."""
        # Clean query
        query = self.clean_query(query)

        # Extract words
        words = re.findall(r'\b\w+\b', query.lower())

        # Filter stop words and short words
        keywords = [
            word for word in words
            if len(word) > 2 and word not in self.stop_words
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for word in keywords:
            if word not in seen:
                seen.add(word)
                unique_keywords.append(word)

        return unique_keywords[:max_keywords]

class HybridRetriever:
    """
    High-performance hybrid retrieval combining dense vectors and sparse search.

    Implements fusion of ChromaDB vector similarity and BM25-style keyword matching
    for optimal precision and recall.
    """

    def __init__(self, indexer=None):
        """Initialize retriever with indexer instance."""
        self.indexer = indexer or get_indexer()
        self.router = QueryRouter()
        self.preprocessor = QueryPreprocessor()

        # Performance tracking
        self.query_count = 0
        self.total_retrieval_time = 0.0

    def _compute_bm25_score(self, query_terms: List[str], document: str) -> float:
        """
        Compute BM25-style score for sparse retrieval.

        Args:
            query_terms: List of query keywords
            document: Document text

        Returns:
            BM25-style relevance score
        """
        if not query_terms or not document:
            return 0.0

        doc_lower = document.lower()
        doc_length = len(doc_lower.split())

        # BM25 parameters
        k1 = 1.2
        b = 0.75
        avg_doc_length = 100  # Estimated average document length

        score = 0.0
        for term in query_terms:
            # Term frequency in document
            tf = doc_lower.count(term.lower())
            if tf == 0:
                continue

            # Inverse document frequency (simplified)
            idf = 1.0  # Would normally compute from collection stats

            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))

            score += idf * (numerator / denominator)

        return score

    def _fuse_scores(self,
                     vector_results: List[Dict],
                     query_terms: List[str],
                     alpha: float = 0.7) -> List[Dict]:
        """
        Fuse vector similarity and BM25 scores.

        Args:
            vector_results: Results from vector similarity
            query_terms: Query keywords for BM25 scoring
            alpha: Weight for vector scores (1-alpha for BM25)

        Returns:
            Fused and ranked results
        """
        if not vector_results:
            return []

        fused_results = []

        for result in vector_results:
            # Get vector similarity score (assuming it's in distance, convert to similarity)
            vector_distance = result.get('distance', 1.0)
            vector_score = max(0.0, 1.0 - vector_distance)

            # Compute BM25 score
            document = result.get('document', '')
            bm25_score = self._compute_bm25_score(query_terms, document)

            # Normalize BM25 score (simple normalization)
            normalized_bm25 = min(1.0, bm25_score / 5.0)

            # Fuse scores
            final_score = alpha * vector_score + (1 - alpha) * normalized_bm25

            # Add to result
            result['relevance_score'] = final_score
            result['vector_score'] = vector_score
            result['bm25_score'] = normalized_bm25

            fused_results.append(result)

        # Sort by fused score
        fused_results.sort(key=lambda x: x['relevance_score'], reverse=True)

        return fused_results

    def retrieve(self,
                 query: str,
                 k: int = 3,
                 chunk_type: Optional[str] = None,
                 include_metadata: bool = True) -> List[RetrievalResult]:
        """
        Main retrieval function with hybrid search.

        Args:
            query: Search query string
            k: Number of results to return
            chunk_type: Force specific chunk type ('fine' or 'coarse')
            include_metadata: Whether to include full metadata

        Returns:
            List of RetrievalResult objects
        """
        start_time = time.time()
        self.query_count += 1

        try:
            # Preprocess query
            cleaned_query = self.preprocessor.clean_query(query)
            query_keywords = self.preprocessor.extract_keywords(cleaned_query)

            if not cleaned_query:
                logger.warning("Empty query after preprocessing")
                return []

            # Route query if chunk type not specified
            if chunk_type is None:
                chunk_type, confidence = self.router.route_query(cleaned_query)
                logger.debug(f"Query routed to {chunk_type} chunks (confidence: {confidence:.2f})")

            # Select appropriate collection
            if chunk_type == "coarse":
                collection = self.indexer.coarse_collection
            else:
                collection = self.indexer.fine_collection

            # Generate query embedding
            query_embedding = self.indexer.embedding_model.encode([cleaned_query])[0].tolist()

            # Perform vector search
            vector_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k * 2, 20),  # Get more results for fusion
                include=['documents', 'metadatas', 'distances']
            )

            # Convert to standard format
            formatted_results = []
            if vector_results['ids'] and vector_results['ids'][0]:
                for i in range(len(vector_results['ids'][0])):
                    result = {
                        'id': vector_results['ids'][0][i],
                        'document': vector_results['documents'][0][i],
                        'metadata': vector_results['metadatas'][0][i] if vector_results['metadatas'] else {},
                        'distance': vector_results['distances'][0][i] if vector_results['distances'] else 1.0
                    }
                    formatted_results.append(result)

            # Fuse vector and BM25 scores
            fused_results = self._fuse_scores(formatted_results, query_keywords)

            # Convert to RetrievalResult objects
            retrieval_results = []
            for i, result in enumerate(fused_results[:k]):
                metadata = result.get('metadata', {})

                retrieval_result = RetrievalResult(
                    text=result.get('document', ''),
                    source_title=metadata.get('source_title', 'Unknown'),
                    source_type=metadata.get('source_type', 'unknown'),
                    msg_id=metadata.get('msg_id'),
                    file_path=metadata.get('file_path'),
                    sender=metadata.get('sender'),
                    date=metadata.get('date'),
                    relevance_score=result.get('relevance_score', 0.0),
                    chunk_type=metadata.get('chunk_type', chunk_type),
                    citation_id=i + 1
                )
                retrieval_results.append(retrieval_result)

            # Track performance
            retrieval_time = (time.time() - start_time) * 1000
            self.total_retrieval_time += retrieval_time

            logger.debug(f"Retrieved {len(retrieval_results)} results in {retrieval_time:.1f}ms")

            return retrieval_results

        except Exception as e:
            logger.error(f"Retrieval failed for query '{query}': {e}")
            return []

        finally:
            # Always track timing
            retrieval_time = (time.time() - start_time) * 1000
            if retrieval_time > 150:  # Log slow queries
                logger.warning(f"Slow retrieval: {retrieval_time:.1f}ms for query: {query[:50]}...")

    def retrieve_by_message_id(self, message_id: str, k: int = 5) -> List[RetrievalResult]:
        """
        Retrieve related chunks for a specific email message.

        Args:
            message_id: Email message ID
            k: Number of results

        Returns:
            List of related chunks
        """
        try:
            # Search in both collections
            fine_results = self.indexer.fine_collection.get(
                where={"msg_id": message_id},
                include=['documents', 'metadatas']
            )

            coarse_results = self.indexer.coarse_collection.get(
                where={"msg_id": message_id},
                include=['documents', 'metadatas']
            )

            # Combine results
            all_results = []

            # Process fine results
            if fine_results['ids']:
                for i in range(len(fine_results['ids'])):
                    metadata = fine_results['metadatas'][i] if fine_results['metadatas'] else {}
                    result = RetrievalResult(
                        text=fine_results['documents'][i],
                        source_title=metadata.get('source_title', 'Unknown'),
                        source_type=metadata.get('source_type', 'email'),
                        msg_id=message_id,
                        sender=metadata.get('sender'),
                        date=metadata.get('date'),
                        relevance_score=1.0,
                        chunk_type="fine",
                        citation_id=len(all_results) + 1
                    )
                    all_results.append(result)

            # Process coarse results
            if coarse_results['ids']:
                for i in range(len(coarse_results['ids'])):
                    metadata = coarse_results['metadatas'][i] if coarse_results['metadatas'] else {}
                    result = RetrievalResult(
                        text=coarse_results['documents'][i],
                        source_title=metadata.get('source_title', 'Unknown'),
                        source_type=metadata.get('source_type', 'email'),
                        msg_id=message_id,
                        sender=metadata.get('sender'),
                        date=metadata.get('date'),
                        relevance_score=1.0,
                        chunk_type="coarse",
                        citation_id=len(all_results) + 1
                    )
                    all_results.append(result)

            return all_results[:k]

        except Exception as e:
            logger.error(f"Failed to retrieve by message ID {message_id}: {e}")
            return []

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get retrieval performance statistics."""
        avg_time = (self.total_retrieval_time / self.query_count
                   if self.query_count > 0 else 0)

        return {
            "total_queries": self.query_count,
            "total_time_ms": round(self.total_retrieval_time, 2),
            "average_time_ms": round(avg_time, 2),
            "target_time_ms": 150,
            "performance_grade": "A" if avg_time < 150 else "B" if avg_time < 300 else "C"
        }

# Global retriever instance
_retriever_instance = None

def get_retriever() -> HybridRetriever:
    """Get global retriever instance (singleton pattern)."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance

def format_results_for_llm(results: List[RetrievalResult],
                          max_context_length: int = 2000) -> List[Dict[str, Any]]:
    """
    Format retrieval results for LLM consumption.

    Args:
        results: List of RetrievalResult objects
        max_context_length: Maximum total context length

    Returns:
        Formatted evidence list for LLM prompt
    """
    if not results:
        return []

    evidence = []
    current_length = 0

    for result in results:
        # Truncate text if necessary
        text = result.text
        if len(text) > 500:  # Max per snippet
            text = text[:500] + "..."

        # Check if adding this would exceed limit
        if current_length + len(text) > max_context_length:
            break

        evidence.append({
            "id": result.citation_id,
            "text": text,
            "source": result.source_title,
            "type": result.source_type,
            "score": round(result.relevance_score, 3)
        })

        current_length += len(text)

    return evidence

# Test and CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG Retrieval CLI")
    parser.add_argument("--query", type=str, help="Search query")
    parser.add_argument("--k", type=int, default=3, help="Number of results")
    parser.add_argument("--chunk-type", choices=['fine', 'coarse'], help="Force chunk type")
    parser.add_argument("--message-id", type=str, help="Retrieve by message ID")
    parser.add_argument("--stats", action="store_true", help="Show performance stats")
    parser.add_argument("--test", action="store_true", help="Run test queries")

    args = parser.parse_args()

    retriever = get_retriever()

    if args.stats:
        stats = retriever.get_performance_stats()
        print("📊 Retrieval Performance Stats:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

    elif args.message_id:
        print(f"🔍 Retrieving chunks for message: {args.message_id}")
        results = retriever.retrieve_by_message_id(args.message_id, args.k)
        for result in results:
            print(f"\n[{result.citation_id}] {result.source_title}")
            print(f"Type: {result.source_type} | Chunk: {result.chunk_type}")
            print(f"Text: {result.text[:200]}...")

    elif args.query:
        print(f"🔍 Searching: {args.query}")
        results = retriever.retrieve(args.query, args.k, args.chunk_type)

        if results:
            print(f"\n📋 Found {len(results)} results:")
            for result in results:
                print(f"\n[{result.citation_id}] {result.source_title}")
                print(f"Score: {result.relevance_score:.3f} | Type: {result.source_type}")
                print(f"Text: {result.text[:200]}...")
        else:
            print("❌ No results found")

    elif args.test:
        print("🧪 Running test queries...")

        test_queries = [
            "What is our policy on remote work?",
            "Show me the timeline for the project",
            "PDF documents about contracts",
            "Meeting updates from last week",
            "How do we handle customer complaints?"
        ]

        for query in test_queries:
            print(f"\nQuery: {query}")
            start_time = time.time()
            results = retriever.retrieve(query, k=2)
            elapsed = (time.time() - start_time) * 1000

            print(f"Results: {len(results)} in {elapsed:.1f}ms")
            if results:
                print(f"Top result: {results[0].source_title} (score: {results[0].relevance_score:.3f})")

        stats = retriever.get_performance_stats()
        print(f"\n📊 Overall Performance: {stats['average_time_ms']:.1f}ms avg ({stats['performance_grade']} grade)")

    else:
        parser.print_help()