"""
LLM service for interacting with AI models using Pydantic-AI.
"""

import logging
import os
import json
import asyncio
import time
from typing import List, Dict, Any, Optional
from pydantic_ai import Agent
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

# Enable debug printing
DEBUG_PRINT = True

def debug_print(message):
    """Print debug information if DEBUG_PRINT is enabled."""
    if DEBUG_PRINT:
        print(f"[LLM] {message}")

class LLM:
    """Class for interacting with LLMs using Pydantic-AI."""
    
    def __init__(self, model: str = None, max_retries: int = 3):
        """Initialize the LLM class."""
        self.model = model or os.environ.get("DEFAULT_MODEL", 'openai:gpt-4o-mini')
        self.max_retries = max_retries
        
        # Create the Pydantic-AI agent
        debug_print(f"Initializing Pydantic-AI agent with model: {self.model}")
        self.agent = Agent(self.model)
    
    async def call(self, prompt: str, system_prompt: str = None, attempt: int = 0) -> str:
        """Call the LLM with the given prompt."""
        debug_print(f"Async calling LLM, attempt: {attempt+1}/{self.max_retries+1}")
        try:
            # Prepare the prompt with system prompt if provided
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
                debug_print("Added system prompt to message")
            else:
                full_prompt = prompt
            
            debug_print(f"Calling Pydantic-AI agent with prompt (length: {len(full_prompt)})")
            
            # Call the agent
            result = await self.agent.run(full_prompt)
            debug_print("Successfully received response from Pydantic-AI agent")
            
            # Access the output attribute
            output = result.output
            
            # Strip markdown code blocks if present
            if isinstance(output, str) and output.startswith("```") and "```" in output:
                # Extract content between code blocks
                content_start = output.find("\n") + 1
                content_end = output.rfind("```")
                if content_start > 0 and content_end > content_start:
                    output = output[content_start:content_end].strip()
                    debug_print("Stripped markdown code block from response")
            
            return output
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            debug_print(f"ERROR calling LLM: {str(e)}")
            
            if attempt < self.max_retries:
                # Retry with exponential backoff
                retry_delay = 2 ** attempt
                debug_print(f"Retrying in {retry_delay} seconds (attempt {attempt+1}/{self.max_retries})")
                await asyncio.sleep(retry_delay)
                return await self.call(prompt, system_prompt, attempt + 1)
            else:
                # Return error message after max retries
                debug_print(f"Failed after {self.max_retries} attempts")
                return f"Error after {self.max_retries} attempts: {str(e)}"
    
    def call_sync(self, prompt: str, system_prompt: str = None) -> str:
        """Synchronous version of call for non-async contexts."""
        debug_print("Sync calling LLM")
        try:
            # Run the async call in a synchronous context
            return asyncio.run(self.call(prompt, system_prompt))
        
        except Exception as e:
            logger.error(f"Error in synchronous LLM call: {e}")
            debug_print(f"ERROR in synchronous LLM call: {str(e)}")
            return f"Error: {str(e)}"
    
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        """Simple completion method for text generation.
        This is a wrapper around call_sync for simpler interface."""
        debug_print("Starting complete method")
        return self.call_sync(prompt, system_prompt)
    
    def structured_output(self, prompt: str, output_schema: dict, system_prompt: str = None) -> Dict[str, Any]:
        """Get structured output from the LLM."""
        debug_print("Calling LLM for structured output")
        try:
            # Create a system prompt with schema instructions
            schema_instructions = f"Your response must be a valid JSON object following this schema: {json.dumps(output_schema)}"
            debug_print(f"Added schema instructions to system prompt")
            
            if system_prompt:
                full_system_prompt = f"{system_prompt}\n\n{schema_instructions}"
            else:
                full_system_prompt = schema_instructions
            
            # Create a combined prompt
            full_prompt = f"{full_system_prompt}\n\n{prompt}"
            debug_print(f"Prepared prompt with schema instructions (length: {len(full_prompt)})")
            
            # Add retry logic for connection issues
            max_retries = 3
            retry_delay_base = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    # Call the agent synchronously to get JSON response
                    result = asyncio.run(self.agent.run(full_prompt))
                    debug_print(f"Successfully received response from Pydantic-AI agent")
                    
                    # Extract the content from the output attribute
                    output = result.output
                    debug_print(f"Raw output: {output[:100]}...")  # Log first 100 chars
                    
                    # Check if response is wrapped in markdown code blocks
                    if isinstance(output, str) and output.startswith("```") and "```" in output:
                        # Extract content between code blocks
                        content_start = output.find("\n") + 1
                        content_end = output.rfind("```")
                        if content_start > 0 and content_end > content_start:
                            output = output[content_start:content_end].strip()
                            debug_print(f"Stripped markdown code block, content: {output[:100]}...")
                    
                    try:
                        # Try to parse as JSON if it's a string
                        if isinstance(output, str):
                            parsed_json = json.loads(output)
                            debug_print(f"Successfully parsed JSON response")
                            return parsed_json
                        elif isinstance(output, dict):
                            # If it's already a dict, return it directly
                            return output
                        else:
                            debug_print(f"Unexpected response type: {type(output)}")
                            return {"error": "Unexpected response type", "raw_content": str(output)}
                    except json.JSONDecodeError as json_err:
                        debug_print(f"ERROR parsing JSON response: {str(json_err)}")
                        logger.error(f"Error parsing JSON response: {json_err}")
                        return {"error": f"Failed to parse JSON: {str(json_err)}", "raw_content": output}
                
                except Exception as connection_err:
                    # Handle connection errors with retries
                    if "Connection" in str(connection_err) and attempt < max_retries - 1:
                        retry_delay = retry_delay_base ** attempt
                        debug_print(f"Connection error, retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Re-raise if we've exhausted retries or it's not a connection error
                        raise
            
        except Exception as e:
            logger.error(f"Error getting structured output: {e}")
            debug_print(f"ERROR getting structured output: {str(e)}")
            
            # Return a fallback empty structure that matches expected format
            if "items" in output_schema.get("properties", {}):
                # Return empty array for array responses
                return []
            else:
                # Return error object for object responses
                return {"error": str(e)}
