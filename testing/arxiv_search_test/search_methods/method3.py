"""
Method 3: LlamaIndex ArxivReader Implementation
This implementation uses LlamaIndex's ArxivReader to search arXiv papers.
"""

import logging
import time
import os
import tempfile
import re
import shutil
from typing import List, Dict, Any, Optional

# Import compatibility shim for Python 3.13+
from . import cgi_compat

# Configure logging first
logger = logging.getLogger(__name__)

# Try different import paths for LlamaIndex ArxivReader
try:
    from llama_index.readers.papers.arxiv.base import ArxivReader
except (ImportError, ModuleNotFoundError):
    try:
        from llama_index.readers.papers import ArxivReader
    except (ImportError, ModuleNotFoundError):
        try:
            from llama_index_readers_papers import ArxivReader
        except (ImportError, ModuleNotFoundError):
            # If LlamaIndex isn't available, we'll fall back to direct arxiv package usage
            ArxivReader = None
            logger.warning("LlamaIndex ArxivReader not available, will use fallback method")

import arxiv as arxiv_pkg  # We'll use this directly for some cases

# Enable debug printing
DEBUG_PRINT = True

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[SEARCH-M3] {message}")

def create_arxiv_query(structured_terms: Dict[str, List[str]]) -> str:
    """
    Create an arXiv query string from structured terms.
    LlamaIndex's ArxivReader uses the arxiv package which supports advanced query syntax.
    """
    query_parts = []
    
    # Process exact phrases (add to all fields)
    for phrase in structured_terms.get("exact_phrases", []):
        if phrase.strip():
            # Search for exact phrases in title OR abstract
            query_parts.append(f'(ti:"{phrase}" OR abs:"{phrase}")')
    
    # Process title terms
    for term in structured_terms.get("title_terms", []):
        if term.strip():
            query_parts.append(f'ti:"{term}"')
    
    # Process abstract terms
    for term in structured_terms.get("abstract_terms", []):
        if term.strip():
            query_parts.append(f'abs:"{term}"')
    
    # Process general terms
    for term in structured_terms.get("general_terms", []):
        if term.strip():
            query_parts.append(f'all:"{term}"')
    
    # Join all parts with OR
    if query_parts:
        query = " OR ".join(query_parts)
        debug_print(f"Generated query: {query}")
        return query
    else:
        # If no parts, try to use original terms directly
        all_terms = []
        for terms_list in structured_terms.values():
            all_terms.extend([term for term in terms_list if term.strip()])
        
        if all_terms:
            fallback_query = " OR ".join([f'"{term}"' for term in all_terms])
            debug_print(f"Fallback query: {fallback_query}")
            return fallback_query
        
        debug_print("No valid search terms found")
        return ""

def extract_metadata_from_documents(documents, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Extract metadata from LlamaIndex documents and format them into our standard format.
    The documents include both PDF content and abstracts, so we need to combine them.
    """
    debug_print(f"Extracting metadata from {len(documents)} documents")
    
    # Group documents by arXiv ID
    papers_by_id = {}
    for doc in documents:
        metadata = doc.metadata or {}
        arxiv_id = metadata.get("arxiv_id")
        
        if not arxiv_id:
            # Try to extract from file_path
            file_path = metadata.get("file_path", "")
            if file_path:
                # Try to extract arXiv ID from filename
                match = re.search(r'(\d+\.\d+)', file_path)
                if match:
                    arxiv_id = match.group(1)
        
        if arxiv_id:
            if arxiv_id not in papers_by_id:
                papers_by_id[arxiv_id] = {
                    "id": arxiv_id,
                    "title": metadata.get("title", "Unknown Title"),
                    "authors": metadata.get("authors", []),
                    "abstract": metadata.get("abstract", ""),
                    "date": metadata.get("published", ""),
                    "url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    "is_abstract": "abstract" in metadata.get("file_path", "").lower()
                }
            elif "abstract" in metadata.get("file_path", "").lower():
                # Update with abstract data
                papers_by_id[arxiv_id]["abstract"] = doc.text
                papers_by_id[arxiv_id]["is_abstract"] = True
    
    # Convert to list and limit to max_results
    results = []
    for paper_data in list(papers_by_id.values())[:max_results]:
        # Remove the is_abstract field since it's not part of our standard output
        if "is_abstract" in paper_data:
            del paper_data["is_abstract"]
        
        # Clean up abstract if needed
        if paper_data.get("abstract"):
            # Remove excessive whitespace
            paper_data["abstract"] = re.sub(r'\s+', ' ', paper_data["abstract"]).strip()
            
            # Truncate if too long
            if len(paper_data["abstract"]) > 2000:
                paper_data["abstract"] = paper_data["abstract"][:1997] + "..."
        
        results.append(paper_data)
    
    debug_print(f"Extracted metadata for {len(results)} papers")
    return results

def fetch_with_arxiv_directly(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Fallback function to fetch papers using the arxiv package directly
    if the LlamaIndex approach fails.
    """
    debug_print(f"Falling back to direct arxiv package with query: {query}")
    
    try:
        search = arxiv_pkg.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv_pkg.SortCriterion.Relevance,
            sort_order=arxiv_pkg.SortOrder.Descending
        )
        
        results = []
        for paper in search.results():
            arxiv_id = paper.get_short_id()
            
            # Extract authors
            authors = [author.name for author in paper.authors]
            
            # Clean the abstract
            abstract = re.sub(r'\s+', ' ', paper.summary).strip()
            
            # Create paper entry
            paper_data = {
                "id": arxiv_id,
                "title": paper.title,
                "authors": authors,
                "abstract": abstract,
                "date": paper.published.strftime("%Y-%m-%d") if paper.published else "",
                "url": f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            }
            
            results.append(paper_data)
            
            # Respect rate limits
            time.sleep(0.1)
        
        debug_print(f"Retrieved {len(results)} papers from arxiv directly")
        return results
        
    except Exception as e:
        debug_print(f"Error in direct arxiv search: {e}")
        logger.error(f"Error in direct arxiv search: {e}")
        return []

def search_arxiv(
    structured_terms: Dict, 
    max_results: int = 20, 
    original_topics: Optional[List[str]] = None, 
    original_queries: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Method 3: Search arXiv using LlamaIndex's ArxivReader
    
    Args:
        structured_terms: Dictionary of structured search terms
        max_results: Maximum number of results to return
        original_topics: Optional list of original user topics to include directly in search
        original_queries: Optional list of original user queries to include directly in search
        
    Returns:
        List of dictionaries containing paper details
    """
    debug_print(f"Starting LlamaIndex arXiv search with structured terms")
    
    # Create arXiv query
    query = create_arxiv_query(structured_terms)
    
    # Add original topics and queries if provided
    if original_topics or original_queries:
        additional_terms = []
        
        if original_topics:
            additional_terms.extend([f'"{topic}"' for topic in original_topics if topic.strip()])
        
        if original_queries:
            additional_terms.extend([f'"{q}"' for q in original_queries if q.strip()])
        
        if additional_terms:
            if query:
                query = f"({query}) OR ({' OR '.join(additional_terms)})"
            else:
                query = " OR ".join(additional_terms)
    
    if not query:
        debug_print("No valid query created, returning empty results")
        return []
    
    debug_print(f"Final arXiv query: {query}")
    
    # If ArxivReader is not available, use fallback
    if ArxivReader is None:
        debug_print("ArxivReader not available, using direct arxiv package fallback")
        return fetch_with_arxiv_directly(query, max_results)
    
    try:
        # Create a temporary directory for PDF downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            debug_print(f"Created temporary directory for papers: {temp_dir}")
            
            try:
                # Instantiate ArxivReader
                reader = ArxivReader()
                
                # Load data - this downloads PDFs locally then loads them as Document objects
                debug_print(f"Loading data with ArxivReader using query: {query}")
                documents = reader.load_data(
                    search_query=query,
                    papers_dir=temp_dir,
                    max_results=max_results
                )
                
                debug_print(f"Loaded {len(documents)} documents")
                
                # Extract metadata and format into standard output
                return extract_metadata_from_documents(documents, max_results)
                
            except Exception as e:
                debug_print(f"Error using LlamaIndex ArxivReader: {e}")
                logger.error(f"Error using LlamaIndex ArxivReader: {e}")
                
                # Fall back to using arxiv package directly
                return fetch_with_arxiv_directly(query, max_results)
    
    except Exception as outer_e:
        debug_print(f"Error in temporary directory handling: {outer_e}")
        logger.error(f"Error in temporary directory handling: {outer_e}")
        
        # If tempfile fails, use direct approach
        return fetch_with_arxiv_directly(query, max_results)
