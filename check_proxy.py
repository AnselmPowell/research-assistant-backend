#!/usr/bin/env python
"""
Script to check proxy settings in the Python environment.
"""

import os
import sys
import inspect

# Print Python version and environment
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print("\nProxy environment variables:")
for env_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
    print(f"{env_var}: {os.environ.get(env_var, 'Not set')}")

# Check if requests is configured with proxies
try:
    import requests
    session = requests.Session()
    print("\nRequests session proxies:")
    print(session.proxies)
except ImportError:
    print("\nRequests library not installed")

# Check OpenAI configuration
try:
    from openai import OpenAI
    print("\nOpenAI library version:")
    import openai
    print(openai.__version__)
    
    # Check if OpenAI accepts proxies
    client_init_params = inspect.signature(OpenAI.__init__).parameters
    print("\nOpenAI client init parameters:")
    for param_name, param in client_init_params.items():
        print(f"- {param_name}: {param.default}")
except ImportError:
    print("\nOpenAI library not installed")

# Check Pydantic-AI configuration
try:
    from pydantic_ai import Agent
    print("\nPydantic-AI library:")
    import pydantic_ai
    print(f"Version: {getattr(pydantic_ai, '__version__', 'unknown')}")
    
    # Check if Agent accepts our model format
    try:
        agent = Agent('openai:gpt-4o-mini')
        print("Successfully initialized Pydantic-AI Agent")
    except Exception as e:
        print(f"Error initializing Pydantic-AI Agent: {e}")
except ImportError:
    print("\nPydantic-AI library not installed")

if __name__ == "__main__":
    print("Environment check complete")
