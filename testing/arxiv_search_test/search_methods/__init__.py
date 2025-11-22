"""
Search method implementations for arXiv API testing.
This package contains different implementations of arXiv search methods
to be tested and compared for result relevance.
"""

from typing import Dict, List, Any, Optional

# Common result format for all search methods
ArxivPaperResult = Dict[str, Any]

# Import all search methods for easy access
from .method1 import search_arxiv as search_arxiv_method1
from .method2 import search_arxiv as search_arxiv_method2
from .method3 import search_arxiv as search_arxiv_method3
from .method4 import search_arxiv as search_arxiv_method4

# Dictionary mapping method names to their functions
SEARCH_METHODS = {
    "method1": search_arxiv_method1,
    "method2": search_arxiv_method2,
    "method3": search_arxiv_method3,
    "method4": search_arxiv_method4
}
