# Project Brief: AI Academic Research Assistant Backend

## Core Objective

Provide a robust, AI-powered backend system for the Research Assistant frontend that efficiently processes academic papers, extracts relevant information based on user queries, and delivers structured research notes with proper academic formatting.

## Project Overview

The AI Academic Research Assistant Backend is a Django-based service that powers the "ResearchNotes" application. It serves as the engine behind the frontend's three-layer architecture by handling the actual research processing, AI integration, and data management. The backend processes research requests, searches for relevant academic papers, analyzes PDF content, and generates structured research notes that can be seamlessly integrated into the frontend's note management system.

## Key Features

1. **Research Session Management**
   - Session-based research tracking
   - Status updates and progress monitoring
   - WebSocket support for real-time updates

2. **Academic Paper Processing**
   - PDF downloading and text extraction
   - Metadata parsing for citation information
   - Harvard reference generation

3. **Intelligent Content Analysis**
   - Semantic search using embeddings
   - Contextual chunking of large documents
   - Relevance detection for targeted extraction

4. **AI Integration**
   - OpenAI API integration for text processing
   - Structured data extraction
   - Academic information classification

5. **Frontend-Ready Data Format**
   - Note output structured for frontend compatibility
   - Support for citations and references
   - Topic classification matching frontend requirements

## Technical Stack

- **Framework**: Django with Django REST Framework
- **Real-time**: Django Channels with WebSockets
- **Database**: SQLite (development), PostgreSQL (production ready)
- **AI Services**: OpenAI API for LLM and embeddings
- **PDF Processing**: PyMuPDF for document handling
- **Search Integration**: arXiv API for paper discovery
- **Background Processing**: Threading (simplified from Celery)
- **Testing**: Test script for terminal-based evaluation

## Design Principles

1. **Academic Integrity**
   - Accurate citation extraction and formatting
   - Source traceability for all extracted information
   - Proper attribution and reference management

2. **Performance Optimization**
   - Two-path processing for documents of different sizes
   - Embedding-based relevance detection to focus on important sections
   - Efficient text chunking to handle large documents

3. **Reliability**
   - Robust error handling with detailed logging
   - Status tracking for all processing stages
   - Fallback mechanisms for service disruptions

4. **Frontend Integration**
   - Data structures aligned with frontend requirements
   - Real-time updates via WebSockets
   - Clean API endpoints for frontend interaction

## Project Goals

1. Create a reliable backend that can process academic papers and extract relevant information
2. Implement intelligent search capabilities to find relevant sources
3. Deliver structured, well-formatted research notes to the frontend
4. Provide real-time feedback on research progress
5. Ensure compatibility with the existing frontend data model

## Current Status

The backend system has been implemented with core functionality working. It includes PDF processing, OpenAI integration, arXiv search, and research session management. The system has been recently enhanced with debug logging throughout to enable better tracking and issue identification. A test script has been implemented for terminal-based testing of the research process.