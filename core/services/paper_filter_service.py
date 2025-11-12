"""
Paper metadata pre-filtering service.
This service fetches metadata for arXiv papers and filters them based on relevance
before the expensive PDF download and processing steps.
"""

import logging
import time
import xml.etree.ElementTree as ET
import urllib.parse
import requests
from typing import List, Dict, Any
from django.db import close_old_connections
from .llm_service import LLM
from ..models import Paper, ResearchSession
import concurrent.futures

# Configure logging
logger = logging.getLogger(__name__)

# Enable debug printing
DEBUG_PRINT = True

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[FILTER] {message}")

def process_arxiv_response(response_text: str, url_to_id_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """Process arXiv API response and extract metadata."""
    batch_metadata = []
    
    try:
        # Parse XML response
        NAMESPACE = {'atom': 'http://www.w3.org/2005/Atom',
                    'arxiv': 'http://arxiv.org/schemas/atom'}
        
        root = ET.fromstring(response_text)
        
        for entry in root.findall('.//atom:entry', NAMESPACE):
            # Extract ID
            id_elem = entry.find('.//atom:id', NAMESPACE)
            if id_elem is None or not id_elem.text:
                continue
            
            id_text = id_elem.text.strip()
            arxiv_id = id_text.split('/')[-1]
            
            # Remove version number if present
            if 'v' in arxiv_id and arxiv_id.split('v')[-1].isdigit():
                base_parts = arxiv_id.split('v')
                if base_parts[-1].isdigit():
                    arxiv_id = 'v'.join(base_parts[:-1])
            
            # Extract title
            title_elem = entry.find('.//atom:title', NAMESPACE)
            title = title_elem.text.strip() if title_elem is not None else "Unknown Title"
            
            # Extract abstract
            summary_elem = entry.find('.//atom:summary', NAMESPACE)
            abstract = summary_elem.text.strip() if summary_elem is not None else ""
            
            # Extract authors
            authors = []
            for author_elem in entry.findall('.//atom:author/atom:name', NAMESPACE):
                if author_elem.text:
                    authors.append(author_elem.text.strip())
            
            # Get URL from mapping - try both with and without version
            url = None
            # First try exact match
            if arxiv_id in url_to_id_map:
                url = url_to_id_map[arxiv_id]
            else:
                # Then try partial match (for versioned IDs)
                for mapped_id, mapped_url in url_to_id_map.items():
                    if arxiv_id in mapped_id or mapped_id in arxiv_id:
                        url = mapped_url
                        break
            
            # If we still couldn't find a match, skip this entry
            if not url:
                debug_print(f"Could not match arxiv_id {arxiv_id} to any URL")
                continue
            
            # Add metadata
            batch_metadata.append({
                'id': arxiv_id,
                'url': url,
                'title': title,
                'abstract': abstract,
                'authors': authors
            })
    
    except Exception as e:
        debug_print(f"Error processing arXiv response: {str(e)}")
    
    return batch_metadata

def fetch_paper_metadata(paper_urls: List[str], batch_size: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch metadata for papers from arXiv based on their URLs.
    
    Args:
        paper_urls: List of arXiv PDF URLs
        batch_size: Number of papers to process in one batch (reduced from 15 to 5)
        
    Returns:
        List of dictionaries containing paper metadata
    """
    debug_print(f"Fetching metadata for {len(paper_urls)} papers in batches of {batch_size}")
    
    all_metadata = []
    batches = [paper_urls[i:i+batch_size] for i in range(0, len(paper_urls), batch_size)]
    
    for batch_index, batch in enumerate(batches):
        debug_print(f"Processing batch {batch_index+1}/{len(batches)}")
        
        # Add delay between batches to respect arXiv rate limits
        if batch_index > 0:  # Don't delay before the first batch
            debug_print(f"Waiting 2 seconds before next arXiv batch to respect rate limits...")
            time.sleep(2)
            
        batch_metadata = []
        
        # Extract arXiv IDs from URLs
        arxiv_ids = []
        url_to_id_map = {}
        
        for url in batch:
            # Extract ID from URL with proper version handling
            if "/pdf/" in url:
                # Extract the ID part
                arxiv_id = url.split("/pdf/")[1].replace(".pdf", "")
                
                # Remove version number (vN) if present
                if 'v' in arxiv_id and arxiv_id.split('v')[-1].isdigit():
                    # Only remove version if it's at the end and has the format vN
                    base_parts = arxiv_id.split('v')
                    if base_parts[-1].isdigit():
                        arxiv_id = 'v'.join(base_parts[:-1])
                        debug_print(f"Removed version from ID: {url.split('/pdf/')[1]} → {arxiv_id}")
                
                arxiv_ids.append(arxiv_id)
                url_to_id_map[arxiv_id] = url
        
        if not arxiv_ids:
            debug_print("No valid arXiv IDs found in batch")
            continue
        
        # Fetch metadata from arXiv API
        try:
            BASE_URL = "http://export.arxiv.org/api/query"
            id_list = ",".join(arxiv_ids)
            api_url = f"{BASE_URL}?id_list={id_list}"
            
            debug_print(f"Fetching metadata from arXiv API: {api_url}")
            
            # Use same User-Agent as in pdf_service.py for consistency
            headers = {
                'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool; mailto:research@example.com)',
                'Accept': 'application/xml'
            }
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            # Check for bad request specifically
            if response.status_code == 400:
                debug_print(f"API returned 400 Bad Request: {response.text}")
                
                # Handle one ID at a time if batch request fails
                debug_print("Falling back to one-by-one requests for IDs")
                for i, single_id in enumerate(arxiv_ids):
                    try:
                        # Add delay between single requests too
                        if i > 0:
                            debug_print(f"Waiting 2 seconds before next single arXiv request...")
                            time.sleep(2)
                            
                        single_url = f"{BASE_URL}?id_list={single_id}"
                        single_response = requests.get(single_url, headers=headers, timeout=30)
                        single_response.raise_for_status()
                        
                        # Process single response
                        single_metadata = process_arxiv_response(single_response.text, {single_id: url_to_id_map[single_id]})
                        all_metadata.extend(single_metadata)
                    except Exception as single_error:
                        debug_print(f"Error processing single ID {single_id}: {str(single_error)}")
                
                # Skip to next batch after processing individual IDs
                continue
            
            # For other status codes, raise for status as usual
            response.raise_for_status()
            
            # Process the batch response
            batch_metadata = process_arxiv_response(response.text, url_to_id_map)
            all_metadata.extend(batch_metadata)
            debug_print(f"Fetched metadata for {len(batch_metadata)} papers in batch {batch_index+1}")
            
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error for batch {batch_index+1}: {http_err}")
            debug_print(f"HTTP ERROR: {str(http_err)}")
            
            # Try to recover by processing IDs individually if not already tried
            if response.status_code != 400:  # We already handled 400 errors above
                debug_print("Falling back to one-by-one requests for IDs after HTTP error")
                for i, single_id in enumerate(arxiv_ids):
                    try:
                        # Add delay between single requests too
                        if i > 0:
                            debug_print(f"Waiting 2 seconds before next single arXiv request...")
                            time.sleep(2)
                            
                        single_url = f"{BASE_URL}?id_list={single_id}"
                        single_response = requests.get(single_url, headers=headers, timeout=30)
                        single_response.raise_for_status()
                        
                        # Process single response
                        single_metadata = process_arxiv_response(single_response.text, {single_id: url_to_id_map[single_id]})
                        all_metadata.extend(single_metadata)
                    except Exception as single_error:
                        debug_print(f"Error processing single ID {single_id}: {str(single_error)}")
        except Exception as e:
            logger.error(f"Error fetching metadata for batch {batch_index+1}: {e}")
            debug_print(f"ERROR: {str(e)}")
    
    debug_print(f"Fetched metadata for {len(all_metadata)}/{len(paper_urls)} papers total")
    return all_metadata

def llm_filter_papers_by_relevance(metadata_list: List[Dict[str, Any]], 
                               topics: List[str], 
                               queries: List[str],
                               search_terms: List[str] = None,
                               explanation: str = "",
                               batch_size: int = 15) -> Dict[str, bool]:
    """
    Filter papers by relevance using LLM evaluation.
    
    Args:
        metadata_list: List of paper metadata dictionaries
        topics: Research topics
        queries: User queries (expanded questions)
        additional_search_terms: Generated search terms used to find papers
        explanation: Explanation of user's research intent
        batch_size: Number of papers to evaluate in one batch
        
    Returns:
        Dictionary mapping paper URLs to relevance boolean
    """
    debug_print(f"Evaluating relevance for {len(metadata_list)} papers")
    
    relevance_map = {}
    batches = [metadata_list[i:i+batch_size] for i in range(0, len(metadata_list), batch_size)]
    
    for batch_index, batch in enumerate(batches):
        debug_print(f"Evaluating batch {batch_index+1}/{len(batches)}")
        
        # Initialize LLM with appropriate model
        llm = LLM(model="openai:gpt-4o-mini")
        
        # Create system prompt
        system_prompt = """
        You are a research paper relevance evaluator for Students in University. Your task is to determine if academic papers shared are relevant to the user's research topics and questions.
        
        Review each paper's metadata (title, abstract) and determine if it's likely to contain information that directly answers the user's research questions.
        
        Respond with a JSON object where:
        - Each key is the paper's ID
        - Each value is a boolean (true = relevant, false = not relevant)
        
        Only mark papers as relevant if they are DIRECTLY relevant to the research topics and questions . Be somewhat strict in your evaluation - papers should clearly address the user's queries to be marked relevant.
        """
        
        # Create user prompt with paper details and research topics/queries
        user_prompt = f"""
        ## USERS RESEARCH QUESTION:\\n\n
        Research Topics: {", ".join(topics)}\n
        
        Specific Research Questions: \n
        {", ".join(queries)}\n\n #####
        """
        
        # Add generated search terms if provided
        if search_terms and len(search_terms) > 0:
            user_prompt += f"""\n\n
        ## GENERATED SEARCH TERMS FOR THE USER TO HELP:
        {", ".join(search_terms)}
        \n\n
        """
            
        # Add explanation if provided
        if explanation and len(explanation) > 0:
            user_prompt += f"""
        ## RESEARCH INTENT EXPLANATION:
        {explanation}
       \n\n
        """
        
        user_prompt += """
        ## PAPERS TO EVALUATE BELOW :
        # \n
        """
        
        # Add paper metadata
        for i, paper in enumerate(batch):
            user_prompt += f"""
            \n\n
            ####\n
            Paper {i+1}:\n
            ID: {paper['id']}\n
            Title: {paper['title']}\n
            Abstract: {paper['abstract']}
            \n #####
            \n\n

            """
        
        user_prompt += """
        \n\n
        Evaluate each paper's relevance to the research topics and questions. Read the abstract for each paper only return th paper ID for paper that will provide useful information based on the user research questions (True). If the paper doesnt relate then return False. If based on the abstract and the title the paper will provide useful information then return True.
        Return a JSON object with paper IDs as keys and boolean values indicating relevance.
        \n\n\n
        """
        
        # Define output schema
        output_schema = {
            "type": "object",
            "relevancePaper": {"type": "boolean"}
        }
        
        try:
            # Get LLM evaluation
            debug_print("Calling LLM for relevance evaluation")
            result = llm.structured_output(user_prompt, output_schema, system_prompt)
            debug_print(f"Received evaluation result from LLM: {result}")
            
            # Process results
            if isinstance(result, dict):
                # Map results to URLs
                for paper in batch:
                    paper_id = paper['id']
                    paper_url = paper['url']
                    
                    if paper_id in result:
                        relevance_map[paper_url] = result[paper_id]
                    else:
                        # Default to relevant if LLM didn't evaluate
                        relevance_map[paper_url] = True
                        debug_print(f"Warning: LLM didn't evaluate paper {paper_id}, defaulting to relevant")
            else:
                debug_print(f"Unexpected LLM response format: {result}")
                # Default all papers in batch to relevant
                for paper in batch:
                    relevance_map[paper['url']] = True
            
        except Exception as e:
            logger.error(f"Error evaluating batch {batch_index+1}: {e}")
            debug_print(f"ERROR: {str(e)}")
            # Default all papers in batch to relevant on error
            for paper in batch:
                relevance_map[paper['url']] = True
    
    # Log results
    relevant_count = sum(1 for is_relevant in relevance_map.values() if is_relevant)
    filtered_count = len(relevance_map) - relevant_count
    debug_print(f"Evaluation results: {relevant_count} relevant, {filtered_count} filtered out")
    
    return relevance_map

def update_paper_status(paper_relevance_map: Dict[str, bool]) -> Dict[str, int]:
    """
    Update paper statuses in the database based on relevance evaluation.
    Irrelevant papers are deleted rather than just being marked as filtered_out.
    
    Args:
        paper_relevance_map: Dictionary mapping paper URLs to relevance boolean
        
    Returns:
        Dictionary with counts of papers in each status
    """
    debug_print(f"Updating status for {len(paper_relevance_map)} papers")
    
    status_counts = {
        'relevant': 0,
        'deleted': 0,
        'error': 0
    }
    
    for url, is_relevant in paper_relevance_map.items():
        try:
            # Find paper in database
            paper = Paper.objects.filter(url=url, status='pending').first()
            
            if paper:
                if is_relevant:
                    # Keep as pending for normal processing
                    status_counts['relevant'] += 1
                else:
                    # Delete irrelevant papers instead of marking them as filtered_out
                    paper_id = str(paper.id)  # Save ID for logging
                    paper.delete()
                    debug_print(f"Deleted irrelevant paper {paper_id}")
                    status_counts['deleted'] += 1
        except Exception as e:
            logger.error(f"Error updating paper status for {url}: {e}")
            debug_print(f"ERROR updating paper status: {str(e)}")
            status_counts['error'] += 1
    
    debug_print(f"Status update results: {status_counts}")
    return status_counts

def filter_paper_urls(paper_urls: List[str], topics: List[str], expanded_questions: List[str], explanation: str, additional_search_terms: List[str] = None, batch_size: int = 15) -> Dict[str, Any]:
    """
    Pre-filter paper URLs before database object creation.
    
    Args:
        paper_urls: List of paper URLs to filter
        topics: Research topics
        expanded_questions: Enhanced questions for relevance evaluation
        explanation: Explanation of user's research intent
        additional_search_terms: Additional search terms for context
        batch_size: Number of papers to evaluate in one batch
        
    Returns:
        Dictionary with filtering results and filtered URL list
    """
    debug_print(f"Pre-filtering {len(paper_urls)} paper URLs")
    
    try:
        if not paper_urls:
            debug_print("No paper URLs to filter")
            return {
                'success': True,
                'papers_processed': 0,
                'papers_relevant': 0,
                'papers_filtered': 0,
                'relevant_urls': [],
                'message': 'No paper URLs to filter'
            }
        
        # Fetch paper metadata
        metadata_list = fetch_paper_metadata(paper_urls, batch_size)
        
        if not metadata_list:
            debug_print("Failed to fetch metadata for any papers")
            return {
                'success': False,
                'papers_processed': 0,
                'papers_relevant': 0,
                'papers_filtered': 0,
                'relevant_urls': paper_urls,  # Return all as relevant if metadata fetch fails
                'message': 'Failed to fetch metadata'
            }
        
        # Filter papers by relevance using all available context
        paper_relevance_map = llm_filter_papers_by_relevance(
            metadata_list, 
            topics, 
            expanded_questions,
            search_terms=additional_search_terms,
            explanation=explanation,
            batch_size=batch_size
        )
        
        # Separate relevant and irrelevant URLs
        relevant_urls = []
        filtered_urls = []
        
        for url, is_relevant in paper_relevance_map.items():
            if is_relevant:
                relevant_urls.append(url)
            else:
                filtered_urls.append(url)
        
        # Count papers for which we couldn't get metadata
        missing_urls = [url for url in paper_urls if url not in paper_relevance_map]
        relevant_urls.extend(missing_urls)  # Include URLs without metadata as relevant by default
        
        debug_print(f"Filtering results: {len(relevant_urls)} relevant, {len(filtered_urls)} filtered out, {len(missing_urls)} missing metadata")
        
        return {
            'success': True,
            'papers_processed': len(paper_relevance_map),
            'papers_relevant': len(relevant_urls),
            'papers_filtered': len(filtered_urls),
            'relevant_urls': relevant_urls,
            'message': 'Pre-filtering completed successfully'
        }
    
    except Exception as e:
        logger.error(f"Error pre-filtering paper URLs: {e}")
        debug_print(f"ERROR: {str(e)}")
        return {
            'success': False,
            'papers_processed': 0,
            'papers_relevant': 0,
            'papers_filtered': 0,
            'relevant_urls': paper_urls,  # Return all as relevant on error
            'message': f'Error: {str(e)}'
        }

def pre_filter_papers_for_session(session_id: str, expanded_questions: List[str], explanation: str, batch_size: int = 15) -> Dict[str, Any]:
    """
    Pre-filter papers for a research session before full PDF processing.
    Legacy function that operates on database objects.
    
    Args:
        session_id: ID of the research session
        expanded_questions: Enhanced questions for relevance evaluation
        explanation: Explanation of user's research intent
        batch_size: Number of papers to evaluate in one batch
        
    Returns:
        Dictionary with filtering results
    """
    debug_print(f"Pre-filtering papers for session {session_id}")
    
    try:
        # Get session and pending papers
        session = ResearchSession.objects.get(id=session_id)
        pending_papers = Paper.objects.filter(session=session, status='pending')
        
        debug_print(f"Found {pending_papers.count()} pending papers")
        
        if not pending_papers:
            debug_print("No pending papers to filter")
            return {
                'success': True,
                'papers_processed': 0,
                'papers_relevant': 0,
                'papers_deleted': 0,
                'message': 'No pending papers to filter'
            }
        
        # Get paper URLs
        paper_urls = [paper.url for paper in pending_papers]
        
        # Fetch paper metadata
        metadata_list = fetch_paper_metadata(paper_urls, batch_size)
        
        if not metadata_list:
            debug_print("Failed to fetch metadata for any papers")
            return {
                'success': False,
                'papers_processed': 0,
                'papers_relevant': 0,
                'papers_deleted': 0,
                'message': 'Failed to fetch metadata'
            }
        
        # Get research topics from session
        topics = session.topics
        
        # Use the expanded questions and explanation passed as parameters
        # instead of overwriting them
        
        # Filter papers by relevance using all available context
        paper_relevance_map = llm_filter_papers_by_relevance(
            metadata_list, 
            topics, 
            expanded_questions,
            search_terms=None,
            explanation=explanation,
            batch_size=batch_size
        )
        
        # Update paper statuses
        status_counts = update_paper_status(paper_relevance_map)
        
        return {
            'success': True,
            'papers_processed': len(paper_relevance_map),
            'papers_relevant': status_counts['relevant'],
            'papers_deleted': status_counts['deleted'],
            'message': 'Pre-filtering completed successfully'
        }
    
    except Exception as e:
        logger.error(f"Error pre-filtering papers for session {session_id}: {e}")
        debug_print(f"ERROR: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }
