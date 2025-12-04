"""
URL verification service for selecting relevant URLs using LLM.
"""

import logging
import re
import urllib.parse
import requests
import xml.etree.ElementTree as ET
import traceback
from .llm_service import LLM
from ..utils.debug import debug_print

logger = logging.getLogger(__name__)

def extract_arxiv_id_from_url(url):
    """Extract arXiv ID from a URL."""
    # Handle PDF URLs
    pdf_pattern = r'arxiv\.org/pdf/([^/]+)\.pdf'
    pdf_match = re.search(pdf_pattern, url)
    if pdf_match:
        return pdf_match.group(1)
    
    # Handle abstract URLs
    abs_pattern = r'arxiv\.org/abs/([^/]+)'
    abs_match = re.search(abs_pattern, url)
    if abs_match:
        return abs_match.group(1)
    
    return None

def get_arxiv_metadata(arxiv_id):
    """Get title and summary for an arXiv paper by ID."""
    try:
        # Define arXiv API constants
        BASE_URL = "http://export.arxiv.org/api/query"
        NAMESPACE = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
        
        # Build the request URL
        url = f"{BASE_URL}?id_list={arxiv_id}"
        
        # Make request
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.text)
        
        # Extract metadata
        entry = root.find('.//atom:entry', NAMESPACE)
        if entry is None:
            return {"title": f"arXiv Paper {arxiv_id}", "summary": "No summary available"}
        
        # Get title
        title_elem = entry.find('.//atom:title', NAMESPACE)
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else f"arXiv Paper {arxiv_id}"
        
        # Get summary
        summary_elem = entry.find('.//atom:summary', NAMESPACE)
        summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else "No summary available"
        
        return {
            "title": title,
            "summary": summary[:500] + "..." if len(summary) > 500 else summary
        }
    
    except Exception as e:
        logger.error(f"Error getting arXiv metadata for {arxiv_id}: {e}")
        return {"title": f"arXiv Paper {arxiv_id}", "summary": "Failed to retrieve summary"}

def get_metadata_for_urls(urls):
    """Get title and summary for a list of URLs."""
    results = []
    
    for url in urls:
        try:
            # For arXiv URLs, get metadata from API
            arxiv_id = extract_arxiv_id_from_url(url)
            
            if arxiv_id:
                metadata = get_arxiv_metadata(arxiv_id)
                results.append({
                    "url": url,
                    "title": metadata["title"],
                    "summary": metadata["summary"]
                })
            else:
                # For non-arXiv URLs, just use the URL as the title
                results.append({
                    "url": url,
                    "title": url.split('/')[-1].replace('.pdf', '').replace('-', ' ').title(),
                    "summary": "No summary available for non-arXiv papers"
                })
        
        except Exception as e:
            logger.error(f"Error getting metadata for URL {url}: {e}")
            results.append({
                "url": url,
                "title": url.split('/')[-1].replace('.pdf', '').replace('-', ' ').title(),
                "summary": "Error retrieving paper information"
            })
    
    return results

def verify_urls_with_llm(search_terms, topics, urls, max_urls=None):
    """
    Use LLM to verify and select the most relevant URLs.
    
    Args:
        search_terms: List of search terms used to find URLs
        topics: Original research topics from the user
        urls: List of URLs to verify
        max_urls: Maximum number of URLs to return (None means LLM decides)
    
    Returns:
        List of verified URLs (strings)
    """
    try:
        # First, get metadata for all URLs
        debug_print(f"Getting metadata for {len(urls)} URLs")
        url_metadata = get_metadata_for_urls(urls)
        debug_print(f"Successfully retrieved metadata for {len(url_metadata)} URLs")
        
        llm = LLM(model="openai:gpt-4o")
        
        # Format URLs with metadata as a numbered list for the prompt
        url_list = ""
        for i, item in enumerate(url_metadata, 1):
            url_list += f"PAPER {i}:\n"
            url_list += f"URL: {item['url']}\n"
            url_list += f"TITLE: {item['title']}\n"
            url_list += f"SUMMARY: {item['summary']}\n\n"
            url_list += "###########################\n\n"
        
        debug_print(f"Prepared metadata for {len(url_metadata)} papers for LLM verification")
        
        # Prepare the system prompt with multiple warnings about empty results
        system_prompt = f"""You are an expert academic research assistant helping to select the most relevant papers for a research query.

Original research topics: {", ".join(topics)}
Search terms: {", ".join(search_terms)}

INSTRUCTIONS:
1. Analyze each paper's title and summary to determine if it's directly relevant to the research topics.
2. Only select papers that are HIGHLY relevant to the specified topics and search terms.
3. Focus on academic quality and direct topical relevance.

IMPORTANT: If NO papers are relevant, return an EMPTY LIST. Do not include irrelevant papers.
REPEAT: If none of the papers are relevant, return NONE of them.
CRITICAL: Return ZERO URLs if none meet high relevance standards.

Return ONLY a JSON array containing the URLs of relevant papers, in order of relevance.
No explanation, no additional text, JUST the array of URLs."""
        
        # Add user-specified max_urls constraint if provided
        if max_urls:
            newline = "\n"
            system_prompt += f"{newline}Select a maximum of {max_urls} most relevant URLs."
            debug_print(f"Limiting results to {max_urls} URLs")
        
        # Create the prompt
        newline = "\n\n"
        prompt = f"Papers to evaluate:{newline}{url_list}"
        
        debug_print("Sending prompt to LLM for URL verification")
        
        # Define the schema for structured output
        output_schema = {
            "type": "array",
            "items": {
                "type": "string",
                "description": "URL of a relevant paper"
            },
            "description": "Array of URLs for papers that are relevant to the research topics"
        }
        
        # Use structured_output instead of complete
        debug_print("Using structured_output to get a proper JSON response")
        result = llm.structured_output(prompt, output_schema, system_prompt)
        
        # The result should already be a list of URLs
        debug_print(f"Received structured response from LLM: {result}")
        
        # Check if we got a valid list of URLs
        if isinstance(result, list):
            debug_print(f"LLM returned {len(result)} relevant URLs")
            return result
        elif isinstance(result, dict) and "error" in result:
            # Handle error case
            debug_print(f"Error in LLM structured output: {result['error']}")
            logger.error(f"LLM structured output error: {result['error']}")
            
            # Fallback: return all URLs if LLM verification fails
            debug_print("LLM verification failed, falling back to all URLs")
            return urls
        else:
            # Unexpected response format
            debug_print(f"Unexpected response format from LLM: {type(result)}")
            logger.error(f"Unexpected response format from LLM: {type(result)}")
            
            # Fallback: return all URLs if LLM verification fails
            debug_print("LLM verification failed, falling back to all URLs")
            return urls
        
    except Exception as e:
        logger.error(f"Error in URL verification: {e}")
        debug_print(f"Exception in URL verification: {str(e)}")
        traceback_str = traceback.format_exc()
        debug_print(f"Traceback: {traceback_str}")
        # Fallback: return all URLs if verification fails
        return urls