"""
Analysis Script for arXiv Search Method Comparison

This script analyzes the results from different search methods,
generating comparative metrics and visualizations to determine
which method provides the most relevant papers.

Usage:
    python analysis.py [--summary summary_file]

Examples:
    # Analyze using the latest summary file
    python analysis.py
    
    # Analyze a specific summary file
    python analysis.py --summary results/summary_20251112_123045.json
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

def find_latest_summary() -> str:
    """Find the most recent summary file."""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    summary_files = glob.glob(os.path.join(results_dir, 'summary_*.json'))
    
    if not summary_files:
        raise FileNotFoundError("No summary files found in results directory")
    
    # Sort by modification time (most recent first)
    summary_files.sort(key=os.path.getmtime, reverse=True)
    return summary_files[0]

def load_summary(summary_path: str) -> Dict[str, Any]:
    """Load a summary file."""
    with open(summary_path, 'r') as f:
        return json.load(f)

def find_test_results(method: str, test_id: str) -> Optional[str]:
    """Find the most recent test results for a method and test case."""
    method_dir = os.path.join(os.path.dirname(__file__), 'results', method)
    if not os.path.exists(method_dir):
        return None
        
    result_files = glob.glob(os.path.join(method_dir, f"{test_id}_metadata_*.md"))
    
    if not result_files:
        return None
    
    # Sort by modification time (most recent first)
    result_files.sort(key=os.path.getmtime, reverse=True)
    return result_files[0]

def generate_comparison_report(methods: List[str], test_id: str) -> Optional[str]:
    """
    Generate a comparison report for a specific test case across all methods.
    Returns the path to the generated report.
    """
    # Find results files for all methods
    results_files = {}
    for method in methods:
        result_file = find_test_results(method, test_id)
        if result_file:
            results_files[method] = result_file
    
    if not results_files:
        print(f"No results found for test case {test_id}")
        return None
    
    # Create the comparison report
    report_path = os.path.join(
        os.path.dirname(__file__),
        'results',
        f'comparison_{test_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    )
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Method Comparison for Test Case: {test_id}\n\n")
        f.write(f"Comparison generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write a summary of the methods compared
        f.write(f"## Methods Compared\n\n")
        for method in methods:
            if method in results_files:
                f.write(f"- **{method}**: Results available\n")
            else:
                f.write(f"- **{method}**: No results found\n")
        f.write("\n")
        
        # For each method with results, extract the first 5 papers for comparison
        f.write(f"## Top Results Comparison\n\n")
        
        # Use a table to show the top papers from each method side by side
        f.write(f"| Rank |")
        for method in methods:
            if method in results_files:
                f.write(f" {method} |")
        f.write("\n")
        
        f.write(f"|------|")
        for method in methods:
            if method in results_files:
                f.write(f"---|")
        f.write("\n")
        
        # Extract titles for the first 5 papers from each method
        top_papers = {}
        for method in methods:
            if method in results_files:
                top_papers[method] = []
                with open(results_files[method], 'r', encoding='utf-8') as mf:
                    lines = mf.readlines()
                    for i, line in enumerate(lines):
                        if line.startswith("### "):
                            # Extract title (remove rank number and period)
                            title_parts = line[4:].strip().split('. ', 1)
                            if len(title_parts) > 1:
                                title = title_parts[1]
                            else:
                                title = title_parts[0]
                            top_papers[method].append(title)
                            
                            # Only take the first 5 papers
                            if len(top_papers[method]) >= 5:
                                break
        
        # Write the table rows for the first 5 papers
        for i in range(5):
            f.write(f"| {i+1} |")
            for method in methods:
                if method in results_files and i < len(top_papers[method]):
                    f.write(f" {top_papers[method][i]} |")
                elif method in results_files:
                    f.write(" - |")
            f.write("\n")
        
        # Write full method-specific sections for more detailed comparison
        f.write(f"## Detailed Results\n\n")
        
        for method in methods:
            if method in results_files:
                f.write(f"### {method}\n\n")
                
                # Copy content from the method's results file, excluding the header
                with open(results_files[method], 'r', encoding='utf-8') as mf:
                    content = mf.read()
                    # Skip the first few lines (title and date)
                    content_parts = content.split("## Test Parameters")
                    if len(content_parts) > 1:
                        f.write("## Test Parameters" + content_parts[1])
                    else:
                        f.write(content)
                
                f.write("\n\n")
    
    print(f"Comparison report generated: {report_path}")
    return report_path

def analyze_summary(summary_path: Optional[str] = None) -> None:
    """Analyze the test results from a summary file."""
    # Find or use the specified summary file
    if not summary_path:
        try:
            summary_path = find_latest_summary()
            print(f"Using latest summary file: {summary_path}")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return
    
    # Load the summary file
    try:
        summary = load_summary(summary_path)
    except Exception as e:
        print(f"Error loading summary file: {e}")
        return
    
    # Extract methods and test cases
    methods = summary.get('methods_tested', [])
    test_cases = summary.get('test_cases', [])
    
    if not methods or not test_cases:
        print("No methods or test cases found in summary")
        return
    
    # Generate comparison reports for each test case
    for test_id in test_cases:
        report_path = generate_comparison_report(methods, test_id)
        if report_path:
            print(f"Comparison report for {test_id} generated: {report_path}")
    
    # Generate an overall comparison summary
    overall_path = os.path.join(
        os.path.dirname(__file__),
        'results',
        f'overall_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    )
    
    with open(overall_path, 'w') as f:
        f.write("# Overall Method Comparison\n\n")
        f.write(f"Analysis generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write summary statistics
        f.write("## Summary Statistics\n\n")
        f.write("| Method | Tests Run | Success Rate | Avg. Execution Time (s) | Avg. Results |\n")
        f.write("|--------|-----------|-------------|-------------------------|-------------|\n")
        
        for method in methods:
            method_stats = summary.get('summary_by_method', {}).get(method, {})
            total_tests = method_stats.get('total_tests', 0)
            successful_tests = method_stats.get('successful_tests', 0)
            success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
            avg_time = method_stats.get('avg_execution_time', 0)
            avg_results = method_stats.get('avg_results_returned', 0)
            
            f.write(f"| {method} | {total_tests} | {success_rate:.1f}% | {avg_time:.2f} | {avg_results:.1f} |\n")
        
        f.write("\n")
        
        # Provide links to individual comparison reports
        f.write("## Test Case Comparisons\n\n")
        for test_id in test_cases:
            f.write(f"- [{test_id}](comparison_{test_id}_*.md)\n")
    
    print(f"Overall comparison report generated: {overall_path}")

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Analysis Script for arXiv Search Method Comparison")
    parser.add_argument("--summary", help="Path to a specific summary file to analyze")
    
    args = parser.parse_args()
    
    analyze_summary(args.summary)

if __name__ == "__main__":
    main()
