#!/usr/bin/env python
"""
Test script for the Research Assistant system.
Allows running a search from the command line and displays results.
"""

import os
import sys
import django
import time
import json
import uuid
import concurrent.futures
from pprint import pprint
import inspect
import types

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')
django.setup()

# Import models and services after Django setup
from core.models import ResearchSession, Note, Paper
from core.tasks import process_research_session, _process_paper_thread_safe
from core.services.embedding_service import get_embedding
from core.services.search_service import generate_search_terms, generate_search_questions, search_arxiv, generate_structured_search_terms, search_arxiv_with_structured_queries
from core.services.llm_service import LLM
from core.services.pdf_service import process_pdf
from django.conf import settings

# Setup mock for channel layer to prevent WebSocket errors during testing
try:
    from channels.layers import get_channel_layer, BaseChannelLayer
    from django.test.utils import override_settings
    
    # Check if a channel layer is configured
    channel_layer = get_channel_layer()
    if channel_layer is None:
        print("[INFO] No channel layer configured for WebSockets - messages will be logged but not sent")
except Exception as e:
    print(f"[INFO] WebSocket functionality will be disabled for testing: {str(e)}")

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_user_input():
    """Get user input for research topic and queries."""
    print("\n" + "="*80)
    print(" "*30 + "RESEARCH ASSISTANT TEST")
    print("="*80 + "\n")
    
    # Get research topic
    topic = input("Enter your research topic/subject: ").strip()
    
    # Get search queries
    print("\nEnter up to 3 specific information queries (one per line, press Enter twice to finish):")
    queries = []
    for i in range(3):
        query = input(f"Query {i+1}: ").strip()
        if not query:
            break
        queries.append(query)
    
    # Get direct URLs (optional)
    print("\nOptional: Enter any direct PDF URLs (one per line, press Enter twice to finish):")
    urls = []
    while True:
        url = input("URL: ").strip()
        if not url:
            break
        urls.append(url)
    
    return topic, queries, urls

def monkey_patch_process_research_session():
    """Create a synchronous version of the process_research_session function with parallel processing."""
    
    def sync_process_research_session(session_id):
        """Synchronous version of process_research_session with parallel papers processing."""
        print(f"[DEBUG] Starting synchronous research session: {session_id}")
        
        try:
            # Get session
            session = ResearchSession.objects.get(id=session_id)
            
            # Extract data
            topics = session.topics
            info_queries = session.info_queries
            direct_urls = session.direct_urls
            
            print(f"[DEBUG] Session data: topics={topics}, queries={info_queries}, urls={direct_urls}")
            
            # Update session status
            session.status = 'searching'
            session.save()
            print(f"[DEBUG] Updated session status to: searching")
            
            # Create LLM instance
            llm = LLM()
            print("[DEBUG] Created LLM instance")
            
            # Generate structured search terms for better arXiv results
            search_structure = generate_structured_search_terms(llm, session.topics, session.info_queries)
            print(f"[DEBUG] Generated structured search terms with {len(search_structure.get('exact_phrases', []))} exact phrases, "
                  f"{len(search_structure.get('title_terms', []))} title terms, "
                  f"{len(search_structure.get('abstract_terms', []))} abstract terms, and "
                  f"{len(search_structure.get('general_terms', []))} general terms")
            
            # Also generate regular search terms for compatibility with other functions
            gen_search_terms = generate_search_terms(llm, session.topics, session.info_queries)
            search_terms = gen_search_terms + session.topics
            print(f"[DEBUG] Generated search terms: {search_terms}")
            
            # Generate expanded questions for embedding creation
            expanded_questions, explanation = generate_search_questions(llm, session.topics, session.info_queries)
            print(f"[DEBUG] Generated expanded questions: {expanded_questions}")
            
            # Get embedding for the query
            query_embedding = get_embedding(" ".join(expanded_questions))
            print("[DEBUG] Generated query embedding")
            
            # If direct URLs are provided, use them
            if direct_urls:
                print(f"[DEBUG] Using {len(direct_urls)} direct URLs provided")
                arxiv_urls = []
            else:
                # Use the structured approach for better results
                print("[DEBUG] Searching arXiv with structured queries")
                arxiv_urls = search_arxiv_with_structured_queries(search_structure)
                print(f"[DEBUG] Found {len(arxiv_urls)} papers from arXiv")
            
            # Combine URLs, prioritizing direct URLs
            all_urls = direct_urls + [url for url in arxiv_urls if url not in direct_urls]
            print(f"[DEBUG] Combined URLs, total: {len(all_urls)}")
            
            if not all_urls:
                print("[DEBUG] No URLs found, ending session")
                session.status = 'completed'
                session.save()
                return
            
            # Create Paper objects for all URLs
            papers = []
            for url in all_urls:
                print(f"[DEBUG] Creating paper object for URL: {url}")
                paper = Paper.objects.create(
                    session=session,
                    url=url,
                    status="pending",
                    year="",
                    summary="",
                    total_pages=0
                )
                papers.append(paper)
            
            # Update session status
            session.status = 'processing'
            session.save()
            print("[DEBUG] Updated session status to: processing")
            
            # Process papers in parallel
            max_workers = getattr(settings, 'MAX_WORKERS', 4)
            print(f"[DEBUG] Using {max_workers} workers for parallel processing")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all papers to the thread pool
                future_to_paper = {
                    executor.submit(
                        _process_paper_thread_safe, 
                        str(paper.id), 
                        search_terms,
                        query_embedding, 
                        session.info_queries,
                        explanation  # Pass the explanation to each worker
                    ): paper for paper in papers
                }
                
                # Process results as they complete
                for i, future in enumerate(concurrent.futures.as_completed(future_to_paper)):
                    paper = future_to_paper[future]
                    try:
                        result = future.result()
                        print(f"[DEBUG] Paper {i+1}/{len(papers)} ({paper.id}) completed with status: {result.get('status')}")
                    except Exception as e:
                        print(f"[DEBUG] Error processing paper {paper.id}: {str(e)}")
            
            # Final update to session status
            session.status = 'completed'
            session.save()
            print("[DEBUG] Updated session status to: completed")
            
            return "Research completed successfully"
        
        except Exception as e:
            print(f"[DEBUG] ERROR in process_research_session: {str(e)}")
            try:
                session = ResearchSession.objects.get(id=session_id)
                session.status = 'error'
                session.save()
                print("[DEBUG] Updated session status to: error")
            except Exception as inner_e:
                print(f"[DEBUG] ERROR updating session status: {str(inner_e)}")
            
            raise
    
    return sync_process_research_session

def save_notes_to_markdown(session_id: str, filepath: str):
    """Save all notes from a session to a markdown file with improved formatting."""
    try:
        session = ResearchSession.objects.get(id=session_id)
        
        # Get absolute path for the file
        import os
        from datetime import datetime
        
        # Create a dedicated folder for research results
        results_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), "research_results")
        os.makedirs(results_dir, exist_ok=True)
        
        # Update filepath to be in the new directory
        filename = os.path.basename(filepath)
        filepath = os.path.join(results_dir, filename)
        
        # Get expanded questions and explanation if available
        # These would be generated during the research process but we're accessing them retrospectively
        try:
            llm = LLM()
            _, explanation = generate_search_questions(llm, session.topics, session.info_queries)
        except Exception as e:
            explanation = "Not available"
            print(f"Could not retrieve explanation: {e}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write enhanced header with better formatting
            f.write(f"# Research Results: {', '.join(session.topics)}\n\n")
            
            # Add table of contents
            f.write("## Table of Contents\n\n")
            f.write("1. [Research Overview](#research-overview)\n")
            f.write("2. [Papers Analyzed](#papers-analyzed)\n")
            
            paper_count = 1
            for paper in session.papers.all():
                if paper.notes.count() > 0:
                    paper_title = paper.title if paper.title else f"Paper {paper_count}"
                    paper_anchor = paper_title.lower().replace(' ', '-').replace(':', '').replace(',', '')[:50]
                    f.write(f"   {paper_count}. [{paper_title}](#{paper_anchor})\n")
                    paper_count += 1
            
            f.write("3. [Summary and Statistics](#summary-and-statistics)\n\n")
            
            # Write research overview section
            f.write("## Research Overview\n\n")
            f.write("<div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 5px solid #007bff;'>\n\n")
            f.write("### Search Topics\n\n")
            for topic in session.topics:
                f.write(f"- {topic}\n")
            f.write("\n")
            
            f.write("### Research Questions\n\n")
            for query in session.info_queries:
                f.write(f"- {query}\n")
            f.write("\n")
            
            # Add explanation of what the user is looking for
            f.write("### Research Intent\n\n")
            f.write(f"_{explanation}_\n\n")
            
            # Add session metadata
            f.write("### Session Details\n\n")
            f.write(f"- **Session ID**: `{session_id}`\n")
            f.write(f"- **Created**: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Status**: {session.status}\n")
            
            total_papers = session.papers.count()
            papers_with_notes = sum(1 for paper in session.papers.all() if paper.notes.count() > 0)
            total_notes = sum(paper.notes.count() for paper in session.papers.all())
            
            f.write(f"- **Papers Analyzed**: {total_papers}\n")
            f.write(f"- **Papers with Relevant Information**: {papers_with_notes}\n")
            f.write(f"- **Total Notes Extracted**: {total_notes}\n")
            f.write("</div>\n\n")
            
            f.write("---\n\n")
            
            # Papers section
            f.write("## Papers Analyzed\n\n")
            
            # Process each paper
            paper_count = 1
            for paper in session.papers.all():
                # Skip papers with no notes to focus on relevant results
                if paper.notes.count() == 0:
                    continue
                    
                paper_title = paper.title if paper.title else f"Paper {paper_count}"
                paper_anchor = paper_title.lower().replace(' ', '-').replace(':', '').replace(',', '')[:50]
                
                f.write(f"### {paper_title}\n\n")
                
                # Paper metadata in a highlighted box
                f.write("<div style='background-color: #f0f7ff; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>\n\n")
                f.write(f"**Harvard Reference**: {paper.harvard_reference}\n\n")
                if paper.authors:
                    f.write(f"**Authors**: {', '.join(paper.authors)}\n\n")
                if paper.year:
                    f.write(f"**Year**: {paper.year}\n\n")
                if paper.summary:
                    f.write(f"**Summary**: {paper.summary}\n\n")
                f.write(f"**PDF URL**: [{paper.url}]({paper.url})\n\n")
                f.write(f"**Pages**: {paper.total_pages}\n\n")
                f.write("</div>\n\n")
                
                # Process notes for this paper
                notes = paper.notes.all()
                if notes:
                    f.write(f"#### Extracted Notes ({len(notes)})\n\n")
                    
                    for i, note in enumerate(notes, 1):
                        note_data = note.to_frontend_format()
                        
                        # Note card with color based on type
                        note_color = "#e8f5e9" if note_data['type'] == 'quote' else "#fff8e1" if note_data['type'] == 'statistic' else "#e3f2fd"
                        border_color = "#43a047" if note_data['type'] == 'quote' else "#ff8f00" if note_data['type'] == 'statistic' else "#1e88e5"
                        
                        f.write(f"<div style='background-color: {note_color}; padding: 15px; border-radius: 5px; border-left: 5px solid {border_color}; margin-bottom: 20px;'>\n\n")
                        
                        # Note header with badges
                        f.write(f"##### Note {i} | <span style='background-color: {border_color}; color: white; padding: 3px 7px; border-radius: 10px; font-size: 0.8em;'>{note_data['type'].upper()}</span> | Page {note_data['pageNumber']}\n\n")
                        
                        # Add relevance score if available
                        if 'relevance_score' in note_data:
                            score = float(note_data['relevance_score']) * 100
                            f.write(f"**Relevance Score**: {score:.1f}%\n\n")
                        
                        # Show which query/topic this note matches
                        f.write(f"**Addresses Research Question**: \"{note_data['matchesTopic']}\"\n\n")
                        
                        # Main content with blockquote styling
                        f.write("**Content**:\n\n")
                        f.write(f"> {note_data['content'].replace(chr(10), chr(10) + '> ')}\n\n")
                        
                        # Citations section if available
                        if note_data.get('inlineCitations'):
                            f.write("**Citations**:\n\n")
                            for citation in note_data['inlineCitations']:
                                f.write(f"- {citation}\n")
                            f.write("\n")
                            
                        # Reference list if available
                        if note_data.get('referenceList') and len(note_data['referenceList']) > 0:
                            f.write("**References**:\n\n")
                            for ref_key, ref_text in note_data['referenceList'].items():
                                f.write(f"- {ref_key}: {ref_text}\n")
                            f.write("\n")
                            
                        f.write("</div>\n\n")
                
                paper_count += 1
                f.write("---\n\n")
            
            # Write summary section
            f.write("## Summary and Statistics\n\n")
            f.write("<div style='background-color: #f5f5f5; padding: 15px; border-radius: 5px;'>\n\n")
            
            # Papers statistics
            f.write("### Papers Statistics\n\n")
            f.write(f"- **Total Papers Analyzed**: {total_papers}\n")
            f.write(f"- **Papers with Relevant Information**: {papers_with_notes}\n")
            f.write(f"- **Papers with No Relevant Information**: {total_papers - papers_with_notes}\n\n")
            
            # Notes statistics
            f.write("### Notes Statistics\n\n")
            f.write(f"- **Total Notes Extracted**: {total_notes}\n")
            
            # Count by type
            quote_count = 0
            statistic_count = 0
            methodology_count = 0
            
            for paper in session.papers.all():
                for note in paper.notes.all():
                    note_data = note.to_frontend_format()
                    note_type = note_data.get('type', '').lower()
                    if note_type == 'quote':
                        quote_count += 1
                    elif note_type == 'statistic':
                        statistic_count += 1
                    elif note_type == 'methodology':
                        methodology_count += 1
            
            f.write(f"- **Quotes**: {quote_count}\n")
            f.write(f"- **Statistics**: {statistic_count}\n")
            f.write(f"- **Methodologies**: {methodology_count}\n\n")
            
            # Final notes
            f.write("### Research Complete\n\n")
            f.write(f"_This research was generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} using the AI Academic Research Assistant._\n\n")
            f.write("</div>\n\n")
        
        print(f"\n✅ Notes saved to: {filepath}")
        print(f"   Full path: {os.path.abspath(filepath)}")
        
        # Try to open the file for the user if on a GUI system
        try:
            import platform
            system = platform.system()
            if system == 'Windows':
                os.startfile(filepath)
                print("   Opening file automatically...")
            elif system == 'Darwin':  # macOS
                import subprocess
                subprocess.call(['open', filepath])
                print("   Opening file automatically...")
            elif system == 'Linux':
                import subprocess
                subprocess.call(['xdg-open', filepath])
                print("   Opening file automatically...")
        except Exception as e:
            print(f"   Note: Could not automatically open the file: {e}")
            print("   Please open it manually using your preferred text editor or Markdown viewer.")
        
        return True
    except Exception as e:
        print(f"\nError saving notes to markdown: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_test():
    """Run the research test and display results."""
    # Get user input
    topic, queries, urls = get_user_input()
    
    if not topic and not queries:
        print("\nError: You must provide at least a topic or a query.")
        return
    
    # Create session
    session_id = str(uuid.uuid4())
    print(f"\nCreating research session with ID: {session_id}")
    
    session = ResearchSession.objects.create(
        id=session_id,
        topics=[topic] if topic else [],
        info_queries=queries,
        direct_urls=urls,
        status='initiated'
    )
    
    # Start the research process
    print("\nStarting research process...")
    
    try:
        # Get synchronous version of process_research_session
        sync_process_research_session = monkey_patch_process_research_session()
        
        # Run the synchronous process
        sync_process_research_session(session_id)
        
        # Refresh the session to get latest status
        session.refresh_from_db()
        print(f"\nFinal status: {session.status}")
        
        if session.status == 'error':
            print("Error occurred during processing.")
            return
        
        # Get all notes
        all_notes = []
        paper_count = 0
        
        for paper in session.papers.all():
            paper_count += 1
            paper_notes = paper.notes.all()
            for note in paper_notes:
                all_notes.append(note.to_frontend_format())
        
        # Display results
        print("\n" + "="*80)
        print(f" Results: {len(all_notes)} notes found from {paper_count} papers")
        print("="*80 + "\n")
        
        if not all_notes:
            print("No notes were found for your query.")
            return
        
        # Display each note
        for i, note in enumerate(all_notes, 1):
            print(f"\nNote {i}/{len(all_notes)}:")
            print(f"Type: {note['type']}")
            print(f"Content: {note['content'][:200]}..." if len(note['content']) > 200 else f"Content: {note['content']}")
            print(f"Page: {note['pageNumber']}")
            print(f"Source: {note['source']}")
            print(f"Matches Topic: {note['matchesTopic']}")
            
            # Ask if user wants to see full details
            if i < len(all_notes):
                choice = input("\nPress Enter for next note, 'd' for details, 'q' to quit, or 's' to skip to markdown export: ").lower()
                
                if choice == 'd':
                    pprint(note)
                    input("Press Enter to continue...")
                elif choice == 'q':
                    break
                elif choice == 's':
                    break
                
                clear_screen()
        
        print("\nTest completed.")
        
        # Save all notes to markdown file
        print("\nSaving notes to markdown file...")
        # Use a more descriptive filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_slug = topic.lower().replace(' ', '_')[:20] if topic else "research"
        filename = f"{topic_slug}_notes_{timestamp}.md"
        save_notes_to_markdown(session_id, filename)
    
    except Exception as e:
        print(f"\nError during research process: {str(e)}")
        print("\nStack trace:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
