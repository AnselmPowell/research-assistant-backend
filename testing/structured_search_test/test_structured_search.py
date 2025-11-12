#!/usr/bin/env python
"""
Isolated test script for the structured search functionality.
Tests the enhanced arXiv search with structured queries.
To Test this file use a Windows CMD
Use window command shell if needed best to use  cmd shell  
"""

import os
import sys
import json
import datetime

# Add the parent directory to sys.path to allow imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, parent_dir)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')

# Import Django and set up
import django
django.setup()

# Now import the specific modules we need
from core.services.llm_service import LLM
from core.services.search_service import (
    generate_structured_search_terms,
    build_arxiv_queries,
    search_arxiv_with_structured_queries
)

def timestamp():
    """Get a formatted timestamp."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_to_file(filename, content, mode='a'):
    """Append content to a file."""
    with open(filename, mode, encoding='utf-8') as f:
        f.write(content)

def create_markdown_header(title):
    """Create a markdown header with timestamp."""
    return f"# {title}\n\nTest run at: {timestamp()}\n\n"

def get_user_input():
    """Get the research topic and queries from user input."""
    print("\n===== Structured Search Test =====\n")
    
    # Get research topic
    topic = input("Enter a research topic: ").strip()
    
    # Get search queries
    print("\nEnter up to 3 specific information queries (one per line, press Enter twice to finish):")
    queries = []
    for i in range(3):
        query = input(f"Query {i+1}: ").strip()
        if not query:
            break
        queries.append(query)
    
    return topic, queries

def test_structured_search():
    """Test the structured search functionality."""
    # File paths for output
    current_dir = os.path.dirname(os.path.abspath(__file__))
    diagnostic_file = os.path.join(current_dir, "diagnostics.md")
    results_file = os.path.join(current_dir, "search_results.md")
    
    # Initialize output files with headers
    log_to_file(diagnostic_file, create_markdown_header("Search Diagnostics"), 'w')
    log_to_file(results_file, create_markdown_header("Search Results"), 'w')
    
    # Get user input
    topic, queries = get_user_input()
    
    # Log input to diagnostic file
    log_to_file(diagnostic_file, f"## Input Parameters\n\n")
    log_to_file(diagnostic_file, f"- **Topic:** {topic}\n")
    log_to_file(diagnostic_file, f"- **Queries:**\n")
    for query in queries:
        log_to_file(diagnostic_file, f"  - {query}\n")
    log_to_file(diagnostic_file, f"\n")
    
    print(f"\n[{timestamp()}] Initializing LLM...")
    llm = LLM()
    
    try:
        # Step 1: Generate structured search terms
        print(f"[{timestamp()}] Generating structured search terms...")
        log_to_file(diagnostic_file, f"## Structured Search Term Generation\n\n")
        
        search_structure = generate_structured_search_terms(llm, [topic], queries)
        
        # Log the structured search terms
        log_to_file(diagnostic_file, f"### Generated Search Structure\n\n```json\n{json.dumps(search_structure, indent=2)}\n```\n\n")
        
        print(f"[{timestamp()}] Generated structured search terms:")
        print(f"- Exact Phrases: {len(search_structure.get('exact_phrases', []))}")
        print(f"- Title Terms: {len(search_structure.get('title_terms', []))}")
        print(f"- Abstract Terms: {len(search_structure.get('abstract_terms', []))}")
        print(f"- General Terms: {len(search_structure.get('general_terms', []))}")
        
        # Step 2: Build arXiv queries from the structure
        print(f"[{timestamp()}] Building arXiv queries...")
        log_to_file(diagnostic_file, f"## arXiv Query Building\n\n")
        
        arxiv_queries = build_arxiv_queries(search_structure)
        
        # Log the built queries
        log_to_file(diagnostic_file, f"### Generated arXiv Queries\n\n")
        for i, query in enumerate(arxiv_queries, 1):
            log_to_file(diagnostic_file, f"{i}. `{query}`\n")
        log_to_file(diagnostic_file, f"\n")
        
        print(f"[{timestamp()}] Generated {len(arxiv_queries)} arXiv queries")
        
        # Step 3: Search arXiv with the structured queries
        print(f"[{timestamp()}] Searching arXiv with structured queries...")
        log_to_file(diagnostic_file, f"## arXiv Search Execution\n\n")
        
        arxiv_urls = search_arxiv_with_structured_queries(search_structure)
        
        # Log the search results count
        log_to_file(diagnostic_file, f"### Search Results\n\n")
        log_to_file(diagnostic_file, f"- **Total Results:** {len(arxiv_urls)} papers found\n\n")
        log_to_file(diagnostic_file, f"### Paper URLs\n\n")
        for i, url in enumerate(arxiv_urls, 1):
            log_to_file(diagnostic_file, f"{i}. {url}\n")
        
        print(f"[{timestamp()}] Found {len(arxiv_urls)} papers")
        
        # Step 4: Fetch metadata for each paper
        print(f"[{timestamp()}] Fetching paper metadata...")
        log_to_file(results_file, f"## Search Results\n\n")
        log_to_file(results_file, f"- **Topic:** {topic}\n")
        log_to_file(results_file, f"- **Queries:**\n")
        for query in queries:
            log_to_file(results_file, f"  - {query}\n")
        log_to_file(results_file, f"- **Total Results:** {len(arxiv_urls)} papers\n\n")
        
        # Extract arXiv IDs from the URLs
        arxiv_ids = []
        for url in arxiv_urls:
            if "/pdf/" in url:
                arxiv_id = url.split("/pdf/")[1].replace(".pdf", "")
                arxiv_ids.append(arxiv_id)
        
        # Use the arXiv API to get metadata for each paper
        import requests
        import xml.etree.ElementTree as ET
        
        # Batch the requests to avoid overwhelming the API
        BATCH_SIZE = 10
        for i in range(0, len(arxiv_ids), BATCH_SIZE):
            batch = arxiv_ids[i:i+BATCH_SIZE]
            id_list = ",".join(batch)
            
            try:
                print(f"[{timestamp()}] Fetching metadata for batch {i//BATCH_SIZE + 1}...")
                
                api_url = f"http://export.arxiv.org/api/query?id_list={id_list}"
                response = requests.get(api_url, timeout=30)
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.text)
                
                # Process each entry
                for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                    # Extract metadata
                    id_elem = entry.find('.//{http://www.w3.org/2005/Atom}id')
                    if id_elem is None or not id_elem.text:
                        continue
                    
                    arxiv_id = id_elem.text.split('/')[-1]
                    title_elem = entry.find('.//{http://www.w3.org/2005/Atom}title')
                    title = title_elem.text if title_elem is not None else "Unknown Title"
                    
                    summary_elem = entry.find('.//{http://www.w3.org/2005/Atom}summary')
                    summary = summary_elem.text if summary_elem is not None else "No abstract available"
                    
                    # Get authors
                    authors = []
                    for author_elem in entry.findall('.//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name'):
                        if author_elem is not None and author_elem.text:
                            authors.append(author_elem.text)
                    
                    # Write to results file
                    log_to_file(results_file, f"### {title}\n\n")
                    log_to_file(results_file, f"- **Authors:** {', '.join(authors)}\n")
                    log_to_file(results_file, f"- **arXiv ID:** {arxiv_id}\n")
                    log_to_file(results_file, f"- **URL:** [PDF Link](https://arxiv.org/pdf/{arxiv_id}.pdf)\n\n")
                    
                    # Add shortened abstract (first 600 characters)
                    shortened_summary = summary[:600] + "..." if len(summary) > 600 else summary
                    log_to_file(results_file, f"**Abstract:**\n\n{shortened_summary}\n\n")
                    log_to_file(results_file, f"---\n\n")
                
                # Sleep to avoid rate limiting
                import time
                time.sleep(1)
                
            except Exception as e:
                print(f"[{timestamp()}] Error fetching metadata for batch: {e}")
                log_to_file(diagnostic_file, f"\n### Error Fetching Metadata\n\n")
                log_to_file(diagnostic_file, f"Error fetching metadata for batch {i//BATCH_SIZE + 1}: {e}\n\n")
        
        print(f"\n[{timestamp()}] Search test completed successfully!")
        print(f"\nDiagnostics written to: {os.path.abspath(diagnostic_file)}")
        print(f"Search results written to: {os.path.abspath(results_file)}")
        
    except Exception as e:
        print(f"[{timestamp()}] Error during test: {e}")
        log_to_file(diagnostic_file, f"\n## Error During Test\n\n")
        log_to_file(diagnostic_file, f"Error: {e}\n\n")
        import traceback
        log_to_file(diagnostic_file, f"```\n{traceback.format_exc()}\n```\n")

if __name__ == "__main__":
    test_structured_search()


"""
Isolated test script for the structured search functionality.
Tests the enhanced arXiv search with structured queries.
To Test this file use a Windows CMD
Use window command shell if needed best to use  cmd shell  
 run the test script with CMD shell
"""