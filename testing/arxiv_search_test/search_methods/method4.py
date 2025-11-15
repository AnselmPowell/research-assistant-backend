"""
Method 4: Enhanced arXiv API Implementation
This implementation uses the same direct arXiv API as Method 1 but with enhanced query construction
techniques based on community feedback and best practices for improved relevance.

Key improvements:
1. Always quotes multi-word phrases
2. Uses field-specific queries (ti:, abs:) instead of general all: when possible
3. Combines terms with proper logical operators
4. Prioritizes title and abstract fields for higher relevance
5. Implements post-processing relevance scoring
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
        print(f"[SEARCH-M4] {message}")

def is_multi_word(term: str) -> bool:
    """Check if a term contains multiple words."""
    # Remove special characters and check if there are multiple words
    cleaned = re.sub(r'[^\w\s]', ' ', term)
    words = [w for w in cleaned.split() if w]
    return len(words) > 1

def preprocess_term(term: str) -> str:
    """Preprocess a search term for optimal arXiv search."""
    # Replace hyphens with spaces inside quoted strings
    term = term.replace('-', ' ')
    
    # Remove special characters that might interfere with search
    term = re.sub(r'[^\w\s]', ' ', term)
    
    # Remove extra whitespace
    term = re.sub(r'\s+', ' ', term).strip()
    
    return term

def build_enhanced_arxiv_queries(structured_terms: Dict) -> List[str]:
    """
    Build optimized arXiv queries from structured search terms using best practices:
    1. Quote multi-word phrases
    2. Use field-specific searches
    3. Combine with proper logical operators
    4. Create separate queries for different field combinations for better coverage
    """
    debug_print("Building enhanced arXiv queries from structured terms")
    queries = []
    
    # Process exact phrases with highest priority
    exact_phrase_queries = []
    for phrase in structured_terms.get("exact_phrases", []):
        if not phrase.strip():
            continue
            
        phrase = preprocess_term(phrase)
        
        # Always quote phrases
        if is_multi_word(phrase):
            # Create specific field queries for exact phrases
            exact_phrase_queries.append(f'(ti:"{phrase}" OR abs:"{phrase}")')
        else:
            # For single words, search in all fields
            exact_phrase_queries.append(f'all:"{phrase}"')
    
    # If we have exact phrases, create a combined query
    if exact_phrase_queries:
        combined_exact = " OR ".join(exact_phrase_queries)
        if len(exact_phrase_queries) > 1:
            combined_exact = f"({combined_exact})"
        queries.append(combined_exact)
    
    # Process title terms (high priority)
    title_term_queries = []
    for term in structured_terms.get("title_terms", []):
        if not term.strip():
            continue
            
        term = preprocess_term(term)
        
        # Always quote phrases
        if is_multi_word(term):
            title_term_queries.append(f'ti:"{term}"')
        else:
            title_term_queries.append(f'ti:{term}')
    
    # If we have title terms, create a combined query
    if title_term_queries:
        combined_title = " OR ".join(title_term_queries)
        if len(title_term_queries) > 1:
            combined_title = f"({combined_title})"
        queries.append(combined_title)
    
    # Process abstract terms
    abstract_term_queries = []
    for term in structured_terms.get("abstract_terms", []):
        if not term.strip():
            continue
            
        term = preprocess_term(term)
        
        # Always quote phrases
        if is_multi_word(term):
            abstract_term_queries.append(f'abs:"{term}"')
        else:
            abstract_term_queries.append(f'abs:{term}')
    
    # If we have abstract terms, create a combined query
    if abstract_term_queries:
        combined_abstract = " OR ".join(abstract_term_queries)
        if len(abstract_term_queries) > 1:
            combined_abstract = f"({combined_abstract})"
        queries.append(combined_abstract)
    
    # Process general terms (lowest priority)
    general_term_queries = []
    for term in structured_terms.get("general_terms", []):
        if not term.strip():
            continue
            
        term = preprocess_term(term)
        
        # Always quote multi-word phrases
        if is_multi_word(term):
            general_term_queries.append(f'all:"{term}"')
        else:
            general_term_queries.append(f'all:{term}')
    
    # If we have general terms, create a combined query
    if general_term_queries:
        combined_general = " OR ".join(general_term_queries)
        if len(general_term_queries) > 1:
            combined_general = f"({combined_general})"
        queries.append(combined_general)
    
    # If no valid queries were generated, create a fallback query
    if not queries and structured_terms.get("general_terms"):
        fallback_terms = [preprocess_term(term) for term in structured_terms["general_terms"] if term.strip()]
        if fallback_terms:
            # Create a simple AND query with the first two terms
            if len(fallback_terms) >= 2:
                term1, term2 = fallback_terms[:2]
                if is_multi_word(term1):
                    term1 = f'"{term1}"'
                if is_multi_word(term2):
                    term2 = f'"{term2}"'
                queries.append(f'all:{term1} AND all:{term2}')
            else:
                # Just one term
                term = fallback_terms[0]
                if is_multi_word(term):
                    term = f'"{term}"'
                queries.append(f'all:{term}')
    
    # Create a special combined query for better relevance
    # This combines one term from each category (if available) using AND
    # for more precise results
    combined_parts = []
    
    # Get one term from each category
    if structured_terms.get("exact_phrases"):
        phrase = preprocess_term(structured_terms["exact_phrases"][0])
        if phrase:
            if is_multi_word(phrase):
                combined_parts.append(f'(ti:"{phrase}" OR abs:"{phrase}")')
            else:
                combined_parts.append(f'all:{phrase}')
    
    if structured_terms.get("title_terms") and not combined_parts:  # Only if we don't have an exact phrase
        term = preprocess_term(structured_terms["title_terms"][0])
        if term:
            if is_multi_word(term):
                combined_parts.append(f'ti:"{term}"')
            else:
                combined_parts.append(f'ti:{term}')
    
    if structured_terms.get("abstract_terms") and len(combined_parts) < 2:  # Only if we need more terms
        term = preprocess_term(structured_terms["abstract_terms"][0])
        if term:
            if is_multi_word(term):
                combined_parts.append(f'abs:"{term}"')
            else:
                combined_parts.append(f'abs:{term}')
    
    # Add the combined query if we have multiple parts
    if len(combined_parts) >= 2:
        combined_query = " AND ".join(combined_parts)
        queries.append(combined_query)
    
    debug_print(f"Built {len(queries)} enhanced arXiv queries: {queries}")
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

def calculate_relevance_score(paper: Dict[str, Any], topics: List[str], queries: List[str]) -> float:
    """
    Calculate a relevance score for a paper based on how well it matches the topics and queries.
    This helps with post-filtering to improve result quality.
    """
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    
    # Check for exact matches in title and abstract
    score = 0.0
    
    # Topic matches are more important (multiply by 2)
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower in title:
            score += 2.0  # Higher weight for title matches
        if topic_lower in abstract:
            score += 1.0
            
    # Query matches
    for query in queries:
        query_lower = query.lower()
        if query_lower in title:
            score += 1.5  # Slightly higher weight for title matches
        if query_lower in abstract:
            score += 0.75
    
    # Check for word-level matches (for multi-word topics/queries)
    for topic in topics:
        words = [w.lower() for w in topic.split() if len(w) > 3]  # Only consider words with >3 chars
        for word in words:
            if word in title and word not in topic_lower:
                score += 0.5
            if word in abstract and word not in topic_lower:
                score += 0.25
                
    for query in queries:
        words = [w.lower() for w in query.split() if len(w) > 3]  # Only consider words with >3 chars
        for word in words:
            if word in title and word not in query_lower:
                score += 0.25
            if word in abstract and word not in query_lower:
                score += 0.1
    
    return score

def search_arxiv(
    structured_terms: Dict, 
    max_results: int = 20, 
    original_topics: Optional[List[str]] = None, 
    original_queries: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Method 4: Enhanced arXiv API search with improved query construction and relevance scoring.
    
    Args:
        structured_terms: Dictionary of structured search terms
        max_results: Maximum number of results to return
        original_topics: Optional list of original user topics to include directly in search
        original_queries: Optional list of original user queries to include directly in search
        
    Returns:
        List of dictionaries containing paper details
    """
    # Build queries from the structured terms
    queries = build_enhanced_arxiv_queries(structured_terms)
    
    # Add direct searches for original topics and queries with proper quoting
    if original_topics:
        for topic in original_topics:
            if topic.strip():
                # Add original topics as properly quoted all-field searches
                if is_multi_word(topic):
                    queries.append(f'all:"{preprocess_term(topic)}"')
                else:
                    queries.append(f'all:{preprocess_term(topic)}')
    
    if original_queries:
        for query in original_queries:
            if query.strip():
                # Add original queries as properly quoted all-field searches
                if is_multi_word(query):
                    queries.append(f'all:"{preprocess_term(query)}"')
                else:
                    queries.append(f'all:{preprocess_term(query)}')
    
    debug_print(f"Searching arXiv with {len(queries)} enhanced queries")
    
    all_papers = []
    seen_ids = set()
    
    # Calculate results per query to distribute fairly, but ensure at least 5 per query
    results_per_query = max(5, min(25, (max_results * 2 // len(queries) + 1)))  
    debug_print(f"Fetching up to {results_per_query} results per query to reach target of {max_results}")
    
    # Process queries in order (most specific/structured first)
    for i, query in enumerate(queries):
        # Check if we already have enough results
        if len(all_papers) >= max_results * 2:  # Get twice as many for filtering
            debug_print(f"Already have {len(all_papers)} papers for filtering, stopping search")
            break
        
        # Add delay between queries to respect arXiv rate limits
        if i > 0:  # Don't delay the first request
            debug_print(f"Waiting 2 seconds before next arXiv query to respect rate limits...")
            time.sleep(2)

        try:
            # Create arXiv API request
            BASE_URL = "http://export.arxiv.org/api/query"
            
            # Properly URL-encode the query
            encoded_query = urllib.parse.quote(query)
            url = f"{BASE_URL}?search_query={encoded_query}&start=0&max_results={results_per_query}&sortBy=relevance"
            
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
            
            # Add new papers (avoid duplicates)
            for paper in papers:
                if paper["id"] not in seen_ids:
                    seen_ids.add(paper["id"])
                    all_papers.append(paper)
            
            debug_print(f"Found {len(papers)} papers for query, {len(all_papers)} total unique papers so far")
                
        except Exception as e:
            logger.error(f"Error with query '{query}': {e}")
            debug_print(f"ERROR: {str(e)}")
    
    # If we have too many papers, filter and rank by relevance
    if all_papers and (original_topics or original_queries):
        topics = original_topics or []
        queries = original_queries or []
        
        # Calculate relevance scores
        for paper in all_papers:
            paper["relevance_score"] = calculate_relevance_score(paper, topics, queries)
        
        # Sort by relevance score (highest first)
        all_papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
        
        # Keep only papers with a minimum relevance score
        if len(all_papers) > max_results:
            filtered_papers = [p for p in all_papers if p.get("relevance_score", 0) > 0.5]
            
            # If we have enough papers with good scores, use those
            if len(filtered_papers) >= max_results:
                all_papers = filtered_papers
        
        debug_print(f"After relevance filtering: {len(all_papers)} papers")
        
        # Remove the relevance_score field (not part of our standard output)
        for paper in all_papers:
            if "relevance_score" in paper:
                del paper["relevance_score"]
    
    # Apply final result limit
    if max_results and len(all_papers) > max_results:
        debug_print(f"Limiting {len(all_papers)} papers to {max_results}")
        final_papers = all_papers[:max_results]
    else:
        final_papers = all_papers
    
    debug_print(f"Returning {len(final_papers)} papers")
    return final_papers
