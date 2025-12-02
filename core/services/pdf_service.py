"""
PDF service for processing PDFs and extracting information.
"""

import logging
import os
import tempfile
import requests
import re
import hashlib
import mimetypes
import time
from typing import List, Dict, Any
import fitz  # PyMuPDF
from tenacity import retry, stop_after_attempt, wait_exponential
from django.conf import settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from .embedding_service import get_embedding, validate_note_relevance, calculate_similarity, get_google_embeddings_batch, calculate_cosine_similarities
from .llm_service import LLM
from ..utils.debug import debug_print

# Configure logging
logger = logging.getLogger(__name__)



def normalize_url(url: str) -> str:
    """Normalize URL to ensure it's a direct PDF link."""
    # Convert arXiv abstract URLs to PDF URLs
    if "/abs/" in url and "arxiv.org" in url:
        url = url.replace("/abs/", "/pdf/")
        # Don't add .pdf - arXiv handles URLs correctly without extension
    return url

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_pdf(url: str) -> str:
    """Download a PDF from a URL and return the local path."""
    debug_print(f"Downloading PDF from: {url}")
    
    # Add delay to respect arXiv rate limits (1 request per 3 seconds)
    # Increased to 2 seconds due to parallel workers
    time.sleep(1)
    
    try:
        headers = {
            'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool; mailto:research@example.com)',
            'Accept': 'application/pdf'
        }
        
        # Add content-type validation
        try:
            response = requests.head(url, headers=headers, timeout=10)
            content_type = response.headers.get('Content-Type', '')
            if not content_type.lower().startswith('application/pdf'):
                logger.warning(f"URL does not appear to be a PDF: {url} (Content-Type: {content_type})")
                debug_print(f"WARNING: URL content type is {content_type}, not application/pdf")
                # Still proceed, but with warning
            
            # Add file size limit
            max_size = 50 * 1024 * 1024  # 50 MB
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > max_size:
                logger.error(f"PDF too large: {url} ({int(content_length) / (1024*1024):.2f} MB)")
                debug_print(f"ERROR: PDF too large: {int(content_length) / (1024*1024):.2f} MB (max: 50 MB)")
                return None
        except Exception as e:
            logger.warning(f"Could not perform pre-download checks: {e}")
            debug_print(f"WARNING: Pre-download checks failed: {str(e)}")
            # Continue with download attempt
        
        # Get the file
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Use a more secure temp file with hash-based naming
        file_hash = hashlib.md5(url.encode()).hexdigest()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_hash}.pdf")
        
        # Stream the content to the file
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        
        temp_file.close()
        debug_print(f"Successfully downloaded PDF to: {temp_file.name}")
        return temp_file.name
    
    except Exception as e:
        logger.error(f"Failed to download PDF {url}: {e}")
        debug_print(f"ERROR downloading PDF: {str(e)}")
        return None

def get_metadata(doc) -> Dict[str, Any]:
    """Extract metadata from a PDF document."""
    debug_print("Extracting PDF metadata")
    try:
        metadata = doc.metadata
        clean_metadata = {}
        for key, value in metadata.items():
            if value:
                clean_metadata[key] = str(value)
        debug_print(f"Extracted metadata: {clean_metadata}")
        return clean_metadata
    except Exception as e:
        debug_print(f"ERROR extracting metadata: {str(e)}")
        return {}
        
def extract_enhanced_metadata_with_llm(doc, max_pages: int = 3) -> Dict[str, Any]:
    """
    Extract enhanced metadata from the first few pages of a PDF using LLM.
    This provides better title, authors, year, and generates a Harvard reference and summary.
    """
    debug_print(f"Extracting enhanced metadata using LLM from first {max_pages} pages")
    
    try:
        # Get basic metadata first (as fallback)
        basic_metadata = get_metadata(doc)
        
        # Extract text from first few pages
        page_count = min(max_pages, len(doc))
        first_pages_text = ""
        
        for i in range(page_count):
            page_text = doc[i].get_text()
            first_pages_text += f"[PAGE {i+1}]\n{page_text}\n[END PAGE {i+1}]\n"
        
        # Prepare prompt for LLM
        llm = LLM(model="openai:gpt-4o")
        
        system_prompt = """
        You are an academic metadata extraction assistant. Extract the following information from the first few pages of an academic paper:
        1. Title: The full title of the paper
        2. Authors: The complete list of authors
        3. Year: The publication year
        4. Summary: A brief 2-3 sentence summary of the paper's main focus
        
        Return ONLY a JSON object with these keys: title, authors (as array), year, summary. 
        If you cannot determine a field, use null for that field.
        """
        
        # Define output schema
        output_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "authors": {"type": "array", "items": {"type": "string"}},
                "year": {"type": ["string", "number", "null"]},
                "summary": {"type": "string"}
            }
        }
        
        # Call LLM for structured extraction
        result = llm.structured_output(first_pages_text, output_schema, system_prompt)
        debug_print(f"LLM extraction result: {result}")
        
        # Generate Harvard reference from the extracted metadata
        title = result.get('title') or basic_metadata.get('title', 'Unknown Document')
        authors = result.get('authors') or []
        year = str(result.get('year') or "Unknown")
        summary = result.get('summary') or ""
        
        # Format author string for Harvard reference
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} and {authors[1]}"
        elif len(authors) > 2:
            author_str = f"{authors[0]} et al."
        else:
            author_str = "Unknown"
        
        # Create Harvard reference
        harvard_ref = f"{author_str} ({year}). {title}."
        
        # Return enhanced metadata
        return {
            'title': title,
            'authors': authors,
            'year': year,
            'summary': summary,
            'harvard_reference': harvard_ref,
            'basic_metadata': basic_metadata,  # Keep the original metadata as fallback
            'total_pages': len(doc)
        }
        
    except Exception as e:
        logger.error(f"Error extracting enhanced metadata: {e}")
        debug_print(f"ERROR extracting enhanced metadata: {str(e)}")
        
        # Fall back to basic metadata
        basic_metadata = get_metadata(doc)
        
        return {
            'title': basic_metadata.get('title', 'Unknown Document'),
            'authors': basic_metadata.get('author', '').split(', ') if basic_metadata.get('author') else [],
            'year': 'Unknown',
            'summary': '',
            'harvard_reference': format_harvard_reference(basic_metadata),
            'basic_metadata': basic_metadata,
            'total_pages': len(doc)
        }

def format_harvard_reference(metadata: Dict[str, Any]) -> str:
    """Format a Harvard-style reference from metadata."""
    debug_print("Generating Harvard reference")
    try:
        # Extract author information
        authors = metadata.get('author', 'Unknown')
        if isinstance(authors, str):
            authors = authors.split(', ')
        
        # Format author string
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} and {authors[1]}"
        elif len(authors) > 2:
            author_str = f"{authors[0]} et al."
        else:
            author_str = "Unknown"
        
        # Extract year
        year = "Unknown"
        date_str = metadata.get('creationDate', '')
        if date_str:
            # Try to extract a 4-digit year
            year_match = re.search(r'20[0-9]{2}|19[0-9]{2}', date_str)
            if year_match:
                year = year_match.group(0)
        
        # Get title
        title = metadata.get('title', 'Untitled Document')
        
        # Format reference
        harvard_ref = f"{author_str} ({year}). {title}."
        debug_print(f"Generated Harvard reference: {harvard_ref}")
        return harvard_ref
    
    except Exception as e:
        logger.error(f"Error formatting Harvard reference: {e}")
        debug_print(f"ERROR generating Harvard reference: {str(e)}")
        return "Citation generation error"



def extract_information_from_text(text: str, search_terms:List[str], queries: List[str], extract_citations: bool = True) -> List[Dict[str, Any]]:
    """Extract information from text using LLM."""
    debug_print(f"Extracting information from text of length: {len(text)}")
    if not text or not queries:
        debug_print("No text or queries provided")
        return []
    
    # Initialize LLM
    llm = LLM(model='openai:gpt-4o-mini')
    
    # Create system prompt
    system_prompt = f"""

    ########################################\n\n
    You are an AI research assistant analyzing academic papers. Your Goal is to Extract information from research papers that DIRECTLY relates to any of these user queries below, : \n ### \n 

    Relevant search terms for context:\n ### 
     {",".join([f" {t}" for t in search_terms])}\n\n####\n\n
    
    # Users Queries Below, search the pages below to match what the user is looking for. The Users Queries Below: \n
    {"\n".join([f"- {q}" for q in queries])}
    
     \n #######
    
    Be very strict on what the user is asking for! The "Relevent search terms" are the type of books/subject to help understand the topic better, but you MUST ONLY extract information that DIRECTLY answers the users specific queries above.
     
    Don't extract ANY content that might be only remotely relevant. Be STRICT! Make sure it is directly relevant to the user's specific queries.

    Important Instructions:
    1. Extract the exact text from the page that answers or related closely to the users queries above and include sufficient text surrounding the text to maintain context if needed, Keep in all citation found in the text.
    2. Extract as much relevant text as the pages provide that answer what the user is looking for - Dont be afraid to return nothing if no information is relevant (REMEBER BE STRICT). 
    3. For each extraction, specify EXACTLY which user query it relates to (use the exact query wording) ("matches_topic")
    4. The provided text from the academic paper contains multiple pages marked with [PAGE N]
    5. ALWAYS include the correct page number for each extracted piece of information
    6. Explain in detail what the text you extracted is talking about in the boarder context of the full academic paper. And explain what the user is asking for and why the text you extracted relates to the users query (matches_topic) and why is answers what they are looking ("justification"). If your explanation is not good enough and does not directly answers the users question, do not include it, in the final output, provide an 


    Important if nothing in the papers directly answer the queries for the user below DONT INCLUDE IT, YOU MUST JUSTIFY WHY YOU THE TEXT ANSWERS THE USER QUERIES: ##  USER QUESTIONS ({"\n".join([f"- {q}" for q in queries])}) ## \n Important if nothing in the papers directly answer the queries for the user below DONT INCLUDE IT, YOU MUST JUSTIFY WHY YOU THE TEXT ANSWERS THE USER QUERIES:
    """
    
    if extract_citations:
        system_prompt += """
        Additional Instructions for Citations:
        1. Include any citation references (like "[1]" or "[Smith et al., 2020]") found in the extracted text, make sure to keep it in the text
        2. When available, extract the full reference details for each citation
        3. Format citations as a separate list to maintain clarity
        """
    
    page_text = f"""
CONTENT FROM ACADEMIC PAPER:
{text}

TASK: Extract passages that help answer the user's questions or explain these topics. Be generous - if content seems related or educational, include it.

Remember: Academic papers are full of useful information even if they don't provide textbook definitions. Extract anything that would help someone learn about these topics.
"""
    
    
    # Create output schema - SIMPLIFIED for better extraction
    output_schema = {
        "type": "array",
        "items": {
            "type": "object", 
            "properties": {
                "content": {"type": "string", "description": "The extracted text content from the paper"},
                "page_number": {"type": "integer", "description": "Page number (1-based indexing)"},
                "matches_topic": {"type": "string", "description": "Which user question this relates to"},
                "justification": {"type": "string", "description": "Why this content is useful"},
                "inline_citations": {"type": "array", "items": {"type": "string"}, "description": "Any citation references like [1] or [Smith et al., 2020]"},
                "reference_list": {"type": "object", "additionalProperties": {"type": "string"}, "description": "Citation mappings"}
            },
            "required": ["content", "page_number", "matches_topic", "justification"]
        }
    }
    
    try:
        # Extract information
        debug_print("Calling LLM for information extraction")
        result = llm.structured_output(page_text, output_schema, system_prompt)
        
        # Enhanced debugging
        debug_print(f"LLM raw response type: {type(result)}")
        if isinstance(result, dict):
            debug_print(f"Response keys: {result.keys()}")
        
        # Handle the response - account for various formats the LLM might return
        extracted_items = []
        
        if isinstance(result, list):
            # Direct array response
            extracted_items = result
        elif isinstance(result, dict):
            # Check for different possible keys - handle {"type":"array","items":[...]}
            if "items" in result:
                extracted_items = result["items"]
            else:
                # Try to find any array in the response
                for key, value in result.items():
                    if isinstance(value, list):
                        extracted_items = value
                        break
        
        debug_print(f"Extracted {len(extracted_items)} items from text")
        if len(extracted_items) == 0:
            debug_print("WARNING: LLM returned empty list")
        
        return extracted_items
    
    except Exception as e:
        logger.error(f"Error extracting information: {e}")
        debug_print(f"ERROR extracting information: {str(e)}")
        return []

        
def determine_note_type(content: str, topic: str) -> str:
    """Determine the type of note based on content and topic."""
    content_lower = content.lower()
    topic_lower = topic.lower() if topic else ""
    
    # Check for statistics
    if any(term in content_lower for term in [
        "%", "percent", "survey", "study found", "data shows",
        "according to", "results indicate", "analysis revealed"
    ]):
        return "statistic"
    
    # Check for methodology
    if any(term in content_lower or term in topic_lower for term in [
        "method", "approach", "technique", "procedure", "process",
        "framework", "implementation", "algorithm", "steps",
        "experiment", "model", "design", "protocol"
    ]):
        return "methodology"
    
    # Default to quote
    return "quote"

def create_chunks(pages: List[int]) -> List[tuple]:
    """Group pages into logical chunks for processing."""
    debug_print(f"Creating chunks from pages: {pages}")
    if not pages:
        return []
    
    pages = sorted(pages)
    chunks = []
    current_chunk = [pages[0]]
    
    for i in range(1, len(pages)):
        # If consecutive or just one page gap
        if pages[i] <= pages[i - 1] + 2:
            current_chunk.append(pages[i])
        else:
            if current_chunk:  # ✅ ensure non-empty
                chunks.append((min(current_chunk), max(current_chunk)))
            current_chunk = [pages[i]]
        
        # If chunk has 3 pages, close it
        if len(current_chunk) >= 3:
            chunks.append((min(current_chunk), max(current_chunk)))
            current_chunk = []
    
    # Add last chunk if it exists
    if current_chunk:  # ✅ ensure non-empty
        chunks.append((min(current_chunk), max(current_chunk)))
    
    debug_print(f"Created {len(chunks)} chunks: {chunks}")
    return chunks


def format_note(item: Dict[str, Any]) -> Dict[str, Any]:
    """Format an extracted item as a note."""
    content = item.get('content', '')
    topic = item.get('matches_topic', '')

   
    result = {
        'content': content,
        'page_number': item.get('page_number', 1),
        'type': determine_note_type(content, topic),
        'search_criteria': topic,
        'matches_topic': topic,
        'justification': item.get('justification', ''),
        'inline_citations': item.get('inline_citations', []),
        'reference_list': item.get('reference_list', {})
    }
    
    return result
def process_pdf(pdf_url: str, search_terms: List[str], query_embedding: List[float], original_queries: List[str], explanation: str = "", extract_citations: bool = True) -> Dict[str, Any]:
    """
    Process a PDF URL and extract relevant information.
    
    Implements the two-path strategy based on document size:
    - Simple Path for documents <= 8 pages: Process all at once
    - Advanced Path for documents > 8 pages: Use embeddings to find relevant pages
    """
    debug_print(f"Processing PDF: {pdf_url}")
    
    # Validate URL
    try:
        URLValidator()(pdf_url)
    except ValidationError:
        logger.error(f"Invalid URL provided: {pdf_url}")
        debug_print(f"ERROR: Invalid URL: {pdf_url}")
        return {
            'status': 'error',
            'error_message': 'Invalid URL',
            'title': 'URL Error',
            'authors': [],
            'harvard_reference': '',
            'notes': []
        }
    
    # Set processing timeout
    max_processing_time = settings.MAX_PROCESSING_TIME if hasattr(settings, 'MAX_PROCESSING_TIME') else 300  # 5 minutes
    start_time = time.time()
    
    try:
        # Normalize URL and download PDF
        pdf_url = normalize_url(pdf_url)
        pdf_path = download_pdf(pdf_url)
        
        if not pdf_path:
            debug_print("Failed to download PDF")
            return {
                'status': 'error',
                'error_message': 'Failed to download PDF',
                'title': 'Download Error',
                'authors': [],
                'harvard_reference': '',
                'notes': []
            }
        
        # Open PDF and extract metadata
        debug_print(f"Opening PDF: {pdf_path}")
        
        # Verify it's a valid PDF
        try:
            doc = fitz.open(pdf_path)
            # Check if it's a valid PDF
            if not doc.is_pdf:
                debug_print(f"ERROR: Not a valid PDF file: {pdf_path}")
                try:
                    os.remove(pdf_path)
                except:
                    pass
                return {
                    'status': 'error',
                    'error_message': 'Not a valid PDF file',
                    'title': 'Invalid PDF',
                    'authors': [],
                    'harvard_reference': '',
                    'notes': []
                }
        except Exception as e:
            debug_print(f"ERROR: Could not open as PDF: {str(e)}")
            try:
                os.remove(pdf_path)
            except:
                pass
            return {
                'status': 'error',
                'error_message': f'Could not open as PDF: {str(e)}',
                'title': 'PDF Error',
                'authors': [],
                'harvard_reference': '',
                'notes': []
            }
        
        page_count = len(doc)
        debug_print(f"PDF has {page_count} pages")
        
        # Extract enhanced metadata using LLM
        enhanced_metadata = extract_enhanced_metadata_with_llm(doc)
        debug_print(f"Enhanced metadata extracted: {enhanced_metadata['title']}")
        
        # Process the document based on its size
        notes = []
        small_doc_threshold = settings.SMALL_DOC_PAGE_THRESHOLD if hasattr(settings, 'SMALL_DOC_PAGE_THRESHOLD') else 8
        
        if page_count <= small_doc_threshold:
            # SIMPLE PATH for small documents
            debug_print(f"Using Simple Path for document with {page_count} pages")
            
            # Extract text from all pages
            all_text = ""
            for i in range(page_count):
                # Check for timeout
                if time.time() - start_time > max_processing_time:
                    debug_print(f"ERROR: Processing timeout reached ({max_processing_time} seconds)")
                    doc.close()
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
                    return {
                        'status': 'error',
                        'error_message': f'Processing timeout after {max_processing_time} seconds',
                        'title': enhanced_metadata['title'],
                        'authors': enhanced_metadata['authors'],
                        'year': enhanced_metadata['year'],
                        'summary': enhanced_metadata['summary'],
                        'harvard_reference': enhanced_metadata['harvard_reference'],
                        'total_pages': enhanced_metadata['total_pages'],
                        'notes': []
                    }
                
                page_text = doc[i].get_text()
                all_text += f"[PAGE {i+1}]\n{page_text}\n[END PAGE {i+1}]\n"
            
            # Extract information using LLM
            extracted_items = extract_information_from_text(all_text, search_terms, original_queries, extract_citations)
            notes = [format_note(item) for item in extracted_items]
            debug_print(f"Extracted {len(notes)} notes using Simple Path")
            
        else:
            # ADVANCED PATH for larger documents using Google embeddings batch processing
            debug_print(f"Using Advanced Path with Google embeddings for document with {page_count} pages")
            
            # Calculate relevance threshold - temporarily lowered for testing
            relevance_threshold = settings.RELEVANCE_THRESHOLD if hasattr(settings, 'RELEVANCE_THRESHOLD') else 0.15
            debug_print(f"Using relevance threshold: {relevance_threshold}")
            
            # Prepare all pages for batch embedding processing
            relevant_pages = []
            
            # Optimal batch size for memory efficiency - process 20 pages at a time
            # This balances API efficiency with memory usage
            batch_size = 20
            debug_print(f"Processing {page_count} pages in batches of {batch_size} using Google embeddings")
            
            for batch_start in range(0, page_count, batch_size):
                batch_end = min(batch_start + batch_size, page_count)
                debug_print(f"Processing page batch {batch_start+1}-{batch_end}/{page_count} with Google embeddings")
                
                # Check for timeout
                if time.time() - start_time > max_processing_time:
                    debug_print(f"ERROR: Processing timeout reached ({max_processing_time} seconds)")
                    doc.close()
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
                    return {
                        'status': 'error',
                        'error_message': f'Processing timeout after {max_processing_time} seconds',
                        'title': enhanced_metadata['title'],
                        'authors': enhanced_metadata['authors'],
                        'year': enhanced_metadata['year'],
                        'summary': enhanced_metadata['summary'],
                        'harvard_reference': enhanced_metadata['harvard_reference'],
                        'total_pages': enhanced_metadata['total_pages'],
                        'notes': []
                    }
                
                # Prepare documents for batch processing
                batch_documents = []
                page_indices = []
                
                for i in range(batch_start, batch_end):
                    page_text = doc[i].get_text()
                    if page_text.strip():  # Only process non-empty pages
                        batch_documents.append({
                            'content': page_text.strip(),
                            'id': f"page_{i+1}"
                        })
                        page_indices.append(i)
                    else:
                        debug_print(f"Page {i+1} is empty, skipping")
                
                if not batch_documents:
                    debug_print(f"No valid pages in batch {batch_start+1}-{batch_end}")
                    continue
                
                # Prepare query from original queries and search terms
                query_parts = original_queries + search_terms
                user_query = " ".join(query_parts)
                
                # Use Google embeddings for batch processing (much faster than individual calls)
                debug_print(f"Generating Google embeddings for {len(batch_documents)} pages in batch")
                doc_embeddings, query_embedding = get_google_embeddings_batch(batch_documents, user_query)
                
                if doc_embeddings is None or query_embedding is None:
                    debug_print("Google embeddings failed, falling back to OpenAI for this batch")
                    # Fallback to original method for this batch
                    for i, doc_idx in enumerate(page_indices):
                        page_text = batch_documents[i]['content']
                        page_embedding = get_embedding(page_text)
                        similarity = calculate_similarity(page_embedding, query_embedding)
                        debug_print(f"Page {doc_idx+1} has similarity score: {similarity:.4f} (OpenAI fallback)")
                        
                        if similarity > relevance_threshold:
                            debug_print(f"Page {doc_idx+1} is relevant (score: {similarity:.4f})")
                            relevant_pages.append(doc_idx)
                else:
                    # Calculate all similarities at once (vectorized - very fast)
                    debug_print(f"Calculating cosine similarities for {len(doc_embeddings)} pages")
                    similarities = calculate_cosine_similarities(query_embedding, doc_embeddings)
                    
                    # Process similarity results
                    for i, similarity in enumerate(similarities):
                        doc_idx = page_indices[i]
                        debug_print(f"Page {doc_idx+1} has similarity score: {similarity:.4f} (Google embeddings)")
                        
                        if similarity > relevance_threshold:
                            debug_print(f"Page {doc_idx+1} is relevant (score: {similarity:.4f})")
                            relevant_pages.append(doc_idx)
                
                # Memory management - clear large variables immediately
                batch_documents = None
                doc_embeddings = None
                query_embedding = None
                similarities = None
                
                debug_print(f"Completed batch {batch_start+1}-{batch_end}, found {len([p for p in relevant_pages if batch_start <= p < batch_end])} relevant pages")
            
            debug_print(f"Found {len(relevant_pages)} relevant pages total: {relevant_pages}")
            
            if not relevant_pages:
                debug_print("No relevant pages found")
                doc.close()
                try:
                    os.remove(pdf_path)
                except:
                    pass
                
                return {
                    'status': 'no_relevant_info',
                    'title': enhanced_metadata['title'],
                    'authors': enhanced_metadata['authors'],
                    'year': enhanced_metadata['year'],
                    'summary': enhanced_metadata['summary'],
                    'harvard_reference': enhanced_metadata['harvard_reference'],
                    'total_pages': enhanced_metadata['total_pages'],
                    'notes': []
                }
            
            # Group relevant pages into logical chunks for content extraction
            chunks = create_chunks(relevant_pages)
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                # Check for timeout
                if time.time() - start_time > max_processing_time:
                    debug_print(f"ERROR: Processing timeout reached ({max_processing_time} seconds)")
                    doc.close()
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
                    
                    # Return partial results if we have any
                    if notes:
                        return {
                            'status': 'partial_success',
                            'error_message': f'Processing timeout after {max_processing_time} seconds - partial results returned',
                            'title': enhanced_metadata['title'],
                            'authors': enhanced_metadata['authors'],
                            'year': enhanced_metadata['year'],
                            'summary': enhanced_metadata['summary'],
                            'harvard_reference': enhanced_metadata['harvard_reference'],
                            'total_pages': enhanced_metadata['total_pages'],
                            'notes': notes
                        }
                    else:
                        return {
                            'status': 'error',
                            'error_message': f'Processing timeout after {max_processing_time} seconds',
                            'title': enhanced_metadata['title'],
                            'authors': enhanced_metadata['authors'],
                            'year': enhanced_metadata['year'],
                            'summary': enhanced_metadata['summary'],
                            'harvard_reference': enhanced_metadata['harvard_reference'],
                            'total_pages': enhanced_metadata['total_pages'],
                            'notes': []
                        }
                
                debug_print(f"Processing chunk {i+1}/{len(chunks)}: pages {chunk[0]+1}-{chunk[1]+1}")
                
                # Extract text from pages in this chunk
                chunk_text = ""
                for page_num in range(chunk[0], chunk[1] + 1):
                    page_text = doc[page_num].get_text()
                    chunk_text += f"[PAGE {page_num+1}]\n{page_text}\n[END PAGE {page_num+1}]\n"
                
                # Extract information from this chunk
                extracted_items = extract_information_from_text(chunk_text, search_terms, original_queries, extract_citations)
                chunk_notes = [format_note(item) for item in extracted_items]
                notes.extend(chunk_notes)
                debug_print(f"Extracted {len(chunk_notes)} notes from chunk {i+1}")
                
                # Memory management - explicitly clear large variables
                chunk_text = None
                extracted_items = None
        
        # Close and clean up
        doc.close()
        try:
            os.remove(pdf_path)
            debug_print(f"Removed temporary file: {pdf_path}")
        except Exception as e:
            debug_print(f"Failed to remove temporary file: {str(e)}")
        
        # Log performance metrics
        processing_time = time.time() - start_time
        debug_print(f"PDF processing completed in {processing_time:.2f} seconds. PDF: {pdf_url}, Pages: {page_count}, Notes: {len(notes)}")

        # Apply final validation if we have notes and an explanation
        if notes and explanation:
            # Import here to avoid circular imports
            from .embedding_service import validate_note_relevance
            
            debug_print(f"Performing final note validation with explanation: '{explanation[:300]} \n \n...'")
            debug_print(f"Number of notes to validate: '{len(notes)} \n \n...'")
            validated_notes, filtered_notes = validate_note_relevance(
                notes, 
                original_queries, 
                explanation, 
                threshold=0.05
            )
            
            # Log statistics
            debug_print(f"Note validation: {len(validated_notes)}/{len(notes)} passed final relevance check")
            
            # Add statistics to result metadata
            filtered_count = len(notes) - len(validated_notes)
            
            # Update notes with only the validated ones
            notes = validated_notes

        
        # Return the results
        result = {
            'status': 'success',
            'title': enhanced_metadata['title'],
            'authors': enhanced_metadata['authors'],
            'year': enhanced_metadata['year'],
            'summary': enhanced_metadata['summary'],
            'harvard_reference': enhanced_metadata['harvard_reference'],
            'total_pages': enhanced_metadata['total_pages'],
            'notes': notes,
            'processing_time': processing_time
        }
        
        debug_print(f"PDF processing complete: {result['status']}, {len(notes)} notes extracted in {processing_time:.2f} seconds")
        return result
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_url}: {e}", exc_info=True)
        debug_print(f"ERROR processing PDF: {str(e)}")
        
        # Cleanup if PDF path exists
        if locals().get('pdf_path') and os.path.exists(pdf_path):
            try:
                if locals().get('doc'):
                    doc.close()
                os.remove(pdf_path)
            except:
                pass
        
        # Log performance failure
        processing_time = time.time() - start_time
        logger.error(f"PDF processing failed after {processing_time:.2f} seconds. PDF: {pdf_url}, Error: {str(e)}")
        
        return {
            'status': 'error',
            'error_message': str(e),
            'title': 'Processing Error',
            'authors': [],
            'harvard_reference': '',
            'notes': [],
            'processing_time': processing_time
        }