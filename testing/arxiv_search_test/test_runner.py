"""
Test Runner for arXiv Search Methods

This script executes tests on different arXiv search methods using a predefined set of queries
and saves the results for comparison. The goal is to determine which method provides the
most relevant search results.

Usage:
    python test_runner.py [--method method_name] [--max_results n] [--test_case test_id]

Examples:
    # Test all methods with all test cases
    python test_runner.py
    
    # Test only method2 with all test cases
    python test_runner.py --method method2
    
    # Test all methods with a specific test case
    python test_runner.py --test_case climate_change_impact
    
    # Test a specific method with a specific test case
    python test_runner.py --method method3 --test_case quantum_computing
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

# Add the parent directory to the path to allow importing core modules
sys.path.append(backend_dir)

# Import search methods
from testing.arxiv_search_test.search_methods import SEARCH_METHODS

# Import LLM and structured search term generation
from core.services.llm_service import LLM
from core.services.search_service import generate_structured_search_terms

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(
                os.path.dirname(__file__), 
                'results', 
                f'test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
        )
    ]
)

logger = logging.getLogger(__name__)

def load_test_queries() -> List[Dict[str, Any]]:
    """Return a simple test case with one topic and 3 queries."""
    return [
        {
      "id": "robotics_autonomy",
      "topics": ["Robotics and autonomy"],
      "queries": ["Autonomous navigation systems", "Robotic manipulation techniques", "best techniques in robotics"],
      "description": "Technological advancements in robotics and autonomous systems"
    }
    ]

def get_result_path(method_name: str, test_id: str, file_type: str) -> str:
    """Get the path for saving results."""
    result_dir = os.path.join(os.path.dirname(__file__), 'results', method_name)
    os.makedirs(result_dir, exist_ok=True)
    
    result_file = f"{test_id}_{file_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    return os.path.join(result_dir, result_file)

def save_metadata_to_markdown(results: List[Dict[str, Any]], method_name: str, test_case: Dict[str, Any]) -> str:
    """Save paper metadata to a markdown file."""
    test_id = test_case['id']
    result_path = get_result_path(method_name, test_id, 'metadata')
    
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"# Search Results: {method_name} - {test_case['description']}\n\n")
        f.write(f"Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write test parameters
        f.write(f"## Test Parameters\n\n")
        f.write(f"- **Method**: {method_name}\n")
        f.write(f"- **Test ID**: {test_id}\n")
        f.write(f"- **Topics**: {', '.join(test_case['topics'])}\n")
        f.write(f"- **Queries**: {', '.join(test_case['queries'])}\n")
        f.write(f"- **Total Results**: {len(results)} papers\n\n")
        
        # Write paper metadata
        f.write(f"## Papers\n\n")
        
        for i, paper in enumerate(results, 1):
            title = paper.get('title', 'Unknown Title')
            authors = paper.get('authors', [])
            arxiv_id = paper.get('id', 'unknown')
            url = paper.get('url', '')
            abstract = paper.get('abstract', 'No abstract available')
            date = paper.get('date', '')
            
            f.write(f"### {i}. {title}\n\n")
            f.write(f"- **Authors**: {', '.join(authors)}\n")
            f.write(f"- **arXiv ID**: {arxiv_id}\n")
            f.write(f"- **Date**: {date}\n")
            f.write(f"- **URL**: [PDF Link]({url})\n\n")
            
            # Add abstract
            f.write(f"**Abstract**:\n\n{abstract}\n\n")
            f.write(f"---\n\n")
    
    return result_path

def save_raw_results(raw_results: Dict[str, Any], method_name: str, test_id: str) -> str:
    """Save raw test results to a JSON file."""
    result_dir = os.path.join(os.path.dirname(__file__), 'results', method_name)
    os.makedirs(result_dir, exist_ok=True)
    
    result_file = f"{test_id}_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_path = os.path.join(result_dir, result_file)
    
    with open(result_path, 'w') as f:
        json.dump(raw_results, f, indent=2)
    
    return result_path

def run_test_for_method(
    method_name: str, 
    test_case: Dict[str, Any],
    max_results: int = 20,
    llm: Optional[LLM] = None
) -> Dict[str, Any]:
    """Run a test for a specific method and test case."""
    logger.info(f"Testing {method_name} with test case: {test_case['id']}")
    
    # Get the search function for this method
    search_function = SEARCH_METHODS.get(method_name)
    if not search_function:
        logger.error(f"Method {method_name} not found")
        return {
            "error": f"Method {method_name} not found",
            "test_case": test_case['id'],
            "method": method_name,
            "results": []
        }
    
    # Extract topics and queries
    topics = test_case.get('topics', [])
    queries = test_case.get('queries', [])
    
    # Create or use the provided LLM instance
    if llm is None:
        llm = LLM()
    
    # Generate structured search terms with the LLM
    logger.info(f"Generating structured search terms with LLM")
    structured_terms = generate_structured_search_terms(llm, topics, queries)
    
    # Run the search
    start_time = time.time()
    try:
        results = search_function(structured_terms, max_results, topics, queries)
        success = True
        error = None
    except Exception as e:
        logger.error(f"Error running {method_name} for {test_case['id']}: {e}")
        results = []
        success = False
        error = str(e)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Save the results
    if success and results:
        metadata_path = save_metadata_to_markdown(results, method_name, test_case)
        logger.info(f"Metadata saved to {metadata_path}")
    
    # Compile results
    test_results = {
        "test_case": test_case['id'],
        "method": method_name,
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "error": error,
        "execution_time_seconds": execution_time,
        "query_details": {
            "topics": topics,
            "queries": queries,
            "structured_terms": structured_terms
        },
        "results": results,
        "total_results": len(results),
        "max_requested": max_results
    }
    
    # Save the raw results
    raw_path = save_raw_results(test_results, method_name, test_case['id'])
    logger.info(f"Raw results saved to {raw_path}")
    
    return test_results

def run_tests(
    methods: Optional[List[str]] = None,
    test_case_ids: Optional[List[str]] = None,
    max_results: int = 20
) -> None:
    """Run tests for specified methods and test cases."""
    # Load test queries
    test_cases = load_test_queries()
    
    # Filter test cases if specified
    if test_case_ids:
        test_cases = [tc for tc in test_cases if tc['id'] in test_case_ids]
    
    if not test_cases:
        logger.error("No test cases found")
        return
    
    # Determine which methods to test
    if not methods:
        methods = list(SEARCH_METHODS.keys())
    else:
        # Only include valid methods
        methods = [m for m in methods if m in SEARCH_METHODS]
    
    if not methods:
        logger.error("No valid methods specified")
        return
    
    # Initialize LLM once to reuse
    llm = LLM()
    
    # Run tests for each method and test case
    results = []
    for method_name in methods:
        for test_case in test_cases:
            result = run_test_for_method(method_name, test_case, max_results, llm)
            results.append(result)
    
    # Generate summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "methods_tested": methods,
        "test_cases": [tc['id'] for tc in test_cases],
        "total_tests": len(results),
        "successful_tests": sum(1 for r in results if r.get("success", False)),
        "max_results_per_test": max_results,
        "summary_by_method": {
            method: {
                "total_tests": len([r for r in results if r["method"] == method]),
                "successful_tests": len([r for r in results if r["method"] == method and r.get("success", False)]),
                "avg_execution_time": sum([r.get("execution_time_seconds", 0) for r in results if r["method"] == method]) / 
                                    len([r for r in results if r["method"] == method]) if len([r for r in results if r["method"] == method]) > 0 else 0,
                "avg_results_returned": sum([r.get("total_results", 0) for r in results if r["method"] == method]) / 
                                       len([r for r in results if r["method"] == method]) if len([r for r in results if r["method"] == method]) > 0 else 0
            } for method in methods
        }
    }
    
    # Save summary
    summary_path = os.path.join(
        os.path.dirname(__file__), 
        'results', 
        f'summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Test run complete. Summary saved to {summary_path}")

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Test Runner for arXiv Search Methods")
    parser.add_argument("--method", help="Specific method to test")
    parser.add_argument("--test_case", help="Specific test case to run")
    parser.add_argument("--max_results", type=int, default=20, 
                      help="Maximum results to return per test")
    
    args = parser.parse_args()
    
    methods = [args.method] if args.method else None
    test_cases = [args.test_case] if args.test_case else None
    
    run_tests(methods=methods, test_case_ids=test_cases, max_results=args.max_results)

if __name__ == "__main__":
    main()
