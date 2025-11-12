"""
Embedding service for generating embeddings using OpenAI's API.
"""

import logging
import os
import numpy as np
from openai import OpenAI
from django.conf import settings
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Enable debug printing
DEBUG_PRINT = False

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[EMBEDDING] {message}")

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
    print(f"Generated user intent text: '{user_intent_text[:500]}...'")
    
    # Get embedding for user intent
    intent_embedding = get_embedding(user_intent_text)

   
    validated_notes = []
    filtered_notes = []
    
    for note in notes:
        # Get embedding for note content
        note_embedding = get_embedding(note['content'])
        
        # Calculate similarity
        similarity = calculate_similarity(intent_embedding, note_embedding)
        print(f"Note similarity: {similarity:.4f} for note: '{note['content'][:5000]}...'")
       
       
        # Apply threshold
        if similarity >= threshold:
            note['relevance_score'] = float(similarity)
            validated_notes.append(note)
            print(f"Note PASSED with score {similarity:.4f}")
        else:
            note['relevance_score'] = float(similarity)
            filtered_notes.append(note)
            print(f"Note FILTERED with score {similarity:.4f}")
    
    print(f"Validation complete: {len(validated_notes)} notes passed, {len(filtered_notes)} filtered")
    return validated_notes, filtered_notes
