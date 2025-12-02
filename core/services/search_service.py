"""
Search service for generating search terms and searching arXiv.
Uses direct API access with targeted field search for better relevance.
Enhanced with structured search terms and field-specific queries.
"""

import logging
import json
import time
import urllib.parse
import requests
import re
import arxiv as arxiv_pkg
from typing import List, Dict, Any
from .llm_service import LLM
from ..utils.debug import debug_print


# Configure logging
logger = logging.getLogger(__name__)

def clean_abstract(abstract: str) -> str:
    """Clean and format abstract text (from Method 2)."""
    if not abstract:
        return ""
    # Remove newlines and excessive spaces
    abstract = re.sub(r'\s+', ' ', abstract)
    # Remove any LaTeX-style commands
    abstract = re.sub(r'\\[a-zA-Z]+(\{.*?\})?', '', abstract)
    return abstract.strip()



def generate_structured_search_terms(llm: LLM, topics: List[str], queries: List[str]) -> Dict:
    """Generate structured search terms optimized for arXiv's search syntax."""
    debug_print(f"Generating structured search terms for topics: {topics} and queries: {queries}")
    
    if not topics and not queries:
        debug_print("No topics or queries provided, returning basic structure")
        return {
            "exact_phrases": [],
            "title_terms": [],
            "abstract_terms": [],
            "general_terms": []
        }
    
    # Create enhanced system prompt optimized for arXiv's keyword-based search
    system_prompt = """
You are an arXiv search expert who creates SHORT, TARGETED keywords that actually find relevant papers.

CRITICAL RULES FOR ARXIV SUCCESS:
1. arXiv search works BEST with 1-3 word phrases
2. Use EXACT keywords that appear in academic paper titles
3. Start with the MAIN SUBJECT/DOMAIN first
4. Avoid connecting words (like "for", "in", "of", "the")
5. Generate MORE terms (4-5 each) but keep them SHORT

RESPONSE FORMAT:
{
  "exact_phrases": [4-5 phrases, 2-3 words max],
  "title_terms": [4-5 terms, 2-3 words max], 
  "abstract_terms": [3-4 single keywords, 1 word only, MUST PROVIDE MIN OF 3 KEYWORDS],
  "general_terms": [3-4 terms, 2-3 words max]
}

EXAMPLES OF WHAT WORKS IN ARXIV:

EXAMPLE 1 - SPORTS PSYCHOLOGY:
Topic: "sports psychology"
Query: "what is sports psychology"

✅ PERFECT FOR ARXIV:
{
  "exact_phrases": ["sports psychology", "athlete psychology", "Sport performance psychology", "sport mental", "athletic psychology"],
  "title_terms": ["sports psychology", "athlete psychology", "mental training", "sport science", "athletic behavior"],
  "abstract_terms": ["psychology", "Sport", "training", "behavior"],
  "general_terms": ["sports psychology", "athlete mental", "psychology in sport", "sport behavior"]
}

❌ BAD FOR ARXIV (too long):
{
  "exact_phrases": ["sports psychology for elite athletes", "mental resilience in sports performance"]
  ...
}

EXAMPLE 2 - FINANCIAL MARKETS:
Topic: "financial markets" 
Query: "what is market volatility"

✅ PERFECT FOR ARXIV:
{
  "exact_phrases": ["market volatility", "financial volatility", "price volatility", "volatility models", "market risk"],
  "title_terms": ["market volatility", "financial markets", "price dynamics", "volatility forecasting", "market behavior"],
  "abstract_terms": ["volatility", "markets", "finance", "risk", "stock market"],
  "general_terms": ["stock market", "market volatility", "financial risk", "price movements", "market dynamics"]
}

EXAMPLE 3 - URBAN PLANNING:
Topic: "urban planning sustainability"
Query: "green infrastructure benefits"

✅ PERFECT FOR ARXIV:
{
  "exact_phrases": ["urban planning", "green infrastructure", "sustainable cities", "urban sustainability", "smart cities"],
  "title_terms": ["urban planning", "green infrastructure", "sustainable development", "city planning", "urban design"],
  "abstract_terms": ["planning", "sustainability", "infrastructure", "urban"],
  "general_terms": ["urban sustainability", "green cities", "sustainable planning", "eco cities"]
}

KEY SUCCESS FACTORS:
- Use terms that would appear in actual paper TITLES
- Focus on the core academic field/domain
- Keep it simple and direct
- Generate enough options (4-5) for good coverage
- Think like an academic author naming their paper
    

EXAMPLE 4 - POLITICAL SCIENCE:
Topic: "democratization processes"
Query: "role of civil society in democratic transitions"

✅ PERFECT FOR ARXIV:
{
  "exact_phrases": ["democratization", "civil society", "democratic transitions", "political transitions", "democracy building"],
  "title_terms": ["democratization", "civil society", "political change", "democratic reform", "transition studies"],
  "abstract_terms": ["democratization", "democracy", "transitions", "politics"],
  "general_terms": ["democratization", "civil society", "political transitions", "democracy studies"]
}

EXAMPLE 5 - LITERATURE:
Topic: "shakespearean tragedy"
Query: "modern interpretations of hamlet psychology"

✅ PERFECT FOR ARXIV:
{
  "exact_phrases": ["shakespeare hamlet", "hamlet psychology", "shakespearean tragedy", "hamlet analysis", "tragedy studies"],
  "title_terms": ["shakespeare hamlet", "hamlet psychology", "literary analysis", "tragedy interpretation", "character analysis"],
  "abstract_terms": ["shakespeare", "hamlet", "tragedy", "psychology"],
  "general_terms": ["shakespeare hamlet", "literary psychology", "tragedy analysis", "dramatic character"]
}

EXAMPLE 6 - ENGINEERING:
Topic: "structural engineering"
Query: "composite materials for earthquake resistant buildings"

✅ PERFECT FOR ARXIV:
{
  "exact_phrases": ["structural engineering", "composite materials", "earthquake engineering", "seismic design", "building materials"],
  "title_terms": ["structural engineering", "composite materials", "earthquake resistance", "seismic structures", "building design"],
  "abstract_terms": ["engineering", "composites", "seismic", "materials"],
  "general_terms": ["structural composites", "earthquake engineering", "seismic materials", "building structures"]
}

KEY SUCCESS FACTORS:
- Use terms that would appear in actual paper TITLES
- Focus on the core academic field/domain
- Keep it simple and direct
- Generate enough options (4-5) for good coverage
- Think like an academic author naming their paper
            """
    
    # Create enhanced user prompt
    newline_char = '\n'
    user_prompt = f"""
    RESEARCH TOPICS: {', '.join(topics)}
    
    SPECIFIC RESEARCH QUESTIONS:
    {newline_char.join([f'- {q}' for q in queries])}
    
    Based on this research Topic and Questions provide by the User, generate optimized and highly relevant search terms  for finding academic papers on arXiv.
    IMPORTANT: You must first take time to understand the main research subject and key words and make sure that those words are at the front of the search terms.
    - Each search term MUST contain at least one key word from the original User topics or questions.
    Create focused search terms that will find highly relevant academic papers addressing these specific questions by the user these terms will be passed to arXiv api but dont make them generic one word phrases must be clearly aligned with what the user is searching for.
    """
    
    # Define output schema
    output_schema = {
        "type": "object",
        "properties": {
            "exact_phrases": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 exact phrases containing original query keywords, IMPORTANT: You must first take time to understand the main research subject and key words and make sure that those words are at the front of the search terms."
            },
            "title_terms": {
                "type": "array", 
                "items": {"type": "string"},
                "description": "2-3 title search terms containing original query keywords"
            },
            "abstract_terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 abstract search terms they must contain words/keyword related to the user question, Must have 3"
            },
            "general_terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-2 general search terms they must contain words/keyword related to the user question ,  "
            }
        }
    }
    
    try:
        # Get structured output
        debug_print("Calling LLM for structured search term generation")
        result = llm.structured_output(user_prompt, output_schema, system_prompt)
        debug_print(f"Received result from LLM: {result}")
        
        # Validate the result
        if not isinstance(result, dict):
            debug_print("LLM didn't return a dictionary, falling back to basic search")
            return {
                "exact_phrases": [],
                "title_terms": [],
                "abstract_terms": [],
                "general_terms": topics + queries
            }
        
        # Validate that each term contains keywords from original query
        all_keywords = set()
        for topic in topics:
            all_keywords.update([word.lower() for word in topic.split() if len(word) > 3])
        for query in queries:
            all_keywords.update([word.lower() for word in query.split() if len(word) > 3])
        
        validated_terms = {}
        
        for key in ["exact_phrases", "title_terms", "abstract_terms", "general_terms"]:
            if key not in result or not isinstance(result[key], list):
                result[key] = []
            
            # Filter terms that don't contain any keywords from the original query
            validated_terms[key] = []
            for term in result[key]:
                if term and isinstance(term, str):
                    term_words = set([word.lower() for word in term.split()])
                    # Check if there's any overlap with original keywords
                    if all_keywords and term_words.intersection(all_keywords):
                        validated_terms[key].append(term)
                    elif not all_keywords:  # If no keywords extracted, accept all terms
                        validated_terms[key].append(term)
            
            # If no terms passed validation, use original topics/queries
            if not validated_terms[key]:
                if key == "exact_phrases":
                    validated_terms[key] = [q for q in queries if ' ' in q]
                elif key == "title_terms":
                    validated_terms[key] = [t for t in topics if ' ' in t]
                elif key == "abstract_terms":
                    validated_terms[key] = [q for q in queries if q not in validated_terms["exact_phrases"]]
                elif key == "general_terms":
                    validated_terms[key] = topics + queries
        
        debug_print(f"Validated search terms: {validated_terms}")
        return validated_terms
    except Exception as e:
        debug_print(f"Error generating structured search terms: {str(e)}")
        logger.error(f"Error generating structured search terms: {e}")
        # Fallback to a basic structure
        return {
            "exact_phrases": [q for q in queries if ' ' in q],
            "title_terms": [t for t in topics if ' ' in t],
            "abstract_terms": queries,
            "general_terms": topics + queries
        }



def search_arxiv_with_structured_queries(search_structure: Dict, max_results=50, original_topics=None, original_queries=None) -> Dict[str, Any]:
    """
    Enhanced arXiv search using structured queries with result limiting and rate limiting.
    Now returns both URLs and metadata to eliminate duplicate API calls.
    
    Args:
        search_structure: Dictionary of structured search terms
        max_results: Maximum number of results to return (default: 400)
        original_topics: Optional list of original user topics to include directly in search
        original_queries: Optional list of original user queries to include directly in search
        
    Returns:
        Dict containing:
        - 'urls': List of arXiv PDF URLs (limited to max_results)
        - 'metadata': Dict mapping URLs to metadata (id, title, abstract, authors, date)
    """
    # Build queries from the structured terms
    queries = build_arxiv_queries(search_structure)
    
    # Add direct searches for original topics and queries to ensure they're included
    if original_topics:
        for topic in original_topics:
            if topic.strip():
                # Add original topics as all-field searches
                queries.append(f'all:"{topic}"')
    
    if original_queries:
        for query in original_queries:
            if query.strip():
                # Add original queries as all-field searches
                queries.append(f'all:"{query}"')
    
    debug_print(f"Searching arXiv with {len(queries)} structured queries (including original topics/queries)")
    
    all_results = []
    all_metadata = {}  # Dict mapping PDF URLs to metadata
    
    # Calculate results per query - be more generous to get better coverage
    if max_results and len(queries) > 0:
        # Increase results per query significantly for better coverage
        # For simple queries like "sports psychology", we want lots of results
        results_per_query = max(15, min(50, max_results // 2))  # At least 15, up to 50
    else:
        results_per_query = 50  # Default to higher number for better coverage
    
    debug_print(f"Fetching up to {results_per_query} results per query to reach target of {max_results}")
    debug_print(f"Using {len(queries)} queries, expecting to find {len(queries) * results_per_query} total results before deduplication")
    
    # Process queries in order of creation (most specific first)
    for i, query in enumerate(queries):
        # Don't stop early - let all queries run to get maximum coverage
        # We'll deduplicate later
        
        # Add delay between queries to respect arXiv rate limits
        if i > 0:  # Don't delay the first request
            debug_print(f"Waiting 2 seconds before next arXiv query to respect rate limits...")
            time.sleep(2)

        try:
            
            debug_print(f"Querying arXiv with: {query}")
            
            # Create arxiv search using the package for better performance
            search = arxiv_pkg.Search(
                query=query,
                max_results=results_per_query,
                sort_by=arxiv_pkg.SortCriterion.Relevance,
                sort_order=arxiv_pkg.SortOrder.Descending
            )
            
            query_results = []
            for result in search.results():
                try:
                    # Extract arXiv ID and create PDF URL
                    arxiv_id = result.get_short_id()
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
                    query_results.append(pdf_url)
                    
                    # Collect metadata (Method 2 approach)
                    paper_metadata = {
                        'id': arxiv_id,
                        'url': pdf_url,
                        'title': result.title,
                        'abstract': clean_abstract(result.summary),
                        'authors': [author.name for author in result.authors],
                        'date': result.published.strftime('%Y-%m-%d') if result.published else ""
                    }
                    all_metadata[pdf_url] = paper_metadata
                    
                    # Rate limiting for compatibility with existing system
                    time.sleep(0.1)
                    
                except Exception as result_error:
                    debug_print(f"Error processing individual result: {result_error}")
            
            debug_print(f"Found {len(query_results)} results for query: {query}")
            all_results.extend(query_results)
            
            # Respect result limit during query processing
            if max_results and len(all_results) >= max_results:
                debug_print(f"Reached target of {max_results} results, stopping search")
                break
                
        except Exception as e:
            logger.error(f"Error with query '{query}': {e}")
            debug_print(f"ERROR: {str(e)}")
    
    # Remove duplicates
    unique_results = []
    seen = set()
    for url in all_results:
        if url not in seen:
            seen.add(url)
            unique_results.append(url)
    
    # Apply final result limit
    if max_results and len(unique_results) > max_results:
        debug_print(f"Limiting {len(unique_results)} unique results to {max_results}")
        limited_results = unique_results[:max_results]
        # Filter metadata to match limited URLs
        limited_metadata = {url: all_metadata[url] for url in limited_results if url in all_metadata}
        return {
            'urls': limited_results,
            'metadata': limited_metadata
        }
    
    debug_print(f"Returning {len(unique_results)} unique results with metadata")
    # Filter metadata to match unique URLs only
    filtered_metadata = {url: all_metadata[url] for url in unique_results if url in all_metadata}
    return {
        'urls': unique_results,
        'metadata': filtered_metadata
    }
    
# File: core/services/search_service.py
def generate_search_questions(llm: LLM, topics: List[str], queries: List[str]) -> tuple:
    """Generate expanded search questions using LLM based on topics and queries."""
    debug_print(f"Generating expanded search questions for topics: {topics} and queries: {queries}")
    
    if not topics and not queries:
        debug_print("No topics or queries provided, returning empty list")
        return ([], "")
    
    # Create system prompt
    system_prompt = """You are a research assistant. Generate 3-5 specific research questions based on the user's topics and queries.
    Also provide a concise explanation (30 words max) of what the user wants to learn.

    You must return a JSON object with exactly this structure:
    {
    "questions": ["question 1", "question 2", "question 3"],
    "explanation": "concise explanation here"
    }"""
        
    # Create user prompt
    user_prompt = f"""Research Topics: {', '.join(topics)}
    User Questions: {', '.join(queries) if queries else 'None provided'}

    Generate 3-5 research questions that would help find relevant academic papers about these topics.
    Also explain in 30 words what the user is looking for."""
        
    debug_print(f"Created prompts with {len(topics)} topics and {len(queries)} queries")
    
    # Get response from LLM
    output_schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5
            },
            "explanation": {
                "type": "string",
                "minLength": 20,
                "maxLength": 60
            }
        },
        "required": ["questions", "explanation"]
    }

    try:
        debug_print("Calling LLM for expanded search questions")
        result = llm.structured_output(user_prompt, output_schema, system_prompt)
        debug_print(f"Received result from LLM: {result}")
        
        # Validate and extract
        if isinstance(result, dict):
            questions = result.get("questions", [])
            explanation = result.get("explanation", "")
            
            # Validate questions are actual questions, not schema keys
            valid_questions = [q for q in questions if len(q) > 10 and q not in ["questions", "explanation"]]
            
            if valid_questions and explanation and len(explanation) > 10:
                expanded_questions = queries + valid_questions
                debug_print(f"Got {len(valid_questions)} valid questions, total: {len(expanded_questions)}")
                debug_print(f"Explanation: {explanation}")
                return (expanded_questions, explanation)
        
        # Fallback
        debug_print("Invalid LLM response, using fallback")
        fallback_explanation = f"Research about {', '.join(topics)}" + (f" focusing on {', '.join(queries)}" if queries else "")
        return (queries if queries else topics, fallback_explanation)
        
    except Exception as e:
        debug_print(f"Error in generate_search_questions: {str(e)}")
        logger.error(f"Error generating search questions: {e}")
        fallback_explanation = f"Research about {', '.join(topics)}"
        return (queries if queries else topics, fallback_explanation)

def search_arxiv(search_terms: List[str], max_results=60) -> List[str]:
    """
    Enhanced search for arXiv papers using a combination of techniques.
    Uses field-specific queries for better relevance.
    
    Args:
        search_terms: List of search terms
        max_results: Maximum number of results to return (default: 60)
        
    Returns:
        List of arXiv PDF URLs
    """
    debug_print(f"Searching arXiv for terms: {search_terms}")
    
    # Convert the flat list of terms to a structured format for better searching
    structured_terms = {
        "exact_phrases": [term for term in search_terms if ' ' in term][:3],  # Multi-word terms as exact phrases
        "title_terms": [term for term in search_terms if ' ' not in term][:3],  # Single words to title
        "abstract_terms": [term for term in search_terms if ' ' not in term][3:6],  # More single words to abstract
        "general_terms": search_terms  # All terms are also included as general terms
    }
    
    # Use the structured search approach with result limiting
    # Pass the original search terms as both topics and queries to ensure they're included
    return search_arxiv_with_structured_queries(
        structured_terms, 
        max_results, 
        original_topics=search_terms,
        original_queries=search_terms
    )



def build_arxiv_queries(structured_terms: Dict) -> List[str]:
    """Build arXiv queries from structured search terms optimized for maximum results."""
    debug_print("Building arXiv queries from structured terms")
    queries = []
    
    # Strategy: Use fewer, broader queries to maximize results
    # arXiv works best with simple keyword searches, not complex exact phrases
    
    # 1. Add the BEST exact phrases (only 2-3 most important ones)
    exact_phrases = structured_terms.get("exact_phrases", [])
    if exact_phrases:
        # Use only the first 2 phrases to avoid over-restriction
        for phrase in exact_phrases[:2]:
            if phrase.strip():
                queries.append(f'all:"{phrase}"')
    
    # 2. Add broad title searches (these work very well in arXiv)
    for term in structured_terms.get("title_terms", [])[:3]:  # Limit to 3 best
        if term.strip():
            queries.append(f'ti:{term}')
    
    # 3. Use individual abstract terms (not combined) for better coverage
    abstract_terms = [term for term in structured_terms.get("abstract_terms", []) if term.strip()]
    if abstract_terms:
        # Use single terms instead of AND combinations
        for term in abstract_terms[:2]:  # Take first 2 terms
            queries.append(f"abs:{term}")
    
    # 4. Add broad general searches with OR logic
    general_terms = [term for term in structured_terms.get("general_terms", []) if term.strip()]
    if general_terms:
        # Create one OR query with all general terms
        general_query = " OR ".join([f"all:{term}" for term in general_terms])
        queries.append(f"({general_query})")
    
    # 5. Add a fallback broad search using any available terms
    if not queries:
        # Create a simple keyword search as fallback
        all_terms = (structured_terms.get("exact_phrases", []) + 
                    structured_terms.get("title_terms", []) +
                    structured_terms.get("general_terms", []))
        if all_terms:
            # Use the first available term for a broad search
            queries.append(f'all:{all_terms[0]}')
    
    debug_print(f"Built {len(queries)} arXiv queries: {queries}")
    return queries