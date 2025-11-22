"""
Method 5: ArXiv Advanced Search with Web Scraping
This implementation uses arXiv's advanced search interface via web scraping to leverage
more sophisticated filtering options not available in the API, including:
1. Field-specific searches (title, abstract, author, etc.)
2. Date range filtering
3. Classification filtering
4. Better ordering options

Based on E. J. Keskinoglu's web scraping approach, adapted for structured search terms.
"""

import logging
import requests
import time
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, date

# Configure logging
logger = logging.getLogger(__name__)

# Enable debug printing
DEBUG_PRINT = True

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[SEARCH-M5] {message}")

def preprocess_term(term: str) -> str:
    """Preprocess a search term for optimal arXiv search."""
    # Remove extra whitespace
    term = re.sub(r'\s+', ' ', term).strip()
    return term

def build_advanced_search_params(structured_terms: Dict, original_topics: List[str] = None, 
                                  original_queries: List[str] = None, max_results: int = 20) -> Dict:
    """
    Build parameters for arXiv advanced search from structured terms.
    Returns a dictionary of URL parameters for the advanced search interface.
    """
    debug_print("Building advanced search parameters from structured terms")
    
    # Collect all search terms from different categories
    all_terms = []
    
    # Add exact phrases (highest priority)
    for phrase in structured_terms.get("exact_phrases", []):
        if phrase.strip():
            all_terms.append(preprocess_term(phrase))
    
    # Add title terms
    for term in structured_terms.get("title_terms", []):
        if term.strip():
            all_terms.append(preprocess_term(term))
    
    # Add abstract terms
    for term in structured_terms.get("abstract_terms", []):
        if term.strip():
            all_terms.append(preprocess_term(term))
    
    # Add original topics and queries
    if original_topics:
        for topic in original_topics:
            if topic.strip():
                all_terms.append(preprocess_term(topic))
    
    if original_queries:
        for query in original_queries:
            if query.strip():
                all_terms.append(preprocess_term(query))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_terms = []
    for term in all_terms:
        term_lower = term.lower()
        if term_lower not in seen:
            seen.add(term_lower)
            unique_terms.append(term)
    
    # Combine terms for search (use OR to get broader results, then filter by relevance)
    combined_search = " OR ".join(unique_terms[:5])  # Limit to top 5 terms to avoid overly complex queries
    
    debug_print(f"Combined search query: {combined_search}")
    
    # Build parameters for arXiv advanced search
    # Date range: last 10 years to get recent, relevant papers
    today = date.today()
    from_date = date(today.year - 10, 1, 1)
    
    params = {
        'query': combined_search,
        'searchtype': 'all',
        'abstracts': 'show',  # Show abstracts to extract them
        'size': min(200, max_results * 2),  # Request more than needed for filtering
        'order': '-relevance',  # Order by relevance
        'start': 0
    }
    
    return params

def extract_paper_from_element(result_element) -> Optional[Dict[str, Any]]:
    """
    Extract paper metadata from a BeautifulSoup result element.
    """
    try:
        # Extract arXiv ID - try multiple selectors
        arxiv_id_elem = result_element.find('p', class_='list-title')
        if not arxiv_id_elem:
            arxiv_id_elem = result_element.find('p', class_='list-title is-inline-block')
        
        if not arxiv_id_elem:
            return None
        
        arxiv_link = arxiv_id_elem.find('a')
        if not arxiv_link:
            return None
        
        arxiv_id = arxiv_link.text.strip().replace('arXiv:', '')
        
        # Extract title - try multiple selectors
        title_elem = result_element.find('p', class_='title is-5 mathjax')
        if not title_elem:
            title_elem = result_element.find('p', class_='title')
        title = title_elem.text.strip() if title_elem else "Unknown Title"
        
        # Extract authors
        authors_elem = result_element.find('p', class_='authors')
        authors = []
        if authors_elem:
            author_links = authors_elem.find_all('a')
            authors = [a.text.strip() for a in author_links]
        
        # Extract abstract - try multiple methods
        abstract = ""
        abstract_elem = result_element.find('span', class_='abstract-full')
        if abstract_elem:
            abstract = abstract_elem.text.strip()
        else:
            abstract_elem = result_element.find('span', class_='abstract-short')
            if abstract_elem:
                abstract = abstract_elem.text.strip()
            else:
                abstract_elem = result_element.find('p', class_='abstract mathjax')
                if abstract_elem:
                    abstract = abstract_elem.text.strip()
        
        # Clean abstract text
        abstract = abstract.replace('△ Less', '').replace('▽ More', '').strip()
        
        # Extract date
        date_elem = result_element.find('p', class_='is-size-7')
        date_str = ""
        if date_elem:
            date_text = date_elem.text.strip()
            # Extract date from format like "Submitted 12 March, 2023" or "Submitted 2023-03-12"
            date_match = re.search(r'(\d{1,2}\s+\w+,?\s+\d{4}|\d{4}-\d{2}-\d{2})', date_text)
            if date_match:
                date_str = date_match.group(1)
        
        # Construct PDF URL
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        paper = {
            "id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "date": date_str,
            "url": pdf_url
        }
        
        return paper
        
    except Exception as e:
        logger.error(f"Error extracting paper metadata: {e}")
        return None

def calculate_relevance_score(paper: Dict[str, Any], topics: List[str], queries: List[str]) -> float:
    """
    Calculate a relevance score for a paper based on how well it matches the topics and queries.
    Score ranges from 0.0 to 1.0.
    """
    # Combine all searchable text
    searchable_text = (
        paper.get("title", "").lower() + " " +
        paper.get("abstract", "").lower()
    )
    
    score = 0.0
    total_terms = 0
    
    # Check topics
    for topic in topics:
        if topic:
            total_terms += 1
            topic_lower = topic.lower()
            # Exact phrase match in title (highest weight)
            if topic_lower in paper.get("title", "").lower():
                score += 3.0
            # Exact phrase match in abstract
            elif topic_lower in paper.get("abstract", "").lower():
                score += 2.0
            # Partial word matches
            else:
                words = topic_lower.split()
                matches = sum(1 for word in words if word in searchable_text)
                if matches > 0:
                    score += (matches / len(words))
    
    # Check queries
    for query in queries:
        if query:
            total_terms += 1
            query_lower = query.lower()
            # Exact phrase match in title
            if query_lower in paper.get("title", "").lower():
                score += 3.0
            # Exact phrase match in abstract
            elif query_lower in paper.get("abstract", "").lower():
                score += 2.0
            # Partial word matches
            else:
                words = query_lower.split()
                matches = sum(1 for word in words if word in searchable_text)
                if matches > 0:
                    score += (matches / len(words))
    
    # Normalize score
    if total_terms > 0:
        normalized_score = min(1.0, score / (total_terms * 3.0))
    else:
        normalized_score = 0.0
    
    return normalized_score

def search_arxiv_advanced(
    structured_terms: Dict,
    max_results: int = 20,
    original_topics: List[str] = None,
    original_queries: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Search arXiv using the advanced search web interface with web scraping.
    
    Args:
        structured_terms: Dictionary containing structured search terms from LLM
        max_results: Maximum number of results to return
        original_topics: Optional list of original user topics
        original_queries: Optional list of original user queries
        
    Returns:
        List of dictionaries containing paper details
    """
    debug_print(f"Starting arXiv advanced search (target: {max_results} papers)")
    
    # Build search parameters
    params = build_advanced_search_params(
        structured_terms, 
        original_topics, 
        original_queries,
        max_results
    )
    
    all_papers = []
    seen_ids = set()
    
    try:
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Make request to arXiv search
        debug_print("Sending request to arXiv search...")
        response = requests.get('https://arxiv.org/search/', params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        debug_print(f"Response status: {response.status_code}")
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all result elements
        result_elements = soup.find_all('li', class_='arxiv-result')
        
        debug_print(f"Found {len(result_elements)} result elements on page")
        
        # Extract paper metadata from each result
        for element in result_elements:
            paper = extract_paper_from_element(element)
            if paper and paper["id"] not in seen_ids:
                seen_ids.add(paper["id"])
                all_papers.append(paper)
        
        debug_print(f"Extracted {len(all_papers)} unique papers")
        
        # Calculate relevance scores if we have topics/queries
        if all_papers and (original_topics or original_queries):
            topics = original_topics or []
            queries = original_queries or []
            
            for paper in all_papers:
                paper["relevance_score"] = calculate_relevance_score(paper, topics, queries)
            
            # Sort by relevance score
            all_papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
            
            debug_print(f"Sorted papers by relevance score")
            
            # Remove relevance_score field
            for paper in all_papers:
                if "relevance_score" in paper:
                    del paper["relevance_score"]
        
        # Limit to requested number of results
        final_papers = all_papers[:max_results]
        
        debug_print(f"Returning {len(final_papers)} papers")
        return final_papers
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error: {e}")
        debug_print(f"ERROR: HTTP request failed - {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        debug_print(f"ERROR: {str(e)}")
        return []
