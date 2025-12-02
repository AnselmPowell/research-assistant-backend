"""
Paper metadata pre-filtering service.
This service fetches metadata for arXiv papers using arxiv_pkg for better performance
and filters them based on relevance before the expensive PDF download and processing steps.
"""

import logging
import time
import re
import arxiv as arxiv_pkg
from typing import List, Dict, Any
from django.db import close_old_connections
from .llm_service import LLM
from .embedding_service import filter_papers_by_embedding_similarity
from ..models import Paper, ResearchSession
import concurrent.futures
from ..utils.debug import debug_print

# Configure logging
logger = logging.getLogger(__name__)



def clean_abstract(abstract: str) -> str:
    """Clean and format abstract text for better embedding quality."""
    if not abstract:
        return ""
    # Remove newlines and excessive spaces
    abstract = re.sub(r'\s+', ' ', abstract)
    # Remove any LaTeX-style commands
    abstract = re.sub(r'\\[a-zA-Z]+(\{.*?\})?', '', abstract)
    return abstract.strip()

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

# Removed: process_arxiv_response() function - replaced with arxiv_pkg direct usage

def fetch_paper_metadata(paper_urls: List[str], batch_size: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch metadata for papers from arXiv using arxiv_pkg for better performance and data quality.
    
    Args:
        paper_urls: List of arXiv PDF URLs
        batch_size: Number of papers to process in one batch (used for rate limiting)
        
    Returns:
        List of dictionaries containing paper metadata with cleaned abstracts
    """
    debug_print(f"Fetching metadata for {len(paper_urls)} papers using arxiv_pkg")
    
    all_metadata = []
    
    # Extract arxiv IDs from URLs
    arxiv_ids = []
    url_to_id_map = {}
    
    for url in paper_urls:
        arxiv_id = extract_arxiv_id_from_url(url)
        if arxiv_id and arxiv_id != url:  # Valid ID extracted
            # Remove version number if present
            if 'v' in arxiv_id and arxiv_id.split('v')[-1].isdigit():
                base_parts = arxiv_id.split('v')
                if base_parts[-1].isdigit():
                    clean_id = 'v'.join(base_parts[:-1])
                    debug_print(f"Removed version from ID: {arxiv_id} → {clean_id}")
                    arxiv_id = clean_id
            
            arxiv_ids.append(arxiv_id)
            url_to_id_map[arxiv_id] = url
    
    if not arxiv_ids:
        debug_print("No valid arXiv IDs found in URLs")
        return []
    
    debug_print(f"Extracted {len(arxiv_ids)} valid arXiv IDs")
    
    # Process IDs in batches to respect rate limits
    batches = [arxiv_ids[i:i+batch_size] for i in range(0, len(arxiv_ids), batch_size)]
    
    for batch_index, batch in enumerate(batches):
        debug_print(f"Processing metadata batch {batch_index+1}/{len(batches)} with {len(batch)} papers")
        
        # Add delay between batches to respect arXiv rate limits
        if batch_index > 0:
            debug_print(f"Waiting 2 seconds before next arXiv batch to respect rate limits...")
            time.sleep(2)
        
        # Process each ID in the batch using arxiv_pkg
        for i, arxiv_id in enumerate(batch):
            try:
                # Add delay between individual requests within batch
                if i > 0:
                    time.sleep(0.5)  # Shorter delay within batch
                
                debug_print(f"Fetching metadata for {arxiv_id}")
                
                # Use arxiv package to search for the specific paper
                search = arxiv_pkg.Search(
                    query=f"id:{arxiv_id}",
                    max_results=1,
                    sort_by=arxiv_pkg.SortCriterion.Relevance
                )
                
                # Get the first result
                for result in search.results():
                    try:
                        # Get authors
                        authors = [author.name for author in result.authors]
                        
                        # Get and clean abstract
                        abstract = clean_abstract(result.summary)
                        
                        # Get URL from mapping
                        url = url_to_id_map.get(arxiv_id, f"https://arxiv.org/pdf/{arxiv_id}")
                        
                        # Create metadata object with same structure as before
                        metadata = {
                            'id': arxiv_id,
                            'url': url,
                            'title': result.title.strip(),
                            'abstract': abstract,  # Now cleaned!
                            'authors': authors,
                            'date': result.published.strftime('%Y-%m-%d') if result.published else ""
                        }
                        
                        all_metadata.append(metadata)
                        debug_print(f"Successfully fetched metadata for {arxiv_id}")
                        break  # Only take the first result
                        
                    except Exception as result_error:
                        debug_print(f"Error processing result for {arxiv_id}: {result_error}")
                        logger.error(f"Error processing result for {arxiv_id}: {result_error}")
                
            except Exception as e:
                debug_print(f"Error fetching metadata for {arxiv_id}: {str(e)}")
                logger.error(f"Error fetching metadata for {arxiv_id}: {e}")
                # Continue with next ID instead of failing the whole batch
                continue
    
    debug_print(f"Successfully fetched metadata for {len(all_metadata)}/{len(arxiv_ids)} papers using arxiv_pkg")
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

def embedding_filter_papers_by_relevance(
    metadata_list: List[Dict[str, Any]], 
    topics: List[str], 
    queries: List[str],
    search_terms: List[str] = None,
    explanation: str = "",
    threshold: float = 0.65
) -> tuple:
    """
    Filter papers by relevance using Google Gemini embeddings and cosine similarity.
    
    Args:
        metadata_list: List of paper metadata dictionaries
        topics: Research topics
        queries: User queries (expanded questions)
        search_terms: Generated search terms (optional)
        explanation: Explanation of user's research intent
        threshold: Minimum cosine similarity threshold (default: 0.6)
        
    Returns:
        Tuple of (relevance_map: Dict[str, bool], scores_map: Dict[str, float])
    """
    debug_print(f"Evaluating relevance for {len(metadata_list)} papers using Google embeddings")
    
    if not metadata_list:
        debug_print("No papers to evaluate")
        return {}, {}
    
    try:
        # Prepare documents in the format expected by Google embeddings
        documents = []
        for paper in metadata_list:
            # Combine title and abstract as content
            title = paper.get('title', '').strip()
            abstract = paper.get('abstract', '').strip()
            content = f"{title}. {abstract}" if title and abstract else title or abstract or "No content"
            
            documents.append({
                'content': content,
                'id': paper.get('url', paper.get('id', ''))
            })
        
        # Prepare user query by combining all user inputs
        query_parts = []
        if topics:
            query_parts.extend(topics)
        if queries:
            query_parts.extend(queries)
        if search_terms:
            query_parts.extend(search_terms)
        if explanation:
            query_parts.append(explanation)
        
        user_query = " ".join(query_parts)
        debug_print(f"Combined user query length: {len(user_query)} characters")
        
        # Use Google embeddings to filter papers and get scores
        relevance_map = filter_papers_by_embedding_similarity(
            documents, 
            user_query, 
            threshold
        )
        
        # Get the actual similarity scores for ordering
        scores_map = {}
        try:
            # Import here to avoid circular imports and get scores
            from .embedding_service import get_google_embeddings_batch, calculate_cosine_similarities
            
            # Generate embeddings to get actual scores
            doc_embeddings, query_embedding = get_google_embeddings_batch(documents, user_query)
            
            if doc_embeddings and query_embedding:
                similarities = calculate_cosine_similarities(query_embedding, doc_embeddings)
                for doc, similarity in zip(documents, similarities):
                    scores_map[doc['id']] = float(similarity)
            else:
                # Fallback: use threshold as score for all relevant papers
                for url, is_relevant in relevance_map.items():
                    scores_map[url] = threshold + 0.1 if is_relevant else 0.0
                    
        except Exception as score_error:
            debug_print(f"Error getting similarity scores: {score_error}")
            # Fallback: use threshold as score for all relevant papers
            for url, is_relevant in relevance_map.items():
                scores_map[url] = threshold + 0.1 if is_relevant else 0.0
        
        # Log results
        relevant_count = sum(1 for is_relevant in relevance_map.values() if is_relevant)
        filtered_count = len(relevance_map) - relevant_count
        debug_print(f"Embedding evaluation results: {relevant_count} relevant, {filtered_count} filtered out (threshold: {threshold})")
        
        return relevance_map, scores_map
        
    except Exception as e:
        logger.error(f"Error in embedding-based filtering: {e}")
        debug_print(f"ERROR in embedding filtering: {str(e)}")
        # Return all as relevant on error to avoid breaking the pipeline
        fallback_relevance = {paper.get('url', paper.get('id', '')): True for paper in metadata_list}
        fallback_scores = {paper.get('url', paper.get('id', '')): 0.7 for paper in metadata_list}
        return fallback_relevance, fallback_scores

def apply_interleaved_ordering(url_scores: List[tuple], max_urls: int, workers: int) -> List[str]:
    """
    Apply interleaved ordering to distribute top papers across batches optimally.
    
    Args:
        url_scores: List of (url, score) tuples sorted by score (descending)
        max_urls: Maximum number of URLs to return
        workers: Number of worker threads (batch size)
        
    Returns:
        List of URLs ordered for optimal batch distribution
    """
    debug_print(f"Applying interleaved ordering to {len(url_scores)} URLs with {workers} workers, max {max_urls}")
    
    if len(url_scores) <= max_urls:
        # If we have fewer URLs than max, just return them sorted
        return [url for url, score in url_scores]
    
    # Take only the top max_urls
    top_url_scores = url_scores[:max_urls]
    
    # Apply interleaved distribution
    # This ensures each batch gets high-scoring papers in first positions
    interleaved_urls = []
    
    # Calculate URLs per batch
    urls_per_batch = max_urls // workers
    remainder = max_urls % workers
    
    debug_print(f"Distribution: {urls_per_batch} URLs per batch, {remainder} extra URLs")
    
    # Create batches using round-robin assignment
    batches = [[] for _ in range(workers)]
    
    for i, (url, score) in enumerate(top_url_scores):
        batch_index = i % workers
        batches[batch_index].append((url, score))
    
    # Flatten batches back to single list (preserves interleaved order)
    for batch in batches:
        for url, score in batch:
            interleaved_urls.append(url)
            debug_print(f"Added URL with score {score:.3f}: {url[:50]}...")
    
    debug_print(f"Interleaved ordering complete: {len(interleaved_urls)} URLs ordered")
    return interleaved_urls

def order_urls_by_relevance(
    paper_urls: List[str], 
    relevance_map: Dict[str, bool], 
    scores_map: Dict[str, float],
    direct_urls: List[str] = None,
    max_urls: int = 60,
    workers: int = 4
) -> List[str]:
    """
    Order URLs by relevance score with user-provided URLs prioritized.
    
    Args:
        paper_urls: List of all paper URLs
        relevance_map: Dictionary mapping URLs to relevance boolean
        scores_map: Dictionary mapping URLs to similarity scores
        direct_urls: List of user-provided URLs (get priority)
        max_urls: Maximum number of URLs to return (default: 60)
        workers: Number of worker threads (default: 4)
        
    Returns:
        Ordered list of URLs optimized for batch processing
    """
    debug_print(f"Ordering {len(paper_urls)} URLs by relevance score")
    
    if direct_urls is None:
        direct_urls = []
    
    # Separate direct URLs and arXiv URLs
    direct_relevant = []
    arxiv_relevant = []
    
    # Process all URLs and collect relevant ones with scores
    for url in paper_urls:
        if relevance_map.get(url, False):  # Only include relevant URLs
            score = scores_map.get(url, 0.0)
            
            if url in direct_urls:
                direct_relevant.append((url, score))
                debug_print(f"Direct URL with score {score:.3f}: {url[:50]}...")
            else:
                arxiv_relevant.append((url, score))
    
    # Sort each group by score (highest first)
    direct_relevant.sort(key=lambda x: x[1], reverse=True)
    arxiv_relevant.sort(key=lambda x: x[1], reverse=True)
    
    debug_print(f"Separated URLs: {len(direct_relevant)} direct, {len(arxiv_relevant)} arXiv")
    
    # Prioritize direct URLs but apply URL limit
    if len(direct_relevant) >= max_urls:
        # If we have enough direct URLs, use only them with interleaved ordering
        debug_print(f"Using only direct URLs (have {len(direct_relevant)}, max {max_urls})")
        return apply_interleaved_ordering(direct_relevant, max_urls, workers)
    
    else:
        # Combine direct + arXiv URLs with direct URLs first
        remaining_slots = max_urls - len(direct_relevant)
        arxiv_to_include = arxiv_relevant[:remaining_slots]
        
        debug_print(f"Using {len(direct_relevant)} direct + {len(arxiv_to_include)} arXiv URLs")
        
        # Direct URLs get priority but still apply interleaved ordering
        all_relevant = direct_relevant + arxiv_to_include
        return apply_interleaved_ordering(all_relevant, len(all_relevant), workers)

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
        
        # Filter papers by relevance using Google embeddings (replaced LLM evaluation)
        paper_relevance_map, scores_map = embedding_filter_papers_by_relevance(
            metadata_list, 
            topics, 
            expanded_questions,
            search_terms=additional_search_terms,
            explanation=explanation,
            threshold=0.65  # 65% cosine similarity threshold
        )
        
        # Get all URLs that passed filtering
        relevant_urls_unordered = []
        filtered_urls = []
        
        for url, is_relevant in paper_relevance_map.items():
            if is_relevant:
                relevant_urls_unordered.append(url)
            else:
                filtered_urls.append(url)
        
        # Count papers for which we couldn't get metadata
        missing_urls = [url for url in paper_urls if url not in paper_relevance_map]
        relevant_urls_unordered.extend(missing_urls)  # Include URLs without metadata as relevant by default
        
        # Add default scores for missing URLs
        for url in missing_urls:
            scores_map[url] = 0.65  # Slightly above threshold for missing metadata
        
        # Order URLs by relevance score with optimal batch distribution
        # Note: direct_urls not available here, will be handled in tasks.py integration
        relevant_urls = order_urls_by_relevance(
            relevant_urls_unordered,
            paper_relevance_map,
            scores_map,
            direct_urls=[],  # No direct URL info available at this level
            max_urls=60,
            workers=4
        )
        
        debug_print(f"Filtering and ordering complete: {len(relevant_urls)} relevant URLs ordered by score")
        debug_print(f"Original counts: {len(relevant_urls_unordered)} relevant, {len(filtered_urls)} filtered out, {len(missing_urls)} missing metadata")
        
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
        
        # Filter papers by relevance using Google embeddings (replaced LLM evaluation)
        paper_relevance_map, scores_map = embedding_filter_papers_by_relevance(
            metadata_list, 
            topics, 
            expanded_questions,
            search_terms=None,
            explanation=explanation,
            threshold=0.65  # 65% cosine similarity threshold
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

def filter_paper_urls_with_metadata(
    paper_urls: List[str], 
    existing_metadata: Dict[str, Dict], 
    topics: List[str], 
    expanded_questions: List[str], 
    explanation: str, 
    additional_search_terms: List[str] = None,
    direct_urls: List[str] = None
) -> Dict[str, Any]:
    """
    Pre-filter paper URLs using provided metadata (eliminates duplicate API calls).
    
    Args:
        paper_urls: List of paper URLs to filter
        existing_metadata: Dict mapping URLs to metadata (from arxiv_pkg search)
        topics: Research topics
        expanded_questions: Enhanced questions for relevance evaluation
        explanation: Explanation of user's research intent
        additional_search_terms: Additional search terms for context
        direct_urls: List of user-provided URLs (get priority in ordering)
        
    Returns:
        Dictionary with filtering results and filtered URL list
    """
   
    debug_print(f"Pre-filtering {len(paper_urls)} paper URLs using existing metadata")
    
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
        
        # Use existing metadata instead of fetching new data
        metadata_list = []
        missing_metadata_urls = []
        
        for url in paper_urls:
            if url in existing_metadata:
                metadata_list.append(existing_metadata[url])
                debug_print(f"Using existing metadata for: {url}")
            else:
                # Handle direct URLs or URLs without metadata
                missing_metadata_urls.append(url)
                debug_print(f"No existing metadata for URL: {url}")
        
        debug_print(f"Using existing metadata for {len(metadata_list)} papers, {len(missing_metadata_urls)} URLs without metadata")
        
        if not metadata_list and not missing_metadata_urls:
            debug_print("No metadata available for any papers")
            return {
                'success': False,
                'papers_processed': 0,
                'papers_relevant': 0,
                'papers_filtered': 0,
                'relevant_urls': paper_urls,  # Return all as relevant if no metadata
                'message': 'No metadata available'
            }
        
        # Filter papers by relevance using existing metadata (Google embeddings)
        if metadata_list:
            paper_relevance_map, scores_map = embedding_filter_papers_by_relevance(
                metadata_list, 
                topics, 
                expanded_questions,
                search_terms=additional_search_terms,
                explanation=explanation,
                threshold=0.65  # 65% cosine similarity threshold
            )
        else:
            paper_relevance_map = {}
            scores_map = {}
        
        # Get all URLs that passed filtering
        relevant_urls_unordered = []
        filtered_urls = []
        
        for url, is_relevant in paper_relevance_map.items():
            if is_relevant:
                relevant_urls_unordered.append(url)
            else:
                filtered_urls.append(url)
        
        # Include URLs without metadata as relevant (missing_metadata_urls)
        relevant_urls_unordered.extend(missing_metadata_urls)
        
        # Add default scores for missing URLs
        for url in missing_metadata_urls:
            scores_map[url] = 0.65  # Slightly above threshold for missing metadata
        
        # Order URLs by relevance score with direct URLs prioritized
        if direct_urls is None:
            direct_urls = []
        
        relevant_urls = order_urls_by_relevance(
            relevant_urls_unordered,
            {**paper_relevance_map, **{url: True for url in missing_metadata_urls}},  # Include missing URLs as relevant
            scores_map,
            direct_urls=direct_urls,
            max_urls=60,
            workers=4
        )
        
        # Add URLs without metadata as relevant by default (direct URLs)
        relevant_urls.extend(missing_metadata_urls)
        
        debug_print(f"Filtering results: {len(relevant_urls)} relevant, {len(filtered_urls)} filtered out, {len(missing_metadata_urls)} without metadata")
        
        return {
            'success': True,
            'papers_processed': len(paper_relevance_map),
            'papers_relevant': len(relevant_urls),
            'papers_filtered': len(filtered_urls),
            'relevant_urls': relevant_urls,
            'message': 'Pre-filtering completed successfully using existing metadata'
        }
    
    except Exception as e:
        logger.error(f"Error pre-filtering paper URLs with metadata: {e}")
        debug_print(f"ERROR: {str(e)}")
        return {
            'success': False,
            'papers_processed': 0,
            'papers_relevant': 0,
            'papers_filtered': 0,
            'relevant_urls': paper_urls,  # Return all as relevant on error
            'message': f'Error: {str(e)}'
        }
