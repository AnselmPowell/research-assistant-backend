"""
Method 1: Original Implementation (Baseline)
This is the current implementation of the arXiv search functionality,
adapted to return standardized result format.
"""

import logging
import urllib.parse
import requests
import re
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Enable debug printing
DEBUG_PRINT = True

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[SEARCH-M1] {message}")

def build_arxiv_queries(structured_terms: Dict) -> List[str]:
    """Build arXiv queries from structured search terms."""
    debug_print("Building arXiv queries from structured terms")
    queries = []
    
    # Add exact phrase searches in all fields
    for phrase in structured_terms.get("exact_phrases", []):
        if phrase.strip():
            queries.append(f'all:"{phrase}"')
    
    # Add title-specific searches
    for term in structured_terms.get("title_terms", []):
        if term.strip():
            queries.append(f'ti:"{term}"')
    
    # Add abstract-specific searches
    for term in structured_terms.get("abstract_terms", []):
        if term.strip():
            queries.append(f'abs:"{term}"')
    
    # Add general terms with logical OR between them
    general_terms = [term for term in structured_terms.get("general_terms", []) if term.strip()]
    if general_terms:
        general_query = " OR ".join([f'all:"{term}"' for term in general_terms])
        queries.append(f"({general_query})")
    
    # If no valid queries were generated, create a fallback query
    if not queries and structured_terms.get("general_terms"):
        fallback_term = " AND ".join(structured_terms["general_terms"][:2])
        queries.append(f'all:"{fallback_term}"')
    
    debug_print(f"Built {len(queries)} arXiv queries: {queries}")
    return queries

def extract_metadata_from_response(response_text: str) -> List[Dict[str, Any]]:
    """Extract paper metadata from arXiv API response."""
    papers = []
    try:
        # Parse XML response
        root = ET.fromstring(response_text)
        NAMESPACE = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry', NAMESPACE):
            try:
                # Extract ID
                id_elem = entry.find('.//{http://www.w3.org/2005/Atom}id', NAMESPACE)
                if id_elem is None or not id_elem.text:
                    continue
                
                arxiv_id = id_elem.text.split('/')[-1]
                
                # Extract title
                title_elem = entry.find('.//{http://www.w3.org/2005/Atom}title', NAMESPACE)
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Unknown Title"
                
                # Extract abstract
                summary_elem = entry.find('.//{http://www.w3.org/2005/Atom}summary', NAMESPACE)
                abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else "No abstract available"
                
                # Extract authors
                authors = []
                for author_elem in entry.findall('.//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name', NAMESPACE):
                    if author_elem is not None and author_elem.text:
                        authors.append(author_elem.text.strip())
                
                # Extract publication date
                published_elem = entry.find('.//{http://www.w3.org/2005/Atom}published', NAMESPACE)
                published_date = published_elem.text[:10] if published_elem is not None and published_elem.text else ""
                
                # Create PDF URL
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                
                # Add paper to results
                papers.append({
                    "url": pdf_url,
                    "id": arxiv_id,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "date": published_date
                })
                
            except Exception as e:
                debug_print(f"Error extracting metadata for an entry: {e}")
                continue
                
    except Exception as e:
        debug_print(f"Error parsing XML response: {e}")
        # Fallback to regex if XML parsing fails
        try:
            # Extract paper IDs using regex
            id_pattern = r'<id>http://arxiv\.org/abs/([^<]+)</id>'
            arxiv_ids = re.findall(id_pattern, response_text)
            
            # Extract titles using regex
            title_pattern = r'<title>([^<]+)</title>'
            titles = re.findall(title_pattern, response_text)
            
            # Create basic papers with minimal info
            for i, arxiv_id in enumerate(arxiv_ids):
                title = titles[i] if i < len(titles) else "Unknown Title"
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                
                papers.append({
                    "url": pdf_url,
                    "id": arxiv_id,
                    "title": title,
                    "abstract": "Abstract not available due to parsing error",
                    "authors": [],
                    "date": ""
                })
        except Exception as regex_error:
            debug_print(f"Regex fallback also failed: {regex_error}")
    
    return papers

def fetch_metadata_for_urls(urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch metadata for arXiv paper URLs."""
    results = []
    
    # Extract arXiv IDs from URLs
    arxiv_ids = []
    for url in urls:
        if "/pdf/" in url:
            arxiv_id = url.split("/pdf/")[1].replace(".pdf", "")
            arxiv_ids.append(arxiv_id)
    
    # Batch the IDs to avoid overwhelming the arXiv API
    BATCH_SIZE = 10
    for i in range(0, len(arxiv_ids), BATCH_SIZE):
        batch = arxiv_ids[i:i+BATCH_SIZE]
        id_list = ",".join(batch)
        
        try:
            debug_print(f"Fetching metadata for batch {i//BATCH_SIZE + 1}...")
            
            api_url = f"http://export.arxiv.org/api/query?id_list={id_list}"
            headers = {
                'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool; mailto:research@example.com)',
            }
            
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extract metadata from response
            batch_results = extract_metadata_from_response(response.text)
            results.extend(batch_results)
            
            # Sleep to respect rate limits
            if i + BATCH_SIZE < len(arxiv_ids):
                debug_print("Sleeping for 3 seconds to respect arXiv API rate limits...")
                time.sleep(3)
                
        except Exception as e:
            debug_print(f"Error fetching metadata for batch: {e}")
    
    return results

def search_arxiv(
    structured_terms: Dict, 
    max_results: int = 20, 
    original_topics: Optional[List[str]] = None, 
    original_queries: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Method 1: Search arXiv with structured queries (Original Implementation)
    
    Args:
        structured_terms: Dictionary of structured search terms
        max_results: Maximum number of results to return
        original_topics: Optional list of original user topics to include directly in search
        original_queries: Optional list of original user queries to include directly in search
        
    Returns:
        List of dictionaries containing paper details
    """
    # Build queries from the structured terms
    queries = build_arxiv_queries(structured_terms)
    
    # Add direct searches for original topics and queries to ensure they're included
    if original_topics:
        for topic in original_topics:
            if topic.strip():
                # Add original topics as all-field searches
                queries.append(f'all:"{topic}"')
    
    if original_queries:
        for query in original_queries:
            if query.strip():
                # Add original queries as all-field searches
                queries.append(f'all:"{query}"')
    
    debug_print(f"Searching arXiv with {len(queries)} structured queries (including original topics/queries)")
    
    all_results = []
    
    # Calculate results per query to distribute fairly
    if max_results and len(queries) > 0:
        # Add 1 to ensure we get enough results even with duplicates
        results_per_query = min(10, (max_results // len(queries)) + 1)
    else:
        results_per_query = 10
    
    debug_print(f"Fetching up to {results_per_query} results per query to reach target of {max_results}")
    
    # Process queries in order of creation (most specific first)
    for i, query in enumerate(queries):
        # Check if we already have enough results
        if max_results and len(all_results) >= max_results:
            debug_print(f"Already have {len(all_results)} results, stopping search")
            break
        
        # Add delay between queries to respect arXiv rate limits
        if i > 0:  # Don't delay the first request
            debug_print(f"Waiting 2 seconds before next arXiv query to respect rate limits...")
            time.sleep(2)

        try:
            # Create arXiv API request
            BASE_URL = "http://export.arxiv.org/api/query"
            url = f"{BASE_URL}?search_query={urllib.parse.quote(query)}&start=0&max_results={results_per_query}&sortBy=relevance"
            
            debug_print(f"Querying arXiv with: {query}")
            
            # Set User-Agent for consistent tracking
            headers = {
                'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool; mailto:research@example.com)',
                'Accept': 'application/xml'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extract metadata from response
            papers = extract_metadata_from_response(response.text)
            
            # Get URLs from papers
            urls = [paper["url"] for paper in papers]
            debug_print(f"Found {len(urls)} results for query: {query}")
            
            # Add to combined results
            all_results.extend(papers)
            
            # Respect result limit during query processing
            if max_results and len(all_results) >= max_results:
                debug_print(f"Reached target of {max_results} results, stopping search")
                break
                
        except Exception as e:
            logger.error(f"Error with query '{query}': {e}")
            debug_print(f"ERROR: {str(e)}")
    
    # Remove duplicates by URL
    unique_results = []
    seen_urls = set()
    for result in all_results:
        url = result["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    # Apply final result limit
    if max_results and len(unique_results) > max_results:
        debug_print(f"Limiting {len(unique_results)} unique results to {max_results}")
        final_results = unique_results[:max_results]
    else:
        final_results = unique_results
    
    debug_print(f"Returning {len(final_results)} unique results")
    return final_results
