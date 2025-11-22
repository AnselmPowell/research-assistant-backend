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

# Configure logging
logger = logging.getLogger(__name__)

# Enable debug printing
DEBUG_PRINT = True

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[SEARCH] {message}")

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
    
    # Create enhanced system prompt that enforces inclusion of original query terms
    system_prompt = """
            You are an academic search expert who specializes in arXiv's search syntax and generating search terms for students looking for relevant papers.

            TASK:
            Generate optimised search queries for arXiv based on the user's research needs. These search queries MUST position the most important domain keywords at the BEGINNING of each phrase to maximize relevance in arXiv's search algorithm. You  look carefully and understand the main research subject the user is mentioning make sure that those words are at the front of the search terms to get more relevant results from arXiv. For example "user topic: democratization civil society in Africa."  In this subject AFRICA is the main subject so in your search terms will move this to the BEGINNING to get more result related to the African economy.  

            WHY THIS IS CRITICAL:
            arXiv's search algorithm gives higher weight to terms that appear at the beginning of search phrases. Placing domain keywords first dramatically improves search relevance by ensuring results stay focused on the user's specific field.
            \n
            STRICT RULES FOR ARXIV SEARCH OPTIMIZATION:
            1. EVERY search term MUST start with the core domain keywords from the user's main topic
            2. Keep the user's exact terminology whenever possible or close if possible.
            3. Limit each search term to 5-6 words maximum for optimal arXiv search performance
            4. Include at least one key term from the user's specific query in each search phrase
            5. Never use generic terms that could apply to any fields - always maintain domain specificity
            MAIN POINT: UNDERSTAND WHAT THE USER IS TRYING TO SAY AND SEARCH FOR, UNDERSTAND THERE INTENT AND PUT THOSE WORDS NEAR THE FRONT OF THE SEARCH TERMS 
            IMPORTANT: You must first take time to understand the main research subject and key words and make sure that those words are at the front of the search terms.
            \n
            RESPONSE FORMAT:
            Return a JSON object with these keys:
            1. "exact_phrases": 2-3 exact phrases that START WITH domain keywords (2-3 words max)
            2. "title_terms": 2-3 title search terms that START WITH domain keywords (3-5 words max)
            3. "abstract_terms": 2-3 abstract search terms 1 word single-keywords most relevant to the subject (1-2 words max, single concepts only)
            4. "general_terms": 1-2 general search terms that START WITH domain keywords (2-4 words max)
            \n\n
            EXAMPLES OF PROPERLY STRUCTURED SEARCH TERMS:

            EXAMPLE 1 - SPORTS PSYCHOLOGY:
            Topic: Sports psychology for elite athletes
            Query: Mental resilience techniques for performance under pressure

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["sports psychology mental resilience techniques", "elite athletes performance under pressure", "sports psychology performance pressure techniques"],
            "title_terms": ["elite athletes mental resilience", "sports psychology pressure performance", "athlete psychology resilience techniques"],
            "abstract_terms": ["performance", "resilience", "training"],
            "general_terms": ["sports psychology resilience", "elite athletes performance"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["mental resilience techniques for athletes", "performance under pressure training", "techniques for sports psychology"],
            "title_terms": ["resilience in elite athletes", "pressure performance sports", "psychological techniques athletes"],
            "abstract_terms": ["mental training for performance", "resilience techniques sports", "pressure handling methods athletes"],
            "general_terms": ["performance psychology", "mental resilience sports"]
            }

            EXAMPLE 2 - PHILOSOPHY:
            Topic: Existentialist philosophy
            Query: Sartre's concept of bad faith in modern society

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["existentialist philosophy sartre bad faith", "existentialism bad faith modern society", "philosophy sartre concept modern application"],
            "title_terms": ["existentialist bad faith concept", "philosophy sartre modern society", "existentialism sartre authenticity analysis"],
            "abstract_terms": ["authenticity", "consciousness", "freedom"],
            "general_terms": ["existentialist bad faith", "philosophy sartre modern"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["bad faith concept by sartre", "modern applications of existentialism", "analysis of sartre's philosophical concepts"],
            "title_terms": ["concept of bad faith", "sartre's existentialist ideas", "philosophical analysis of authenticity"],
            "abstract_terms": ["bad faith in contemporary society", "existential concepts in modernity", "philosophical implications of sartre"],
            "general_terms": ["bad faith existentialism", "sartrean concepts"]
            }

            EXAMPLE 3 - HISTORY:
            Topic: Medieval European warfare
            Query: Evolution of siege tactics during the Crusades

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["medieval warfare siege tactics crusades", "medieval european crusades siege evolution", "medieval warfare crusades military developments"],
            "title_terms": ["medieval siege tactics evolution", "crusades warfare technological developments", "medieval military siege strategy"],
            "abstract_terms": ["medieval crusades", "siege engines", "european warfare"],
            "general_terms": ["medieval crusades siege", "european warfare crusades"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["siege tactics used in crusades", "evolution of medieval military strategy", "developments in warfare during crusades"],
            "title_terms": ["siege warfare evolution", "crusade military tactics", "evolution of warfare techniques"],
            "abstract_terms": ["historical siege engines development", "military tactics in medieval period", "crusades impact on warfare"],
            "general_terms": ["medieval siege warfare", "crusades military history"]
            }

            EXAMPLE 4 - SOCIOLOGY:
            Topic: Urban sociology
            Query: Impact of gentrification on community cohesion

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["urban sociology gentrification community impact", "sociology gentrification community cohesion effects", "urban community gentrification social changes"],
            "title_terms": ["urban gentrification community cohesion", "sociology neighborhood displacement effects", "urban community social fragmentation"],
            "abstract_terms": ["urban", "gentrification", "community"],
            "general_terms": ["urban gentrification effects", "sociology community displacement"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["gentrification effects on urban communities", "community cohesion challenges in cities", "social consequences of neighborhood transformation"],
            "title_terms": ["impact of gentrification", "community changes research", "urban social dynamics"],
            "abstract_terms": ["socioeconomic shifts neighborhoods", "displacement of original residents", "social fabric in changing communities"],
            "general_terms": ["urban change studies", "community sociology research"]
            }

            EXAMPLE 5 - PSYCHOLOGY:
            Topic: Developmental psychology
            Query: Effects of early childhood trauma on adult attachment styles

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["developmental psychology childhood trauma attachment", "psychology trauma adult attachment effects", "developmental childhood trauma attachment relationships"],
            "title_terms": ["developmental trauma attachment styles", "psychology childhood trauma effects", "developmental attachment trauma patterns"],
            "abstract_terms": ["developmental trauma adult relationships", "psychology attachment trauma studies", "developmental childhood adverse experiences"],
            "general_terms": ["developmental trauma attachment", "psychology childhood relationships"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["childhood trauma effects on attachment", "attachment styles influenced by trauma", "adult relationship patterns after trauma"],
            "title_terms": ["trauma and attachment", "childhood adverse experiences", "adult relationship difficulties"],
            "abstract_terms": ["early trauma consequences", "attachment theory applications", "psychological effects of maltreatment"],
            "general_terms": ["trauma studies", "attachment research"]
            }

            EXAMPLE 6 - POLITICAL SCIENCE:
            Topic: Democratization processes
            Query: Role of civil society in democratic transitions

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["democratization civil society transitions role", "political science democratic transitions civil", "democratization processes civil organizations role"],
            "title_terms": ["democratization civil society role", "political democratic transitions mechanisms", "democratization civil resistance studies"],
            "abstract_terms": ["democratization civil organizations impact", "political transitions civil participation", "democratization social movements influence"],
            "general_terms": ["democratization civil society", "political democratic transitions"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["civil society's role in democratization", "democratic transitions through social movements", "influence of NGOs on political change"],
            "title_terms": ["civil society impact", "democratic transition studies", "political change analysis"],
            "abstract_terms": ["social movements in transitions", "civil resistance effectiveness", "non-governmental organization roles"],
            "general_terms": ["civil society studies", "democratic transition research"]
            }

            EXAMPLE 7 - DRAMA:
            Topic: Shakespearean tragedy
            Query: Modern interpretations of Hamlet's psychological complexity

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["shakespearean tragedy hamlet psychological interpretations", "drama hamlet psychological complexity modern", "shakespearean hamlet psychology contemporary analysis"],
            "title_terms": ["shakespearean hamlet psychological readings", "drama tragedy modern interpretations", "shakespearean character psychology analysis"],
            "abstract_terms": ["hamlet, "drama ", "contemporary""],
            "general_terms": ["shakespearean hamlet psychology", "drama tragedy interpretations"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["psychological complexity in hamlet", "modern interpretations of shakespeare", "character analysis in tragedy"],
            "title_terms": ["hamlet's psychology", "modern theatrical interpretations", "character complexity studies"],
            "abstract_terms": ["psychological readings of classics", "theatrical character development", "dramatic psychological elements"],
            "general_terms": ["hamlet studies", "dramatic psychology"]
            }

            EXAMPLE 8 - ENGINEERING:
            Topic: Structural engineering
            Query: Advanced composite materials for earthquake-resistant buildings

            ✅ GOOD STRUCTURE:
            {
            "exact_phrases": ["structural engineering composite materials earthquake", "engineering earthquake-resistant composite applications", "structural composite materials building performance"],
            "title_terms": ["structural composite earthquake resistance", "engineering advanced materials buildings", "structural seismic composite development"],
            "abstract_terms": ["earthquake", "engineering", "seismic design"],
            "general_terms": ["structural composite materials", "engineering earthquake resistance"]
            }

            ❌ BAD STRUCTURE:
            {
            "exact_phrases": ["composite materials for seismic design", "earthquake resistance through advanced materials", "building performance with composites"],
            "title_terms": ["advanced composite applications", "seismic building design", "material science innovations"],
            "abstract_terms": ["earthquake engineering developments", "material performance in structures", "building resistance technologies"],
            "general_terms": ["composite materials research", "seismic engineering studies"]
            }

            REMEMBER: Always position the MAIN DOMAIN TERMS at the BEGINNING of each search phrase to maximize arXiv search relevance!
            IMPORTANT: You must first take time to understand the main research subject and key words and make sure that those words are at the BEGINNING of the search terms.
            """
    
    # Create enhanced user prompt
    user_prompt = f"""
    RESEARCH TOPICS: {', '.join(topics)}
    
    SPECIFIC RESEARCH QUESTIONS:
    {'\n'.join([f'- {q}' for q in queries])}
    
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
                "description": "2-3 abstract search terms they must contain words/keyword from the original user query"
            },
            "general_terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-2 general search terms they must contain words from the  original user query ,  "
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



def search_arxiv_with_structured_queries(search_structure: Dict, max_results=400, original_topics=None, original_queries=None) -> Dict[str, Any]:
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
    
    # Calculate results per query to distribute fairly
    if max_results and len(queries) > 0:
        # Add 1 to ensure we get enough results even with duplicates
        results_per_query = min(30, (max_results // len(queries)) + 1)
    else:
        results_per_query = 30
    
    debug_print(f"Fetching up to {results_per_query} results per query to reach target of {max_results}")
    
    # Process queries in order of creation (most specific first)
    for i, query in enumerate(queries):
        # Check if we already have enough results
        if max_results and len(all_results) >= max_results:
            debug_print(f"Already have {len(all_results)} results, stopping search")
            break
        
        # Add delay between queries to respect arXiv rate limits
        if i > 0:  # Don't delay the first request
            debug_print(f"Waiting 1.2 seconds before next arXiv query to respect rate limits...")
            time.sleep(1.2)

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
    """Build arXiv queries from structured search terms."""
    debug_print("Building arXiv queries from structured terms")
    queries = []
    
    # Add exact phrase searches in all fields
    for phrase in structured_terms.get("exact_phrases", []):
        if phrase.strip():
            queries.append(f'all:"{phrase}"')
    
    # Add title-specific searches
    for term in structured_terms.get("title_terms", []):
        if term.strip():
            queries.append(f'ti:{term}')
    
    # Add abstract-specific searches as combined AND query
    abstract_terms = [term for term in structured_terms.get("abstract_terms", []) if term.strip()]
    if abstract_terms:
        abstract_query = " AND ".join([f"abs:{term}" for term in abstract_terms])
        queries.append(f"({abstract_query})")
    
    # Add general terms with logical OR between them
    general_terms = [term for term in structured_terms.get("general_terms", []) if term.strip()]
    if general_terms:
        general_query = " OR ".join([f"all:{term}" for term in general_terms])
        queries.append(f"({general_query})")
    
    # If no valid queries were generated, create a fallback query
    if not queries and structured_terms.get("general_terms"):
        fallback_term = " AND ".join(structured_terms["general_terms"][:2])
        queries.append(f'all:{fallback_term}')
    
    debug_print(f"Built {len(queries)} arXiv queries: {queries}")
    return queries