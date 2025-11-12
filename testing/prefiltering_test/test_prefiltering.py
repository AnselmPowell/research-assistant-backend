#!/usr/bin/env python
"""
Isolated test script for the paper pre-filtering functionality.
Tests the enhanced arXiv search with structured queries followed by URL pre-filtering.
This test demonstrates the complete pipeline from search to pre-filtering.

To run this test:
1. Use Windows Command Prompt (cmd)
2. Navigate to the backend directory
3. Run: python testing/prefiltering_test/test_prefiltering.py
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
from core.services.paper_filter_service import (
    filter_paper_urls,
    fetch_paper_metadata
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
    print("\n===== Pre-filtering Test =====\n")
    
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

def test_prefiltering():
    """Test the complete search and pre-filtering pipeline."""
    # File paths for output
    current_dir = os.path.dirname(os.path.abspath(__file__))
    diagnostic_file = os.path.join(current_dir, "filter_diagnostics.md")
    results_file = os.path.join(current_dir, "filter_results.md")
    filtered_file = os.path.join(current_dir, "filtered_papers.md")
    
    # Initialize output files with headers
    log_to_file(diagnostic_file, create_markdown_header("Search and Pre-filtering Diagnostics"), 'w')
    log_to_file(results_file, create_markdown_header("Search Results"), 'w')
    log_to_file(filtered_file, create_markdown_header("Filtered Papers"), 'w')
    
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
        
        # Step 4: Generate search questions (for expanded context)
        print(f"[{timestamp()}] Generating expanded search questions...")
        
        # Use the LLM to generate expanded questions and explanation
        system_prompt = """
        Generate expanded research questions and a concise explanation based on the user's topic and queries.
        
        Return a JSON object with this structure:
        {
          "expanded_questions": ["question 1", "question 2", "question 3"],
          "explanation": "A concise explanation of what the user is looking for"
        }
        """
        
        user_prompt = f"""
        Research Topic: {topic}
        User Questions: {', '.join(queries)}
        
        Generate 3-5 expanded research questions and a brief explanation (30-50 words) that captures the essence 
        of this research request.
        """
        
        output_schema = {
            "type": "object",
            "properties": {
                "expanded_questions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "explanation": {"type": "string"}
            }
        }
        
        expanded_result = llm.structured_output(user_prompt, output_schema, system_prompt)
        expanded_questions = expanded_result.get("expanded_questions", queries)
        explanation = expanded_result.get("explanation", f"Research about {topic} focusing on {', '.join(queries)}")
        
        log_to_file(diagnostic_file, f"## Expanded Search Questions\n\n")
        log_to_file(diagnostic_file, f"### Questions\n\n")
        for question in expanded_questions:
            log_to_file(diagnostic_file, f"- {question}\n")
        log_to_file(diagnostic_file, f"\n### Explanation\n\n{explanation}\n\n")
        
        # Step 5: Pre-filter the papers based on metadata
        print(f"[{timestamp()}] Pre-filtering papers based on metadata...")
        log_to_file(diagnostic_file, f"## Pre-filtering Papers\n\n")
        
        filter_result = filter_paper_urls(
            arxiv_urls, 
            [topic], 
            expanded_questions, 
            explanation,
            additional_search_terms=search_structure.get('general_terms', [])
        )
        
        log_to_file(diagnostic_file, f"### Pre-filtering Results\n\n")
        log_to_file(diagnostic_file, f"- **Total URLs:** {len(arxiv_urls)}\n")
        log_to_file(diagnostic_file, f"- **Relevant URLs:** {filter_result.get('papers_relevant', 0)}\n")
        log_to_file(diagnostic_file, f"- **Filtered URLs:** {filter_result.get('papers_filtered', 0)}\n")
        log_to_file(diagnostic_file, f"- **Success:** {filter_result.get('success', False)}\n")
        log_to_file(diagnostic_file, f"- **Message:** {filter_result.get('message', '')}\n\n")
        
        # Log the relevant URLs
        relevant_urls = filter_result.get('relevant_urls', [])
        log_to_file(diagnostic_file, f"### Relevant URLs ({len(relevant_urls)})\n\n")
        for i, url in enumerate(relevant_urls, 1):
            log_to_file(diagnostic_file, f"{i}. {url}\n")
        
        # Log the filtered out URLs
        filtered_urls = [url for url in arxiv_urls if url not in relevant_urls]
        log_to_file(diagnostic_file, f"\n### Filtered URLs ({len(filtered_urls)})\n\n")
        for i, url in enumerate(filtered_urls, 1):
            log_to_file(diagnostic_file, f"{i}. {url}\n")
        
        print(f"[{timestamp()}] Pre-filtering completed: {len(relevant_urls)} relevant, {len(filtered_urls)} filtered out")
        
        # Step 6: Fetch metadata for all papers (both relevant and filtered)
        print(f"[{timestamp()}] Fetching metadata for papers...")
        
        # Fetch metadata for all papers to compare
        all_metadata = fetch_paper_metadata(arxiv_urls)
        
        # Separate metadata for relevant and filtered papers
        relevant_metadata = [meta for meta in all_metadata if meta['url'] in relevant_urls]
        filtered_metadata = [meta for meta in all_metadata if meta['url'] in filtered_urls]
        
        # Write results for all papers
        log_to_file(results_file, f"## Search Results (All Papers)\n\n")
        log_to_file(results_file, f"- **Topic:** {topic}\n")
        log_to_file(results_file, f"- **Queries:**\n")
        for query in queries:
            log_to_file(results_file, f"  - {query}\n")
        log_to_file(results_file, f"- **Total Results:** {len(all_metadata)} papers\n\n")
        
        # Write the filtered papers results
        log_to_file(filtered_file, f"## Paper Filtering Results\n\n")
        log_to_file(filtered_file, f"- **Topic:** {topic}\n")
        log_to_file(filtered_file, f"- **Queries:**\n")
        for query in queries:
            log_to_file(filtered_file, f"  - {query}\n")
        log_to_file(filtered_file, f"- **Total Papers:** {len(all_metadata)}\n")
        log_to_file(filtered_file, f"- **Relevant Papers:** {len(relevant_metadata)}\n")
        log_to_file(filtered_file, f"- **Filtered Papers:** {len(filtered_metadata)}\n\n")
        
        # Write all relevant papers with their metadata
        log_to_file(filtered_file, f"## Relevant Papers\n\n")
        for i, meta in enumerate(relevant_metadata, 1):
            title = meta.get('title', 'Unknown Title')
            authors = meta.get('authors', [])
            arxiv_id = meta.get('id', 'unknown')
            url = meta.get('url', '')
            abstract = meta.get('abstract', 'No abstract available')
            
            # Write to filtered file
            log_to_file(filtered_file, f"### {i}. {title}\n\n")
            log_to_file(filtered_file, f"- **Authors:** {', '.join(authors)}\n")
            log_to_file(filtered_file, f"- **arXiv ID:** {arxiv_id}\n")
            log_to_file(filtered_file, f"- **URL:** [PDF Link]({url})\n\n")
            
            # Add shortened abstract (first 600 characters)
            shortened_abstract = abstract[:600] + "..." if len(abstract) > 600 else abstract
            log_to_file(filtered_file, f"**Abstract:**\n\n{shortened_abstract}\n\n")
            log_to_file(filtered_file, f"---\n\n")
        
        # Write all filtered papers with their metadata
        log_to_file(filtered_file, f"## Filtered Papers\n\n")
        for i, meta in enumerate(filtered_metadata, 1):
            title = meta.get('title', 'Unknown Title')
            authors = meta.get('authors', [])
            arxiv_id = meta.get('id', 'unknown')
            url = meta.get('url', '')
            abstract = meta.get('abstract', 'No abstract available')
            
            # Write to filtered file
            log_to_file(filtered_file, f"### {i}. {title}\n\n")
            log_to_file(filtered_file, f"- **Authors:** {', '.join(authors)}\n")
            log_to_file(filtered_file, f"- **arXiv ID:** {arxiv_id}\n")
            log_to_file(filtered_file, f"- **URL:** [PDF Link]({url})\n\n")
            
            # Add shortened abstract (first 600 characters)
            shortened_abstract = abstract[:600] + "..." if len(abstract) > 600 else abstract
            log_to_file(filtered_file, f"**Abstract:**\n\n{shortened_abstract}\n\n")
            log_to_file(filtered_file, f"---\n\n")
        
        # Write the results for search results file (all papers - for backward compatibility)
        for meta in all_metadata:
            title = meta.get('title', 'Unknown Title')
            authors = meta.get('authors', [])
            arxiv_id = meta.get('id', 'unknown')
            url = meta.get('url', '')
            abstract = meta.get('abstract', 'No abstract available')
            
            relevance_status = "✅ RELEVANT" if url in relevant_urls else "❌ FILTERED OUT"
            
            # Write to results file
            log_to_file(results_file, f"### {title}\n\n")
            log_to_file(results_file, f"- **Status:** {relevance_status}\n")
            log_to_file(results_file, f"- **Authors:** {', '.join(authors)}\n")
            log_to_file(results_file, f"- **arXiv ID:** {arxiv_id}\n")
            log_to_file(results_file, f"- **URL:** [PDF Link]({url})\n\n")
            
            # Add shortened abstract (first 600 characters)
            shortened_abstract = abstract[:600] + "..." if len(abstract) > 600 else abstract
            log_to_file(results_file, f"**Abstract:**\n\n{shortened_abstract}\n\n")
            log_to_file(results_file, f"---\n\n")
        
        print(f"\n[{timestamp()}] Pre-filtering test completed successfully!")
        print(f"\nDiagnostics written to: {os.path.abspath(diagnostic_file)}")
        print(f"Search results written to: {os.path.abspath(results_file)}")
        print(f"Filtered papers written to: {os.path.abspath(filtered_file)}")
        
    except Exception as e:
        print(f"[{timestamp()}] Error during test: {e}")
        log_to_file(diagnostic_file, f"\n## Error During Test\n\n")
        log_to_file(diagnostic_file, f"Error: {e}\n\n")
        import traceback
        log_to_file(diagnostic_file, f"```\n{traceback.format_exc()}\n```\n")

if __name__ == "__main__":
    test_prefiltering()
