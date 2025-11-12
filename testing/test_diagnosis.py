#!/usr/bin/env python
"""
Complete end-to-end diagnostic test for Research Assistant backend.
Tests the ENTIRE pipeline from query submission to notes ready for frontend.
NOW WITH DETAILED SEARCH QUERY AND AI PROMPT LOGGING.
"""

import os
import sys
import django
import json
import uuid
import time
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')
django.setup()

# Import after Django setup
from django.db import close_old_connections
from core.models import ResearchSession, Paper, Note
from core.services.llm_service import LLM
from core.services.embedding_service import get_embedding, validate_note_relevance
from core.services.search_service import generate_search_terms, generate_search_questions, search_arxiv, generate_structured_search_terms, search_arxiv_with_structured_queries
from core.services.pdf_service import process_pdf
from django.conf import settings
import concurrent.futures

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}")
    print(f" {text}")
    print(f"{'='*80}{Colors.END}\n")

def print_section(text):
    """Print a section title."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}>>> {text}{Colors.END}")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}[OK] {text}{Colors.END}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARNING] {text}{Colors.END}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}[ERROR] {text}{Colors.END}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.END}")

def process_paper_sync(paper_id, search_terms, query_embedding, info_queries, explanation):
    """
    Synchronous wrapper for paper processing.
    This mimics what happens in the real backend thread pool.
    """
    close_old_connections()
    
    try:
        paper = Paper.objects.get(id=paper_id)
        
        print_info(f"Processing: {paper.url[-50:]}")
        
        # Update status
        paper.status = 'processing'
        paper.save()
        
        # Process the PDF - THIS IS THE CORE EXTRACTION
        result = process_pdf(
            paper.url,
            search_terms,
            query_embedding,
            info_queries,
            explanation
        )
        
        # Update paper with results
        paper.title = result.get('title', 'Unknown')
        paper.authors = result.get('authors', [])
        paper.year = result.get('year', '')
        paper.summary = result.get('summary', '')
        paper.harvard_reference = result.get('harvard_reference', '')
        paper.total_pages = result.get('total_pages', 0)
        paper.status = result.get('status', 'error')
        paper.error_message = result.get('error_message', '')
        paper.save()
        
        # Create Note objects - THIS IS WHAT GOES TO FRONTEND
        notes_created = 0
        if result.get('status') == 'success' and result.get('notes'):
            for note_data in result.get('notes', []):
                Note.objects.create(
                    paper=paper,
                    content=note_data.get('content', ''),
                    page_number=note_data.get('page_number', 1),
                    note_type=note_data.get('note_type', 'quote'),
                    search_criteria=note_data.get('search_criteria', ''),
                    matches_topic=note_data.get('matches_topic', ''),
                    justification=note_data.get('justification', ''),
                    inline_citations=note_data.get('inline_citations', []),
                    reference_list=note_data.get('reference_list', {})
                )
                notes_created += 1
        
        print_success(f"Done: {paper.title[:50]}... -> {notes_created} notes")
        
        return {
            'paper_id': str(paper.id),
            'status': result.get('status'),
            'notes_created': notes_created,
            'title': paper.title,
            'url': paper.url
        }
        
    except Exception as e:
        print_error(f"Error: {str(e)[:100]}")
        return {
            'paper_id': str(paper_id),
            'status': 'error',
            'notes_created': 0,
            'error': str(e)
        }

def run_full_backend_test():
    """
    Run complete end-to-end backend test.
    This simulates EXACTLY what happens when a user submits a research query.
    """
    
    print_header("COMPLETE END-TO-END BACKEND DIAGNOSTIC TEST")
    print_info("This test simulates the ENTIRE backend pipeline")
    print_info("From query submission -> notes ready for frontend\n")
    
    # Storage for diagnostic data
    diagnostic_log = {
        'search_details': {},
        'arxiv_queries': {},
        'pdf_details': [],
        'ai_prompts': {}
    }
    
    # =================================================================
    # STEP 1: USER INPUT (Simulating Frontend Request)
    # =================================================================
    print_section("STEP 1: Collect Research Parameters (Frontend Input)")
    
    print(f"{Colors.BOLD}Enter your test parameters:{Colors.END}")
    topic = input("Research Topic: ").strip()
    query = input("Specific Query (optional): ").strip()
    num_papers = input("Number of papers to test (default 3, max 5): ").strip()
    
    if not topic:
        print_error("Topic is required!")
        return
    
    try:
        num_papers = int(num_papers) if num_papers else 3
        num_papers = min(num_papers, 5)  # Cap at 5 for testing
    except:
        num_papers = 3
    
    topics_list = [topic]
    queries_list = [query] if query else []
    
    diagnostic_log['user_input'] = {
        'topic': topic,
        'query': query,
        'num_papers': num_papers
    }
    
    print_success(f"Parameters collected: Topic='{topic}', Papers={num_papers}")
    
    # =================================================================
    # STEP 2: CREATE DATABASE SESSION
    # =================================================================
    print_section("STEP 2: Create Research Session in Database")
    
    session_id = str(uuid.uuid4())
    
    try:
        session = ResearchSession.objects.create(
            id=session_id,
            topics=topics_list,
            info_queries=queries_list,
            direct_urls=[],
            status='initiated'
        )
        print_success(f"Session created: {session_id}")
    except Exception as e:
        print_error(f"Failed to create session: {e}")
        return
    
    # =================================================================
    # STEP 3: INITIALIZE AI SERVICES
    # =================================================================
    print_section("STEP 3: Initialize AI Services")
    
    try:
        llm = LLM()
        print_success("LLM initialized (Pydantic-AI with OpenAI)")
        
        session.status = 'searching'
        session.save()
        
    except Exception as e:
        print_error(f"Failed to initialize AI: {e}")
        session.status = 'error'
        session.save()
        return
    
    # =================================================================
    # STEP 4: GENERATE SEARCH TERMS (AI Enhancement)
    # =================================================================
    print_section("STEP 4: Generate AI-Enhanced Search Terms")
    
    try:
        gen_search_terms = generate_search_terms(llm, topics_list, queries_list)
        combined_terms = topics_list + gen_search_terms
        print_success(f"Generated {len(combined_terms)} total search terms")
        
        print(f"\n  {Colors.BOLD}Original Topics:{Colors.END}")
        for i, term in enumerate(topics_list, 1):
            print(f"    {i}. {term}")
        
        if gen_search_terms:
            print(f"\n  {Colors.BOLD}AI-Generated Terms:{Colors.END}")
            for i, term in enumerate(gen_search_terms, 1):
                print(f"    {i}. {term}")
        
        print(f"\n  {Colors.BOLD}Combined Terms (sent to arXiv):{Colors.END}")
        for i, term in enumerate(combined_terms, 1):
            print(f"    {i}. '{term}'")
        
        diagnostic_log['search_details'] = {
            'original_topics': topics_list,
            'ai_generated_terms': gen_search_terms,
            'combined_terms': combined_terms
        }
        
    except Exception as e:
        print_error(f"Failed to generate search terms: {e}")
        combined_terms = topics_list
        print_warning("Falling back to original topics only")
    
    # =================================================================
    # STEP 5: GENERATE EXPANDED QUESTIONS & EXPLANATION
    # =================================================================
    print_section("STEP 5: Generate Expanded Questions & Research Intent")
    
    try:
        expanded_questions, explanation = generate_search_questions(
            llm, topics_list, queries_list
        )
        print_success(f"Generated {len(expanded_questions)} expanded questions")
        
        print(f"\n  {Colors.BOLD}Expanded Questions (for AI extraction):{Colors.END}")
        for i, q in enumerate(expanded_questions, 1):
            print(f"    {i}. {q}")
        
        print(f"\n  {Colors.BOLD}Research Intent Explanation:{Colors.END}")
        print(f"    {explanation}")
        
        diagnostic_log['ai_prompts'] = {
            'expanded_questions': expanded_questions,
            'research_explanation': explanation,
            'query_text_for_embedding': " ".join(expanded_questions)
        }
        
    except Exception as e:
        print_error(f"Failed to generate questions: {e}")
        expanded_questions = queries_list or topics_list
        explanation = f"Research about {topic}"
        print_warning("Using fallback questions")
    
    # =================================================================
    # STEP 6: CREATE QUERY EMBEDDING
    # =================================================================
    print_section("STEP 6: Create Query Embedding for Semantic Search")
    
    try:
        query_text = " ".join(expanded_questions)
        query_embedding = get_embedding(query_text)
        print_success(f"Created embedding (dimension: {len(query_embedding)})")
        print_info("This embedding will be used to find relevant pages in PDFs")
        
    except Exception as e:
        print_error(f"Failed to create embedding: {e}")
        session.status = 'error'
        session.save()
        return
    
    # =================================================================
    # STEP 7: SEARCH ARXIV FOR PAPERS
    # =================================================================
    print_section("STEP 7: Search arXiv for Academic Papers")
    
    try:
        print_info(f"Generating structured search for better results...")
        search_structure = generate_structured_search_terms(llm, topics, info_queries)
        print_info(f"Created structure with {len(search_structure.get('exact_phrases', []))} exact phrases, "
                  f"{len(search_structure.get('title_terms', []))} title terms, "
                  f"{len(search_structure.get('abstract_terms', []))} abstract terms, and "
                  f"{len(search_structure.get('general_terms', []))} general terms")
        
        diagnostic_log['search_structure'] = search_structure
                  
        print_info(f"Searching arXiv with structured queries...")
        arxiv_urls = search_arxiv_with_structured_queries(search_structure, max_results=num_papers)
        print_success(f"Found {len(arxiv_urls)} papers total")
        
        if not arxiv_urls:
            print_error("No papers found!")
            session.status = 'completed'
            session.save()
            return
        
        print(f"\n  {Colors.BOLD}arXiv Search Structure:{Colors.END}")
        diagnostic_log['arxiv_queries'] = {}
        
        if search_structure.get("exact_phrases"):
            print(f"    Exact Phrases: {search_structure['exact_phrases']}")
            diagnostic_log['arxiv_queries']['exact_phrases'] = search_structure['exact_phrases']
            
        if search_structure.get("title_terms"):
            print(f"    Title Terms: {search_structure['title_terms']}")
            diagnostic_log['arxiv_queries']['title_terms'] = search_structure['title_terms']
            
        if search_structure.get("abstract_terms"):
            print(f"    Abstract Terms: {search_structure['abstract_terms']}")
            diagnostic_log['arxiv_queries']['abstract_terms'] = search_structure['abstract_terms']
            
        if search_structure.get("general_terms"):
            print(f"    General Terms: {search_structure['general_terms']}")
            diagnostic_log['arxiv_queries']['general_terms'] = search_structure['general_terms']
        
        print(f"\n  {Colors.BOLD}Papers Found (URLs):{Colors.END}")
        for i, url in enumerate(arxiv_urls, 1):
            print(f"    {i}. {url}")
            
    except Exception as e:
        print_error(f"Failed to search arXiv: {e}")
        session.status = 'error'
        session.save()
        return
    
    # =================================================================
    # STEP 8: CREATE PAPER OBJECTS IN DATABASE
    # =================================================================
    print_section("STEP 8: Create Paper Records in Database")
    
    papers = []
    try:
        for url in arxiv_urls:
            paper = Paper.objects.create(
                session=session,
                url=url,
                status='pending'
            )
            papers.append(paper)
        
        print_success(f"Created {len(papers)} Paper objects")
        
        session.status = 'processing'
        session.save()
        
    except Exception as e:
        print_error(f"Failed to create paper records: {e}")
        session.status = 'error'
        session.save()
        return
    
    # =================================================================
    # STEP 9: PARALLEL PDF PROCESSING
    # =================================================================
    print_section("STEP 9: Process PDFs in Parallel (Core Extraction)")
    print_info("Downloading PDFs, extracting metadata, finding relevant pages, extracting notes")
    print_info("Using ThreadPoolExecutor with 4 workers\n")
    
    max_workers = getattr(settings, 'MAX_WORKERS', 4)
    results = []
    
    start_time = time.time()
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_paper = {
                executor.submit(
                    process_paper_sync,
                    str(paper.id),
                    combined_terms,
                    query_embedding,
                    queries_list,
                    explanation
                ): paper for paper in papers
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_paper), 1):
                paper = future_to_paper[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    status_icon = "✓" if result['status'] == 'success' else "✗"
                    print(f"{status_icon} Paper {i}/{len(papers)}: {result['notes_created']} notes")
                    
                except Exception as e:
                    print_error(f"Paper {i} failed: {e}")
                    results.append({
                        'paper_id': str(paper.id),
                        'status': 'error',
                        'notes_created': 0
                    })
        
        processing_time = time.time() - start_time
        print_success(f"All papers processed in {processing_time:.1f} seconds")
        
    except Exception as e:
        print_error(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
    
    # =================================================================
    # STEP 10: UPDATE SESSION STATUS
    # =================================================================
    print_section("STEP 10: Finalize Session")
    
    try:
        session.status = 'completed'
        session.save()
        print_success("Session status -> 'completed'")
        
    except Exception as e:
        print_error(f"Failed to update session: {e}")
    
    # =================================================================
    # STEP 11: PREPARE FRONTEND RESPONSE
    # =================================================================
    print_section("STEP 11: Prepare Data for Frontend (API Response)")
    
    try:
        frontend_notes = []
        
        for paper in session.papers.all():
            for note in paper.notes.all():
                frontend_notes.append(note.to_frontend_format())
        
        print_success(f"Prepared {len(frontend_notes)} notes for frontend")
        
    except Exception as e:
        print_error(f"Failed to prepare frontend data: {e}")
        frontend_notes = []
    
    # =================================================================
    # Collect PDF details
    # =================================================================
    for result in results:
        try:
            paper = Paper.objects.get(id=result['paper_id'])
            diagnostic_log['pdf_details'].append({
                'url': paper.url,
                'title': paper.title,
                'authors': paper.authors,
                'year': paper.year,
                'total_pages': paper.total_pages,
                'status': result['status'],
                'notes_created': result['notes_created']
            })
        except:
            pass
    
    # =================================================================
    # FINAL RESULTS & ANALYSIS
    # =================================================================
    print_header("DIAGNOSTIC RESULTS")
    
    # Count statistics
    total_papers = len(papers)
    successful_papers = sum(1 for r in results if r['status'] == 'success')
    failed_papers = sum(1 for r in results if r['status'] == 'error')
    no_info_papers = sum(1 for r in results if r['status'] == 'no_relevant_info')
    total_notes = sum(r['notes_created'] for r in results)
    
    # Clear visual note count display
    print(f"\n{Colors.BOLD}{Colors.BLUE}╔═══════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}║   NOTES EXTRACTED: {Colors.END}{Colors.GREEN}{Colors.BOLD}{total_notes:2d}                             {Colors.BLUE}{Colors.BOLD}║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}║   NOTES FOR FRONTEND: {Colors.END}{Colors.GREEN}{Colors.BOLD}{len(frontend_notes):2d}                          {Colors.BLUE}{Colors.BOLD}║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}╚═══════════════════════════════════════════════════╝{Colors.END}\n")
    
    print(f"\n{Colors.BOLD}═══ SEARCH QUALITY ANALYSIS ═══{Colors.END}\n")
    
    print(f"{Colors.BOLD}1. Original User Input:{Colors.END}")
    print(f"   Topic: '{topic}'")
    print(f"   Query: '{query if query else 'None'}'")
    
    print(f"\n{Colors.BOLD}2. AI-Generated Search Terms:{Colors.END}")
    for i, term in enumerate(combined_terms, 1):
        print(f"   {i}. '{term}'")
    
    print(f"\n{Colors.BOLD}3. arXiv Query Details:{Colors.END}")
    print(f"   Search terms sent to arXiv: {len(combined_terms)}")
    print(f"   Expected results: ~{len(combined_terms) * 8} papers (8 per term)")
    print(f"   Actual results: {len(arxiv_urls)} papers")
    
    print(f"\n{Colors.BOLD}4. Papers Retrieved:{Colors.END}")
    for i, detail in enumerate(diagnostic_log['pdf_details'], 1):
        print(f"   {i}. {detail['title'][:400]}...")
        print(f"      Authors: {', '.join(detail['authors'][:2])}...")
        print(f"      Year: {detail['year']}")
        print(f"      Status: {detail['status']} | Notes: {detail['notes_created']}")
    
    print(f"\n{Colors.BOLD}5. AI Extraction Parameters:{Colors.END}")
    print(f"   Expanded Questions ({len(expanded_questions)}):")
    for i, q in enumerate(expanded_questions, 1):
        print(f"      {i}. {q}")
    print(f"   Research Intent: {explanation}")
    
    print(f"\n{Colors.BOLD}═══ PIPELINE STATISTICS ═══{Colors.END}\n")
    print(f"  Session ID: {session_id}")
    print(f"  Processing Time: {processing_time:.1f}s")
    print(f"  Search Terms Generated: {len(combined_terms)}")
    print(f"  Papers Found: {len(arxiv_urls)}")
    print(f"  Papers Processed: {total_papers}")
    print(f"  ✓ Successful: {successful_papers}")
    print(f"  ⚠ No Relevant Info: {no_info_papers}")
    print(f"  ✗ Failed/Error: {failed_papers}")
    print(f"  Total Notes Created: {total_notes}")
    print(f"  Notes Ready for Frontend: {len(frontend_notes)}")
    
    # Verdict
    if len(frontend_notes) > 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ FRONTEND WOULD RECEIVE NOTES: YES{Colors.END}")
        print_success(f"{len(frontend_notes)} notes would appear in Layer 2")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ FRONTEND WOULD RECEIVE NOTES: NO{Colors.END}")
        print_error("User would see 'No Items to Review'")
        
        print(f"\n{Colors.YELLOW}{Colors.BOLD}POSSIBLE CAUSES:{Colors.END}")
        print("  1. Papers don't contain relevant information")
        print("  2. Validation threshold too high (check backend logs)")
        print("  3. Search terms not matching paper content")
        print("  4. PDF extraction errors")
    
    # Save diagnostic report
    print_section("Saving Diagnostic Reports")
    
    try:
        # Create test directory if it doesn't exist
        test_dir = "test"
        os.makedirs(test_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        diagnostic_filename = os.path.join(test_dir, f"diagnostic_full_{timestamp}.json")
        notes_filename = os.path.join(test_dir, f"notes_summary_{timestamp}.json")
        
        # Prepare diagnostic data
        diagnostic_data = {
            'test_metadata': {
                'timestamp': timestamp,
                'session_id': session_id,
                'processing_time_seconds': processing_time
            },
            'user_input': diagnostic_log['user_input'],
            'search_details': diagnostic_log['search_details'],
            'ai_prompts': diagnostic_log['ai_prompts'],
            'arxiv_queries': diagnostic_log['arxiv_queries'],
            'pdf_details': diagnostic_log['pdf_details'],
            'results': {
                'successful_papers': successful_papers,
                'failed_papers': failed_papers,
                'no_info_papers': no_info_papers,
                'total_notes_created': total_notes,
                'notes_ready_for_frontend': len(frontend_notes)
            },
            'verdict': {
                'would_reach_frontend': len(frontend_notes) > 0,
                'user_would_see_notes': len(frontend_notes) > 0
            }
        }
        
        # Save full diagnostic report
        with open(diagnostic_filename, 'w', encoding='utf-8') as f:
            json.dump(diagnostic_data, f, indent=2)
        
        print_success(f"Full diagnostic report saved: {diagnostic_filename}")
        
        # Prepare simplified notes summary
        notes_data = {
            'search_info': {
                'topic': topic,
                'query': query if query else 'None',
                'timestamp': timestamp
            },
            'notes': []
        }
        
        # Extract simplified note information for each note
        for note_index, note in enumerate(frontend_notes, 1):
            # Find the paper this note belongs to
            paper_info = None
            for pdf_detail in diagnostic_log['pdf_details']:
                if note.get('source') == pdf_detail.get('title'):
                    paper_info = pdf_detail
                    break
                    
            # Create simplified note entry
            simplified_note = {
                'id': note_index,
                'title': note.get('source', 'Unknown Paper'),
                'search_term': note.get('searchCriteria', 'Unknown Search Term'),
                'page': note.get('pageNumber', 'Unknown'),
                'note_type': note.get('type', 'Unknown Type'),
                'content_preview': note.get('content', '')[:200] + '...' if len(note.get('content', '')) > 200 else note.get('content', ''),
                'paper_url': paper_info.get('url') if paper_info else 'Unknown URL'
            }
            notes_data['notes'].append(simplified_note)
        
        # Save notes summary
        with open(notes_filename, 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, indent=2)
            
        print_success(f"Notes summary saved: {notes_filename}")
        print_info("Review these files for complete search quality analysis")
        
    except Exception as e:
        print_warning(f"Could not save reports: {e}")
        import traceback
        traceback.print_exc()
    
    print_header("TEST COMPLETE")

if __name__ == "__main__":
    try:
        run_full_backend_test()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
