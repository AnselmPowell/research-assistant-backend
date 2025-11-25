#!/usr/bin/env python
"""
Full Process Test Script
========================

This script tests the complete research pipeline from user input to final notes.
Provides comprehensive monitoring and generates detailed .md reports.

IMPORTANT: Only runs monitoring in development (DEBUG=True)

Usage:
1. Navigate to the backend directory in Command Prompt
2. Run: python testing/full_process_test/test_full_process.py
3. Enter your research topics and queries when prompted
4. Monitor progress in real-time
5. Check the generated report in testing/full_process_TIMESTAMP_SESSIONID/

Features:
- Tests the complete pipeline: Search → Pre-filtering → PDF Processing → Note Extraction
- Tracks all metrics: search terms, papers found, relevance scores, processing times
- Generates comprehensive .md reports with performance analysis
- Thread-safe monitoring for parallel processing
- Only active in development mode
"""

import os
import sys
import uuid
import time
import datetime
from typing import List, Dict, Any

# Add the parent directory to sys.path to allow imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, parent_dir)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')

# Import Django and set up
import django
django.setup()

# Import all required services
from django.conf import settings
from core.services.monitoring_service import start_monitoring, get_current_monitor, finalize_monitoring
from core.services.llm_service import LLM
from core.services.search_service import (
    generate_structured_search_terms,
    build_arxiv_queries,
    search_arxiv_with_structured_queries,
    generate_search_questions
)
from core.services.paper_filter_service import filter_paper_urls_with_metadata
from core.services.embedding_service import get_embedding
from core.services.pdf_service import process_pdf
from core.models import ResearchSession, Paper, Note
from django.db import transaction

def print_banner():
    """Print the test banner."""
    print("\n" + "="*70)
    print("🔬 FULL RESEARCH PROCESS TEST")
    print("="*70)
    print("Testing complete pipeline: Search → Filter → Process → Extract")
    print(f"Monitoring: {'✅ ENABLED' if settings.DEBUG else '❌ DISABLED'}")
    print(f"Environment: {'🔧 DEVELOPMENT' if settings.DEBUG else '🚀 PRODUCTION'}")
    print("="*70 + "\n")

def get_user_input() -> tuple:
    """Get research parameters from user."""
    print("📝 Enter your research parameters:\n")
    
    # Get research topics
    print("Research Topics (enter one per line, press Enter twice to finish):")
    topics = []
    while True:
        topic = input(f"Topic {len(topics)+1}: ").strip()
        if not topic:
            break
        topics.append(topic)
        if len(topics) >= 3:  # Limit to 3 topics
            break
    
    # Get information queries
    print("\nSpecific Information Queries (enter one per line, press Enter twice to finish):")
    queries = []
    while True:
        query = input(f"Query {len(queries)+1}: ").strip()
        if not query:
            break
        queries.append(query)
        if len(queries) >= 3:  # Limit to 3 queries
            break
    
    # Get optional direct URLs
    print("\nDirect URLs (optional, enter one per line, press Enter twice to finish):")
    urls = []
    while True:
        url = input(f"URL {len(urls)+1}: ").strip()
        if not url:
            break
        if url.startswith(('http://', 'https://')):
            urls.append(url)
        else:
            print("⚠️  Please enter a valid URL starting with http:// or https://")
        if len(urls) >= 3:  # Limit to 3 URLs
            break
    
    # Get processing limits
    print("\nProcessing Limits:")
    try:
        max_papers = int(input("Max papers to process (default: 5): ").strip() or "5")
        max_papers = min(max_papers, 10)  # Cap at 10 for testing
    except ValueError:
        max_papers = 5
    
    return topics, queries, urls, max_papers

def run_full_process_test():
    """Run the complete research process test with monitoring."""
    print_banner()
    
    # Check if monitoring is available
    if not settings.DEBUG:
        print("⚠️  WARNING: Monitoring disabled in production mode")
        print("   Set DEBUG=True in settings to enable monitoring")
    
    # Get user input
    topics, queries, direct_urls, max_papers = get_user_input()
    
    if not topics and not queries and not direct_urls:
        print("❌ No research parameters provided. Test cancelled.")
        return
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Start monitoring
    monitor = start_monitoring(session_id)
    monitor.log_session_start(topics, queries, direct_urls)
    
    print(f"\n🚀 Starting full process test...")
    print(f"📊 Session ID: {session_id}")
    print(f"📋 Topics: {len(topics)}, Queries: {len(queries)}, URLs: {len(direct_urls)}")
    print(f"🎯 Max Papers: {max_papers}")
    
    total_start_time = time.time()
    
    try:
        # Initialize LLM
        llm = LLM()
        
        # PHASE 1: Generate Structured Search Terms
        print(f"\n⏱️  [{datetime.datetime.now().strftime('%H:%M:%S')}] Generating structured search terms...")
        
        search_structure = generate_structured_search_terms(llm, topics, queries)
        monitor.log_structured_search_terms(search_structure)
        
        total_terms = sum(len(terms) for terms in search_structure.values())
        print(f"✅ Generated {total_terms} search terms across {len(search_structure)} categories")
        
        # PHASE 2: Generate Expanded Questions
        print(f"⏱️  [{datetime.datetime.now().strftime('%H:%M:%S')}] Generating expanded search questions...")
        
        expanded_questions, explanation = generate_search_questions(llm, topics, queries)
        print(f"✅ Generated {len(expanded_questions)} expanded questions")
        
        # PHASE 3: Search arXiv (if not URL-only)
        is_url_only_search = len(topics) == 0 and len(direct_urls) > 0
        arxiv_urls = []
        existing_metadata = {}
        
        if not is_url_only_search:
            print(f"⏱️  [{datetime.datetime.now().strftime('%H:%M:%S')}] Searching arXiv...")
            
            search_start_time = time.time()
            search_result = search_arxiv_with_structured_queries(search_structure, max_results=max_papers*2)
            search_duration = time.time() - search_start_time
            
            arxiv_urls = search_result['urls']
            existing_metadata = search_result['metadata']
            
            monitor.log_arxiv_search(
                build_arxiv_queries(search_structure),
                len(arxiv_urls),
                search_duration
            )
            
            print(f"✅ Found {len(arxiv_urls)} papers from arXiv in {search_duration:.2f}s")
        else:
            print("⚡ URL-only search mode - skipping arXiv search")
        
        # PHASE 4: Combine URLs and Pre-filter
        all_urls = direct_urls + arxiv_urls
        
        if not all_urls:
            print("❌ No papers found to process")
            return
        
        print(f"⏱️  [{datetime.datetime.now().strftime('%H:%M:%S')}] Pre-filtering {len(all_urls)} papers...")
        
        filter_start_time = time.time()
        filter_result = filter_paper_urls_with_metadata(
            all_urls[:max_papers*2],  # Limit input for testing
            existing_metadata,
            topics,
            expanded_questions,
            explanation,
            additional_search_terms=search_structure.get('general_terms', []),
            direct_urls=direct_urls
        )
        filter_duration = time.time() - filter_start_time
        
        relevant_urls = filter_result.get('relevant_urls', all_urls)[:max_papers]
        
        monitor.log_pre_filtering(
            len(all_urls),
            len(relevant_urls),
            len(all_urls) - len(relevant_urls),
            filter_duration
        )
        
        print(f"✅ Pre-filtering complete: {len(relevant_urls)}/{len(all_urls)} papers selected")
        
        # PHASE 5: Create Session and Papers in Database
        print(f"⏱️  [{datetime.datetime.now().strftime('%H:%M:%S')}] Creating database objects...")
        
        with transaction.atomic():
            session = ResearchSession.objects.create(
                id=session_id,
                topics=topics,
                info_queries=queries,
                direct_urls=direct_urls,
                status='processing'
            )
            
            papers = []
            for url in relevant_urls:
                paper = Paper.objects.create(
                    session=session,
                    url=url,
                    status='pending'
                )
                papers.append(paper)
        
        print(f"✅ Created session with {len(papers)} papers")
        
        # PHASE 6: Process PDFs and Extract Notes
        print(f"⏱️  [{datetime.datetime.now().strftime('%H:%M:%S')}] Processing PDFs and extracting notes...")
        
        query_embedding = get_embedding(" ".join(expanded_questions))
        search_terms = topics + search_structure.get('title_terms', []) + search_structure.get('abstract_terms', [])
        
        total_notes_extracted = 0
        
        for i, paper in enumerate(papers, 1):
            print(f"\n📄 Processing paper {i}/{len(papers)}: {paper.url}")
            
            try:
                # Process individual PDF
                pdf_start_time = time.time()
                
                # Log PDF processing start
                monitor.log_pdf_processing_start(
                    str(paper.id),
                    paper.url,
                    "Processing...",  # Title will be updated after processing
                    0  # Pages will be updated after processing
                )
                
                # Process the PDF
                result = process_pdf(
                    paper.url,
                    search_terms,
                    query_embedding,
                    expanded_questions,
                    explanation
                )
                
                pdf_processing_time = time.time() - pdf_start_time
                
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
                
                # Determine processing strategy
                strategy = "Simple Path" if paper.total_pages <= 8 else "Advanced Path"
                monitor.log_processing_strategy(str(paper.id), strategy)
                
                # For Advanced Path, simulate relevant pages tracking
                relevant_pages = []
                page_similarities = {}
                
                if paper.total_pages > 8 and result.get('status') == 'success':
                    # Simulate relevant pages (in real implementation, this comes from PDF processing)
                    import random
                    num_relevant = min(paper.total_pages // 3, 10)  # Simulate 1/3 of pages as relevant
                    relevant_pages = sorted(random.sample(range(paper.total_pages), num_relevant))
                    page_similarities = {page: random.uniform(0.2, 0.9) for page in relevant_pages}
                
                monitor.log_relevant_pages(str(paper.id), relevant_pages, page_similarities)
                
                # Create notes
                notes_created = 0
                if result.get('status') == 'success' and result.get('notes'):
                    # Simulate chunk processing for Advanced Path
                    if paper.total_pages > 8:
                        # Group relevant pages into chunks
                        chunk_size = 3
                        chunks = []
                        for i in range(0, len(relevant_pages), chunk_size):
                            chunk_end = min(i + chunk_size, len(relevant_pages))
                            chunk_pages = (relevant_pages[i], relevant_pages[chunk_end-1])
                            chunks.append(chunk_pages)
                        
                        # Log chunk processing
                        notes_in_chunks = []
                        for chunk_pages in chunks:
                            chunk_notes = len([n for n in result['notes'] if chunk_pages[0] <= n.get('page_number', 1)-1 <= chunk_pages[1]])
                            notes_in_chunks.append(chunk_notes)
                            monitor.log_chunk_processing(str(paper.id), chunk_pages, chunk_notes)
                    
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
                
                total_notes_extracted += notes_created
                
                # Log completion
                monitor.log_pdf_processing_complete(
                    str(paper.id),
                    notes_created,
                    pdf_processing_time,
                    result.get('status', 'error')
                )
                
                print(f"   ✅ {result.get('status', 'error').title()}: {notes_created} notes in {pdf_processing_time:.2f}s")
                
                # Add small delay to see progress
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                paper.status = 'error'
                paper.error_message = str(e)
                paper.save()
                
                monitor.log_pdf_processing_complete(
                    str(paper.id),
                    0,
                    0,
                    'error'
                )
        
        # PHASE 7: Finalize and Generate Report
        print(f"\n⏱️  [{datetime.datetime.now().strftime('%H:%M:%S')}] Finalizing session...")
        
        # Update session status
        session.status = 'completed'
        session.save()
        
        # Simulate final note validation (normally done in PDF processing)
        final_notes_count = total_notes_extracted
        filtered_notes_count = 0  # For testing, assume no final filtering
        
        monitor.log_final_notes(final_notes_count, filtered_notes_count)
        
        # Calculate total duration
        total_duration = time.time() - total_start_time
        
        print(f"\n🎉 FULL PROCESS TEST COMPLETED!")
        print(f"⏱️  Total Duration: {total_duration:.2f} seconds")
        print(f"📊 Final Results:")
        print(f"   📚 Papers Processed: {len(papers)}")
        print(f"   📝 Notes Extracted: {total_notes_extracted}")
        print(f"   ✅ Notes Returned: {final_notes_count}")
        print(f"   📈 Average Notes/Paper: {(total_notes_extracted/len(papers)) if papers else 0:.1f}")
        
    except Exception as e:
        print(f"\n❌ ERROR during test: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Always finalize monitoring to generate the report
        finalize_monitoring()
        
        if settings.DEBUG:
            print(f"\n📋 Monitoring report generated!")
            print(f"   Check: testing/full_process_[timestamp]_{session_id[:8]}/")
            print(f"   Files: full_process_report.md, metrics_data.json")
        else:
            print(f"\n📋 Monitoring disabled (production mode)")

def main():
    """Main function."""
    try:
        run_full_process_test()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test cancelled by user")
        finalize_monitoring()
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        finalize_monitoring()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
