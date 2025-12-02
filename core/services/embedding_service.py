"""
Embedding service for generating embeddings using Google Gemini and OpenAI APIs.
"""

import logging
import os
import numpy as np
from openai import OpenAI
from django.conf import settings
from typing import List, Dict, Any
from ..utils.debug import debug_print


# Google Gemini embeddings imports
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from sklearn.metrics.pairwise import cosine_similarity
    GOOGLE_EMBEDDINGS_AVAILABLE = True
except ImportError:
    GOOGLE_EMBEDDINGS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


def get_embedding(text: str) -> List[float]:
    """Generate an embedding for the given text."""
    debug_print(f"Generating embedding for text (length: {len(text)})")
    if not text or not text.strip():
        # Return empty embedding of appropriate dimension
        debug_print("Empty text provided, returning zero embedding")
        return [0.0] * 1536  # Default dimension for OpenAI embeddings
    try:
        # Initialize OpenAI client
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        
        try:
            # Simple initialization without proxy settings
            client = OpenAI(api_key=api_key)
        except TypeError as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            debug_print(f"ERROR initializing OpenAI client: {str(e)}")
            # Fallback to minimal initialization
            client = OpenAI(api_key=api_key)
        
        # Call the API
        debug_print("Calling OpenAI embeddings API")
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        
        # Return the embedding
        debug_print("Successfully generated embedding")
        return response.data[0].embedding
    
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        debug_print(f"ERROR generating embedding: {str(e)}")
        # Return zero vector as fallback
        return [0.0] * 1536

def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    debug_print(f"Generating batch embeddings for {len(texts)} texts")
    if not texts:
        debug_print("Empty texts list provided, returning empty list")
        return []
    
    # Filter out empty strings
    valid_texts = [text for text in texts if text and text.strip()]
    debug_print(f"Found {len(valid_texts)} valid texts for embedding")
    
    if not valid_texts:
        debug_print("No valid texts after filtering, returning zero embeddings")
        return [[0.0] * 1536] * len(texts)
    
    try:
        # Initialize OpenAI client
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        
        try:
            # Simple initialization without proxy settings
            client = OpenAI(api_key=api_key)
        except TypeError as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            debug_print(f"ERROR initializing OpenAI client: {str(e)}")
            # Fallback to minimal initialization
            client = OpenAI(api_key=api_key)
        
        # Call the API
        debug_print("Calling OpenAI batch embeddings API")
        response = client.embeddings.create(
            input=valid_texts,
            model="text-embedding-3-small"
        )
        
        # Map embeddings back to original texts
        result = []
        valid_idx = 0
        
        for text in texts:
            if text and text.strip():
                result.append(response.data[valid_idx].embedding)
                valid_idx += 1
            else:
                result.append([0.0] * 1536)
        
        debug_print("Successfully generated batch embeddings")
        return result
    
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        debug_print(f"ERROR generating batch embeddings: {str(e)}")
        # Return zero vectors as fallback
        return [[0.0] * 1536] * len(texts)

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    debug_print("Calculating similarity between embeddings")
    if not embedding1 or not embedding2:
        debug_print("Empty embeddings provided, returning 0.0 similarity")
        return 0.0
    
    try:
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            debug_print("Zero norm detected, returning 0.0 similarity")
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        debug_print(f"Calculated similarity: {similarity:.4f}")
        return similarity
    
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        debug_print(f"ERROR calculating similarity: {str(e)}")
        return 0.0
    
def validate_note_relevance(notes, expanded_questions, explanation, threshold=0.05):
    """
    Perform final validation on notes to ensure they meet relevance threshold.
    
    Args:
        notes: List of extracted notes
        expanded_questions: List of search questions
        explanation: Concise explanation of user's research intent
        threshold: Minimum similarity score (default xxx)
        
    Returns:
        validated_notes: List of notes that passed validation
        filtered_notes: List of notes that didn't meet threshold
    """
    debug_print(f"Performing final relevance validation on {len(notes)} notes with threshold {threshold}")
    
    # Create the user intent text by combining expanded questions and explanation
    user_intent_text = " ".join(expanded_questions) + " / " + explanation
    debug_print(f"Generated user intent text: '{user_intent_text[:500]}...'")
    
    # Get embedding for user intent
    intent_embedding = get_embedding(user_intent_text)

   
    validated_notes = []
    filtered_notes = []
    
    for note in notes:
        # Get embedding for note content
        note_embedding = get_embedding(note['content'])
        
        # Calculate similarity
        similarity = calculate_similarity(intent_embedding, note_embedding)
        debug_print(f"Note similarity: {similarity:.4f} for note: '{note['content'][:5000]}...'")
       
       
        # Apply threshold
        if similarity >= threshold:
            note['relevance_score'] = float(similarity)
            validated_notes.append(note)
            debug_print(f"Note PASSED with score {similarity:.4f}")
        else:
            note['relevance_score'] = float(similarity)
            filtered_notes.append(note)
            debug_print(f"Note FILTERED with score {similarity:.4f}")
    
    debug_print(f"Validation complete: {len(validated_notes)} notes passed, {len(filtered_notes)} filtered")
    return validated_notes, filtered_notes

# Google Gemini Embeddings Functions
def setup_google_api_key():
    """
    Setup Google API key from environment variables or Django settings.
    Priority: settings.GOOGLE_API_KEY > GOOGLE_API_KEY env var
    """
    api_key = None
    
    # Try Django settings first
    try:
        api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        if api_key:
            debug_print("Found Google API key in Django settings")
    except Exception as e:
        debug_print(f"Could not access Django settings: {e}")
    
    # Try environment variable if not in settings
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key:
            debug_print("Found Google API key in environment variables")
    
    # Validation
    if not api_key:
        error_msg = "Google API key not found! Please set GOOGLE_API_KEY in your .env file"
        logger.error(error_msg)
        debug_print(f"ERROR: {error_msg}")
        raise ValueError(error_msg)
    
    # Set in environment for LangChain Google GenAI
    os.environ["GOOGLE_API_KEY"] = api_key
    debug_print("Google API key configured successfully")
    return api_key

def get_google_embeddings_batch(documents: List[Dict[str, str]], user_query: str) -> tuple:
    """
    Generate embeddings using Google Gemini for batch document and query processing.
    
    Args:
        documents: List of dicts with 'content' and 'id' keys
        user_query: Concatenated user queries string
        
    Returns:
        Tuple of (doc_embeddings, query_embedding) or (None, None) on error
    """
    debug_print(f"Generating Google embeddings for {len(documents)} documents and 1 query")
    
    if not GOOGLE_EMBEDDINGS_AVAILABLE:
        debug_print("Google embeddings not available - missing dependencies")
        return None, None
    
    try:
        # Setup and validate API key
        api_key = setup_google_api_key()
        if not api_key:
            debug_print("Failed to setup Google API key")
            return None, None
        
        # Initialize embedders with task-specific models
        doc_embedder = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001", 
            task_type="RETRIEVAL_DOCUMENT"
        )
        query_embedder = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001", 
            task_type="RETRIEVAL_QUERY"
        )
        
        
        # Extract document texts
        doc_texts = [doc["content"] for doc in documents]
        
        # Batch embed all documents
        debug_print("Generating document embeddings with Google Gemini")
        doc_embeddings = doc_embedder.embed_documents(doc_texts)
        
        # Embed user query
        debug_print("Generating query embedding with Google Gemini")
        query_embedding = query_embedder.embed_query(user_query)
        
        debug_print("Successfully generated Google Gemini embeddings")
        return doc_embeddings, query_embedding
        
    except Exception as e:
        logger.error(f"Error generating Google embeddings: {e}")
        debug_print(f"ERROR generating Google embeddings: {str(e)}")
        return None, None

def calculate_cosine_similarities(query_embedding: List[float], doc_embeddings: List[List[float]]) -> List[float]:
    """
    Calculate cosine similarities between query and documents using sklearn.
    
    Args:
        query_embedding: Single query embedding vector
        doc_embeddings: List of document embedding vectors
        
    Returns:
        List of similarity scores (0.0 to 1.0)
    """
    debug_print(f"Calculating cosine similarities for {len(doc_embeddings)} documents")
    
    try:
        # Use sklearn for efficient cosine similarity computation
        similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
        debug_print(f"Calculated {len(similarities)} similarity scores")
        return similarities.tolist()
        
    except Exception as e:
        logger.error(f"Error calculating cosine similarities: {e}")
        debug_print(f"ERROR calculating similarities: {str(e)}")
        return [0.0] * len(doc_embeddings)

def filter_papers_by_embedding_similarity(
    documents: List[Dict[str, str]], 
    user_query: str, 
    threshold: float = 0.7
) -> Dict[str, bool]:
    """
    Filter papers using Google Gemini embeddings and cosine similarity.
    
    Args:
        documents: List of dicts with 'content' (title+abstract) and 'id' (URL) keys
        user_query: Concatenated user queries string
        threshold: Minimum cosine similarity threshold (default: 0.7)
        
    Returns:
        Dictionary mapping document IDs (URLs) to relevance boolean
    """
    debug_print(f"Filtering {len(documents)} papers using Google embeddings with threshold {threshold}")
    
    if not documents:
        debug_print("No documents to filter")
        return {}
    
    try:
        # Generate embeddings
        doc_embeddings, query_embedding = get_google_embeddings_batch(documents, user_query)
        
        if doc_embeddings is None or query_embedding is None:
            debug_print("Failed to generate embeddings - falling back to accepting all papers")
            # Return all as relevant if embeddings fail
            return {doc["id"]: True for doc in documents}
        
        # Calculate similarities
        similarities = calculate_cosine_similarities(query_embedding, doc_embeddings)
        
        # Apply threshold and create relevance map
        relevance_map = {}
        relevant_count = 0
        
        for doc, similarity in zip(documents, similarities):
            is_relevant = similarity >= threshold
            relevance_map[doc["id"]] = is_relevant
            
            if is_relevant:
                relevant_count += 1
            
            debug_print(f"Paper {doc['id']}: similarity {similarity:.3f} -> {'RELEVANT' if is_relevant else 'FILTERED'}")
        
        debug_print(f"Filtering complete: {relevant_count}/{len(documents)} papers above {threshold} threshold")
        return relevance_map
        
    except Exception as e:
        logger.error(f"Error in embedding-based filtering: {e}")
        debug_print(f"ERROR in embedding filtering: {str(e)}")
        # Return all as relevant on error to avoid breaking the pipeline
        return {doc["id"]: True for doc in documents}

def test_google_embeddings_setup():
    """
    Test function to verify Google embeddings are properly configured.
    
    Returns:
        Dictionary with test results
    """
    debug_print("Testing Google embeddings setup...")
    
    test_result = {
        'dependencies_available': GOOGLE_EMBEDDINGS_AVAILABLE,
        'api_key_configured': False,
        'embedding_test': False,
        'error_message': None
    }
    
    try:
        # Check dependencies
        if not GOOGLE_EMBEDDINGS_AVAILABLE:
            test_result['error_message'] = "Missing dependencies: langchain-google-genai or scikit-learn"
            return test_result
        
        # Check API key
        try:
            api_key = setup_google_api_key()
            test_result['api_key_configured'] = bool(api_key)
        except Exception as key_error:
            test_result['error_message'] = f"API key setup failed: {str(key_error)}"
            return test_result
        
        # Test basic embedding
        try:
            test_documents = [{"content": "Test document content", "id": "test"}]
            test_query = "Test query"
            
            doc_embeddings, query_embedding = get_google_embeddings_batch(test_documents, test_query)
            test_result['embedding_test'] = doc_embeddings is not None and query_embedding is not None
            
            if test_result['embedding_test']:
                debug_print("Google embeddings test successful!")
            else:
                test_result['error_message'] = "Embedding generation failed"
                
        except Exception as embed_error:
            test_result['error_message'] = f"Embedding test failed: {str(embed_error)}"
    
    except Exception as e:
        test_result['error_message'] = f"Test failed: {str(e)}"
    
    debug_print(f"Google embeddings test result: {test_result}")
    return test_result
