"""
Method 2: LangChain ArxivAPIWrapper Implementation
This implementation uses LangChain's ArxivAPIWrapper to search arXiv papers.
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional

# Import compatibility shim for Python 3.13+
from . import cgi_compat

# Import LangChain's ArxivAPIWrapper
from langchain_community.utilities.arxiv import ArxivAPIWrapper
import arxiv as arxiv_pkg

# Configure logging
logger = logging.getLogger(__name__)

# Enable debug printing
DEBUG_PRINT = True

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[SEARCH-M2] {message}")

def convert_structured_terms_to_query(structured_terms: Dict[str, List[str]]) -> str:
    """
    Convert structured search terms to a LangChain-compatible arXiv query string.
    LangChain's ArxivAPIWrapper uses the arxiv package which supports advanced query syntax.
    """
    queries = []
    
    # Add exact phrases with quotes
    for phrase in structured_terms.get("exact_phrases", []):
        if phrase.strip():
            # Use the exact phrase in the title or abstract
            queries.append(f'(ti:"{phrase}" OR abs:"{phrase}")')
    
    # Add title-specific searches
    for term in structured_terms.get("title_terms", []):
        if term.strip():
            queries.append(f'ti:"{term}"')
    
    # Add abstract-specific searches
    for term in structured_terms.get("abstract_terms", []):
        if term.strip():
            queries.append(f'abs:"{term}"')
    
    # Add general terms
    for term in structured_terms.get("general_terms", []):
        if term.strip():
            # Search in all fields
            queries.append(f'all:"{term}"')
    
    # Join all queries with OR
    if queries:
        final_query = " OR ".join(queries)
        debug_print(f"Constructed arXiv query: {final_query}")
        return final_query
    else:
        # Fallback: join all non-empty terms with OR
        all_terms = []
        for key in structured_terms:
            all_terms.extend([term for term in structured_terms[key] if term.strip()])
        
        if all_terms:
            final_query = " OR ".join([f'"{term}"' for term in all_terms])
            debug_print(f"Constructed fallback arXiv query: {final_query}")
            return final_query
        else:
            debug_print("No valid terms found, using empty query")
            return ""

def extract_arxiv_id_from_url(url: str) -> str:
    """Extract arXiv ID from a URL."""
    # For PDF URLs like https://arxiv.org/pdf/1234.56789.pdf
    if "/pdf/" in url:
        match = re.search(r'/pdf/([^/]+)(?:\.pdf)?$', url)
        if match:
            return match.group(1)
    
    # For abstract URLs like https://arxiv.org/abs/1234.56789
    elif "/abs/" in url:
        match = re.search(r'/abs/([^/]+)$', url)
        if match:
            return match.group(1)
            
    # If no pattern matches, return the URL as is
    return url

def clean_abstract(abstract: str) -> str:
    """Clean and format abstract text."""
    # Remove newlines and excessive spaces
    abstract = re.sub(r'\s+', ' ', abstract)
    # Remove any LaTeX-style commands
    abstract = re.sub(r'\\[a-zA-Z]+(\{.*?\})?', '', abstract)
    return abstract.strip()

def search_arxiv(
    structured_terms: Dict, 
    max_results: int = 20, 
    original_topics: Optional[List[str]] = None, 
    original_queries: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Method 2: Search arXiv using LangChain's ArxivAPIWrapper
    
    Args:
        structured_terms: Dictionary of structured search terms
        max_results: Maximum number of results to return
        original_topics: Optional list of original user topics to include directly in search
        original_queries: Optional list of original user queries to include directly in search
        
    Returns:
        List of dictionaries containing paper details
    """
    debug_print(f"Starting LangChain arXiv search with structured terms: {structured_terms}")
    
    # Convert structured terms to query string
    query = convert_structured_terms_to_query(structured_terms)
    
    # Add original topics and queries if provided
    if original_topics or original_queries:
        additional_terms = []
        
        if original_topics:
            additional_terms.extend([f'"{topic}"' for topic in original_topics if topic.strip()])
        
        if original_queries:
            additional_terms.extend([f'"{query}"' for query in original_queries if query.strip()])
        
        if additional_terms:
            if query:
                query = f"({query}) OR ({' OR '.join(additional_terms)})"
            else:
                query = " OR ".join(additional_terms)
    
    debug_print(f"Final arXiv query: {query}")
    
    if not query:
        debug_print("Empty query, returning empty results")
        return []
    
    try:
        # Initialize ArxivAPIWrapper
        debug_print(f"Initializing ArxivAPIWrapper with max_results={max_results}")
        arxiv_wrapper = ArxivAPIWrapper(
            top_k_results=max_results,
            load_max_docs=max_results,
            continue_on_failure=True,
            doc_content_chars_max=None,  # no truncation
            load_all_available_meta=True
        )
        
        # Since we don't need to download PDFs for this test, we'll use arxiv package directly
        # for more control over the search results and metadata retrieval
        debug_print(f"Creating arxiv search for query: {query}")
        search = arxiv_pkg.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv_pkg.SortCriterion.Relevance,
            sort_order=arxiv_pkg.SortOrder.Descending
        )
        
        # Fetch results
        debug_print("Fetching results from arXiv")
        results = []
        
        for result in search.results():
            try:
                # Create PDF URL
                arxiv_id = result.get_short_id()
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                
                # Get authors
                authors = [author.name for author in result.authors]
                
                # Get abstract and clean it
                abstract = clean_abstract(result.summary)
                
                # Create paper object
                paper = {
                    "url": pdf_url,
                    "id": arxiv_id,
                    "title": result.title,
                    "abstract": abstract,
                    "authors": authors,
                    "date": result.published.strftime('%Y-%m-%d') if result.published else ""
                }
                
                results.append(paper)
                
                # Respect rate limits
                time.sleep(0.1)
                
            except Exception as e:
                debug_print(f"Error processing result: {e}")
        
        debug_print(f"Found {len(results)} papers")
        return results
        
    except Exception as e:
        debug_print(f"Error during arXiv search: {e}")
        logger.error(f"Error during arXiv search: {e}")
        return []
