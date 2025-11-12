"""
Simplified tasks module that doesn't rely on Celery or Channels.
This uses Django's threading capabilities instead.
"""

import logging
import threading
import uuid
import json
import concurrent.futures
from typing import List, Dict, Any
from django.db import transaction, close_old_connections
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ResearchSession, Paper, Note
from .services.llm_service import LLM
from .services.search_service import generate_search_questions, generate_structured_search_terms, search_arxiv_with_structured_queries
from .services.embedding_service import get_embedding
from .services.pdf_service import process_pdf


# Configure logging
logger = logging.getLogger(__name__)

def send_status_update(session_id: str, status: str, message: str = None):
    """Send session status update via WebSocket."""
    try:
        channel_layer = get_channel_layer()
        # Check if channel_layer is None before attempting to use it
        if channel_layer is None:
            logger.warning(f"Channel layer not available - skipping status update for session {session_id}")
            return
            
        async_to_sync(channel_layer.group_send)(
            f"research_{session_id}",
            {
                'type': 'status_message',
                'data': {
                    'stage': status,
                    'message': message or f"Session status: {status}"
                }
            }
        )
        print(f"Sent status update for session {session_id}: {status}")
    except Exception as e:
        logger.error(f"Error sending status update: {e}")
        # Continue execution even if WebSocket update fails

def send_paper_update(session_id: str, paper_data: Dict[str, Any]):
    """Send paper update via WebSocket."""
    try:
        channel_layer = get_channel_layer()
        # Check if channel_layer is None before attempting to use it
        if channel_layer is None:
            logger.warning(f"Channel layer not available - skipping paper update for session {session_id}")
            return
            
        async_to_sync(channel_layer.group_send)(
            f"research_{session_id}",
            {
                'type': 'result_message',
                'data': paper_data
            }
        )
        print(f"Sent paper update for session {session_id}: Paper ID {paper_data.get('paper_id')}")
    except Exception as e:
        logger.error(f"Error sending paper update: {e}")
        # Continue execution even if WebSocket update fails

def process_research_session(session_id: str, settings_data=None):
    """
    Process a research session in a background thread.
    This is a simplified version that doesn't use Celery.
    
    Args:
        session_id: The ID of the session to process
        settings_data: Optional settings data from the request
    """
    # Start a new thread to process the session
    thread = threading.Thread(
        target=_process_research_session_thread,
        args=(session_id, settings_data)
    )
    thread.daemon = True
    thread.start()
    
    return thread

def _process_paper_thread_safe(paper_id: str, search_terms: List[str], query_embedding: List[float], info_queries: List[str], explanation: str = ""):
    """Thread-safe version of process_paper_thread that doesn't update session status."""
    # Close old connections to ensure thread safety with Django's DB connections
    close_old_connections()
    
    try:
        # Get paper
        paper = Paper.objects.get(id=paper_id)
        
        # Update status
        paper.status = 'processing'
        paper.save()
        print(f"Started processing paper {paper.id}: {paper.url}")
        
        # Process the PDF
        result = process_pdf(
            paper.url, 
            search_terms,
            query_embedding, 
            info_queries,
            explanation
        )
        
        # Update paper with results
        with transaction.atomic():
            paper.title = result.get('title', 'Unknown')
            paper.authors = result.get('authors', [])
            paper.year = result.get('year', '')
            paper.summary = result.get('summary', '')
            paper.harvard_reference = result.get('harvard_reference', '')
            paper.total_pages = result.get('total_pages', 0)
            paper.status = result.get('status', 'error')
            paper.error_message = result.get('error_message', '')
            paper.save()
            
            # Create Note objects for each extracted note
            if result.get('status') == 'success' and result.get('notes'):
                for note_data in result.get('notes', []):
                    # Verify justification exists, add default if not
                    if 'justification' not in note_data:
                        default_justification = f"This information relates to the search query '{note_data.get('search_criteria', 'unknown')}' and provides relevant details about {note_data.get('matches_topic', 'the topic')}."
                        note_data['justification'] = default_justification
                        print(f"Added missing justification during note creation: {default_justification}")
                    
                    Note.objects.create(
                        paper=paper,
                        content=note_data.get('content', ''),
                        page_number=note_data.get('page_number', 1),
                        note_type=note_data.get('note_type', 'quote'),
                        search_criteria=note_data.get('search_criteria', ''),
                        matches_topic=note_data.get('matches_topic', ''),
                        justification=note_data.get('justification', ''),  # Added justification field
                        inline_citations=note_data.get('inline_citations', []),
                        reference_list=note_data.get('reference_list', {})
                    )
        
        # Send real-time update to frontend via WebSocket
        try:
            # Prepare paper data for frontend
            paper_data = {
                'paper_id': str(paper.id),
                'title': paper.title,
                'authors': paper.authors,
                'year': paper.year,
                'summary': paper.summary,
                'harvard_reference': paper.harvard_reference,
                'total_pages': paper.total_pages,
                'status': paper.status,
                'notes_count': paper.notes.count(),
                'notes': [note.to_frontend_format() for note in paper.notes.all()]
            }
            
            # Send update to frontend
            send_paper_update(str(paper.session.id), paper_data)
        except Exception as e:
            logger.error(f"Error sending paper update: {e}")
        
        print(f"Completed processing paper {paper.id}")
        return {
            "paper_id": paper_id,
            "status": result.get('status', 'error'),
            "paper_data": {
                "paper_id": str(paper.id),
                "title": paper.title,
                "status": paper.status,
                "notes": [
                    note.to_frontend_format()
                    for note in paper.notes.all()
                ]
            }
        }
    
    except Exception as e:
        logger.error(f"Error processing paper {paper_id}: {e}", exc_info=True)
        try:
            paper = Paper.objects.get(id=paper_id)
            paper.status = 'error'
            paper.error_message = str(e)
            paper.save()
            return {"paper_id": paper_id, "status": "error", "error": str(e)}
        except:
            return {"paper_id": paper_id, "status": "error", "error": "Unknown error and paper not found"}

def _process_research_session_thread(session_id: str, settings_data=None):
    """Background thread to process a research session with parallel paper processing."""
    try:
        # Close old connections to ensure thread safety
        close_old_connections()
        
        # Get session
        try:
            session = ResearchSession.objects.get(id=session_id)
        except ResearchSession.DoesNotExist:
            logger.error(f"Session {session_id} not found")
            return
        
        # Update session status
        session.status = 'searching'
        session.save()
        print(f"Started processing session {session_id}")
        
        # Initialize LLM
        llm = LLM()

        # Debug URLs and topics
        print(f"DEBUG - Session topics: {session.topics}")
        print(f"DEBUG - Session direct URLs: {session.direct_urls}")
        
        # Check if this is a URL-only search (no topics)
        is_url_only_search = len(session.topics) == 0 and len(session.direct_urls) > 0
        print(f"DEBUG - is_url_only_search: {is_url_only_search}")
        # Initialize LLM
        llm = LLM()

        # Get direct URLs from the session
        direct_urls = session.direct_urls
        
        # Simple check for URL-only mode - no topics but has URLs
        is_url_only_search = len(session.topics) == 0 and len(direct_urls) > 0

        # Handle URL-only searches more efficiently
        if is_url_only_search:
            print(f"URL-only search detected with {len(direct_urls)} direct URLs, skipping ArXiv search")
            
            # Send notification about URL-only mode
            send_status_update(
                str(session.id),
                'searching',
                f"Processing {len(direct_urls)} user-provided URLs directly (fast mode)"
            )
            
            # Skip ArXiv search completely
            all_candidate_urls = direct_urls
            arxiv_urls = []
            
            # Still need to generate expanded questions for PDF content extraction
            expanded_questions, explanation = generate_search_questions(llm, [], session.info_queries)
            
            # Create empty search structure for compatibility with later code
            # search_structure = {
            #     "exact_phrases": [],
            #     "title_terms": [],
            #     "abstract_terms": [],
            #     "general_terms": []
            # }

            search_structure = generate_structured_search_terms(llm, [], session.info_queries)
            
            # Generate query embedding for PDF processing
            query_embedding = get_embedding(" ".join(expanded_questions))
        else:
            # Original code for searches with topics
            # Generate structured search terms for better ArXiv results
            search_structure = generate_structured_search_terms(llm, session.topics, session.info_queries)
            print(f"Generated search structure with {len(search_structure.get('exact_phrases', []))} exact phrases, "
                f"{len(search_structure.get('title_terms', []))} title terms, "
                f"{len(search_structure.get('abstract_terms', []))} abstract terms, and "
                f"{len(search_structure.get('general_terms', []))} general terms")
            
            # Generate expanded questions for embedding creation
            expanded_questions, explanation = generate_search_questions(llm, session.topics, session.info_queries)
            print(f"Generated expanded questions: {expanded_questions}")
            
            # Get query embedding for PDF processing
            query_embedding = get_embedding(" ".join(expanded_questions))
            
            # Handle direct URLs first
            direct_urls = session.direct_urls
            
            # Search ArXiv with structured queries for better results
            arxiv_urls = []
            arxiv_urls = search_arxiv_with_structured_queries(
                search_structure,
                original_topics=session.topics,
                original_queries=session.info_queries
            )
            print(f"Found {len(arxiv_urls)} papers from arXiv search using structured queries (including original topics/queries)")
            
            # Combine URLs, prioritizing direct URLs
            all_candidate_urls = direct_urls + [url for url in arxiv_urls if url not in direct_urls]
        
        if not all_candidate_urls:
            session.status = 'completed'
            session.save()
            print(f"No papers found for session {session_id}, marking as complete")
            return
            
        # Try to get the maxSources setting from the passed settings_data
        try:
            max_urls = None
            if settings_data and 'maxSources' in settings_data:
                max_urls = int(settings_data['maxSources'])
            else:
                # Fallback to environment settings
                max_urls = getattr(settings, 'MAX_PAPERS', 30)
        except Exception as e:
            logger.error(f"Error getting max_urls: {e}")
            max_urls = 30  # Default fallback

        max_urls = 100
        print("max_urls, ", max_urls)
        print("len(all_candidate_urls), ", len(all_candidate_urls))
    
        # Apply URL limit if specified
        if len(all_candidate_urls) > max_urls:
            # Prioritize direct URLs
            direct_url_count = len(direct_urls)
            
            if direct_url_count >= max_urls:
                # If we have more direct URLs than max_urls, just take the first max_urls
                selected_urls = direct_urls[:max_urls]
            else:
                # Take all direct URLs plus enough arXiv URLs to reach max_urls
                arxiv_to_include = max_urls - direct_url_count
                arxiv_selection = [url for url in all_candidate_urls if url not in direct_urls][:arxiv_to_include]
                selected_urls = direct_urls + arxiv_selection
            
            print(f"Limited URLs from {len(all_candidate_urls)} to {len(selected_urls)} based on maxSources setting")
        else:
            selected_urls = all_candidate_urls
            print(f"Using all {len(selected_urls)} candidate URLs")




        additional_search_terms = search_structure.get('title_terms', []) + search_structure.get('abstract_terms', [])
        # Pre-filter papers based on metadata before creating database objects
        try:
            from .services.paper_filter_service import filter_paper_urls
            
            # For URL-only mode, skip pre-filtering
            if is_url_only_search:
                print(f"URL-only mode with {len(all_candidate_urls)} URLs - skipping pre-filtering")
                relevant_urls = all_candidate_urls
            else:
                # Regular pre-filtering for topic searches or many URLs
                filter_result = filter_paper_urls(
                    all_candidate_urls, 
                    session.topics,
                    expanded_questions,
                    explanation,
                    additional_search_terms
                )
                
                print(f"Pre-filtering results: {filter_result}")
                
                # Update with filter results
                if filter_result.get('success'):
                    print(f"Pre-filtering completed: {filter_result.get('papers_relevant', 0)} relevant, "
                        f"{filter_result.get('papers_filtered', 0)} filtered out")
                    
                    # Send pre-filtering stats via WebSocket
                    send_status_update(
                        str(session.id),
                        'processing',
                        f"Pre-filtered papers: {filter_result.get('papers_relevant', 0)} relevant, "
                        f"{filter_result.get('papers_filtered', 0)} filtered out"
                    )
                    
                    # Get the list of relevant URLs only
                    relevant_urls = filter_result.get('relevant_urls', all_candidate_urls)
                else:
                    logger.warning(f"Pre-filtering failed: {filter_result.get('message', 'Unknown error')}")
                    print(f"Pre-filtering failed: {filter_result.get('message', 'Unknown error')}")
                    # Use all selected URLs if filtering failed
                    relevant_urls = all_candidate_urls
        except Exception as e:
            logger.error(f"Error during pre-filtering: {e}")
            print(f"Error during pre-filtering: {e}")
            # Continue with all selected URLs if pre-filtering fails
            relevant_urls = all_candidate_urls
        
        # Create Paper objects only for relevant URLs
        papers = []
        with transaction.atomic():
            for url in relevant_urls:
                paper = Paper.objects.create(
                    session=session,
                    url=url,
                    status="pending"
                )
                papers.append(paper)
        
        # Update session status
        session.status = 'processing'
        session.save()
        print(f"Created {len(papers)} paper objects from relevant URLs, proceeding to processing")
        
        # Get maximum number of workers from settings
        # Reduced to 1 to prevent arXiv rate limiting
        max_workers = 1  # Changed from getattr(settings, 'MAX_WORKERS', 6)
        print(f"Using {max_workers} workers for parallel paper processing")
        
        # Process papers with the thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Get all pending papers (already pre-filtered)
            pending_papers = Paper.objects.filter(
                session_id=session.id,
                status='pending'
            )
            
            print(f"Processing {pending_papers.count()} papers")
            search_terms = session.topics + additional_search_terms
            # Submit all pending papers to the thread pool
            future_to_paper = {
                executor.submit(
                    _process_paper_thread_safe,
                    str(paper.id),
                    search_terms,
                    query_embedding,
                    session.info_queries,
                    explanation
                ): paper for paper in pending_papers
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    result = future.result()
                    # Handle result, e.g., send update via WebSocket
                except Exception as e:
                    logger.error(f"Error processing paper: {e}")
        
        # After all papers have been processed, check the final status and update session
        # This is now done in the main thread, avoiding race conditions
        close_old_connections()  # Refresh connections before final DB operations
        session.refresh_from_db()  # Get latest session state
        
        # Double-check all papers are complete
        total_papers = Paper.objects.filter(session_id=session.id).count()
        completed_papers = Paper.objects.filter(
            session_id=session.id,
            status__in=['success', 'no_relevant_info', 'error']
        ).count()
        
        if completed_papers == total_papers:
            session.status = 'completed'
            session.save()
            
            # Send completion notification via WebSocket
            summary = {
                'total_papers': total_papers,
                'total_notes': sum(paper.notes.count() for paper in session.papers.all()),
                'papers_with_notes': sum(1 for paper in session.papers.all() if paper.notes.count() > 0)
            }
            send_status_update(
                str(session.id), 
                'completed', 
                f"Research completed. Found {summary['total_notes']} notes from {summary['papers_with_notes']} papers. "
            )
            
            print(f"All papers processed, session {session_id} marked as complete")
        else:
            logger.warning(f"Session {session_id} has incomplete papers: {completed_papers}/{total_papers} completed")
        
    except Exception as e:
        logger.error(f"Error in research session thread {session_id}: {e}", exc_info=True)
        try:
            session = ResearchSession.objects.get(id=session_id)
            session.status = 'error'
            session.save()
            print(f"Session {session_id} marked as error due to exception")
        except:
            logger.error(f"Failed to update session {session_id} status after error")
