# arXiv Search Method Comparison Tests

This test framework compares four different implementations of arXiv search functionality to determine which method provides the most relevant results.

## Overview

All four methods use the same initial step:
- Generate structured search terms using an LLM

The methods differ in how they query the arXiv API and process the results:
1. **Method 1**: Original implementation (baseline)
2. **Method 2**: LangChain arXiv API implementation
3. **Method 3**: LlamaIndex arXiv API implementation
4. **Method 4**: Custom new approach

## Running the Tests

To run the comparison tests:

```bash
# Run all methods
python test_runner.py

# Run a specific method
python test_runner.py --method method2

# Run with a specific test case
python test_runner.py --test_case quantum_computing

# Set maximum results to return
python test_runner.py --max_results 30
```

## Analyzing Results

Each method's results are saved in the `results/{method_name}/` directory. The analysis script generates comparison reports:

```bash
# Generate comparison analysis
python analysis.py
```

## Adding New Test Queries

To add new test queries, edit the `test_queries.json` file following the existing format:

```json
{
  "id": "unique_id",
  "topics": ["Main topic"],
  "queries": ["Specific query 1", "Specific query 2"],
  "description": "Brief description of the test case"
}
```
