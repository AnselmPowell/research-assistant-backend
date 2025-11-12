from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from urllib.parse import urlparse
import requests
import re
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class ValidatePdfUrlView(APIView):
    """View for validating PDF URLs."""
    
    def post(self, request, format=None):
        """Validate if a URL points to a downloadable PDF and extract title."""
        url = request.data.get('url')
        
        if not url:
            return Response({'isValid': False, 'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate URL format
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                return Response({'isValid': False, 'error': 'Invalid URL format'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Normalize URL (e.g., convert arXiv abstract URLs to PDF URLs)
            url = self._normalize_url(url)
            
            # Make HEAD request to check content type and size
            headers = {
                'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool)',
                'Accept': 'application/pdf'
            }
            
            try:
                # First do a HEAD request to check if accessible and get metadata
                response = requests.head(url, headers=headers, timeout=10)
                
                if not response.ok:
                    return Response({
                        'isValid': False, 
                        'error': f'URL is not accessible (Status: {response.status_code})'
                    })
                
                # Check content type (but be lenient)
                content_type = response.headers.get('Content-Type', '')
                is_pdf = 'application/pdf' in content_type.lower()
                url_ends_with_pdf = url.lower().endswith('.pdf')
                url_contains_pdf = 'pdf' in url.lower()
                
                # Check file size
                content_length = response.headers.get('Content-Length')
                max_size = 50 * 1024 * 1024  # 50 MB
                if content_length and int(content_length) > max_size:
                    return Response({
                        'isValid': False,
                        'error': f'File too large: {int(content_length) / (1024*1024):.2f} MB (max 50 MB)'
                    })
                
                # Default to extracting title from URL
                title = self._extract_title_from_url(url)
                
                # If it doesn't look like a PDF based on content type or URL,
                # we should be cautious but allow it if there are strong PDF indicators
                if not is_pdf and not url_ends_with_pdf:
                    if url_contains_pdf:
                        # URL contains "pdf" but doesn't have PDF content type
                        # This is common with academic sites that use redirects
                        return Response({
                            'isValid': True,
                            'url': url,
                            'title': title,
                            'contentType': content_type,
                            'contentLength': content_length,
                            'warning': 'URL might be a PDF but content type is ambiguous'
                        })
                    else:
                        return Response({
                            'isValid': False,
                            'error': f'URL does not appear to be a PDF (Content-Type: {content_type})'
                        })
                
                # Try to extract title from the actual PDF
                # Reuse existing PDF service functionality if possible
                try:
                    # This will attempt to download just enough of the PDF to get metadata
                    # Use a short timeout to avoid long-running requests
                    pdf_title = self._extract_title_from_pdf(url)
                    if pdf_title:
                        title = pdf_title
                except Exception as e:
                    # If title extraction fails, continue with URL-based title
                    logger.warning(f"Error extracting title from PDF {url}: {str(e)}")
                    # No action needed - we already have a fallback title
                
                # All checks passed
                return Response({
                    'isValid': True,
                    'url': url,
                    'title': title,
                    'contentType': content_type,
                    'contentLength': content_length
                })
                    
            except requests.exceptions.Timeout:
                return Response({
                    'isValid': False,
                    'error': 'Timeout when validating URL'
                })
            except requests.exceptions.RequestException as e:
                logger.error(f"Error validating URL {url}: {str(e)}")
                return Response({
                    'isValid': False,
                    'error': 'Network error when validating URL'
                })
                
        except Exception as e:
            logger.error(f"Unexpected error in validate_pdf_url: {str(e)}")
            return Response({
                'isValid': False,
                'error': 'Server error when validating URL'
            })
    
    def _normalize_url(self, url):
        """Normalize URL for better validation."""
        # Special case for arXiv - convert abstract URLs to PDF URLs
        if "/abs/" in url and "arxiv.org" in url:
            url = url.replace("/abs/", "/pdf/")
            if not url.endswith('.pdf'):
                url = url + '.pdf'
        return url
    
    def _extract_title_from_url(self, url):
        """Extract a human-readable title from a URL."""
        try:
            # Get the last part of the path
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            filename = path_parts[-1] if path_parts else ''
            
            if filename:
                # Clean up filename
                title = (
                    filename
                    .replace('.pdf', '')
                    .replace('-', ' ')
                    .replace('_', ' ')
                    .strip()
                )
                if title:
                    return title
            
            # Fallback to domain
            return f"PDF from {parsed.netloc}"
        except:
            return "PDF Document"
    
    def _extract_title_from_pdf(self, url, timeout=15):
        """Extract title from the PDF metadata using PyPDF2."""
        try:
            from io import BytesIO
            
            # Use PyPDF2 for PDF metadata extraction
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                # Fallback to older version
                from PyPDF2 import PdfFileReader as PdfReader
            
            headers = {
                'User-Agent': 'ResearchAssistantBot/1.0 (Educational Research Tool)',
                'Accept': 'application/pdf',
                'Range': 'bytes=0-10240'  # First 10KB should contain metadata
            }
            
            # Try to get just the header part of the PDF
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            
            if not response.ok:
                return None
            
            # Create a temporary file to store the partial PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                # Write the partial content
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        tmp_file.write(chunk)
                
                tmp_file_path = tmp_file.name
            
            # Extract metadata from the partial PDF
            try:
                with open(tmp_file_path, 'rb') as f:
                    pdf = PdfReader(f)
                    
                    # Try to get title from document info
                    if hasattr(pdf, 'metadata') and pdf.metadata and hasattr(pdf.metadata, 'title') and pdf.metadata.title:
                        return pdf.metadata.title
                    elif hasattr(pdf, 'getDocumentInfo') and pdf.getDocumentInfo() and hasattr(pdf.getDocumentInfo(), 'title') and pdf.getDocumentInfo().title:
                        return pdf.getDocumentInfo().title
                    
                    # If no title in metadata, try to extract from first page text
                    if len(pdf.pages) > 0:
                        first_page_text = pdf.pages[0].extract_text()
                        # Take first line as potential title
                        if first_page_text:
                            lines = first_page_text.strip().split('\n')
                            if lines:
                                return lines[0][:100]  # Limit title length
            except Exception as e:
                logger.error(f"PDF metadata extraction error: {str(e)}")
                return None
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            
            return None
        except Exception as e:
            # Log error but don't fail validation
            logger.error(f"Error extracting PDF title: {str(e)}")
            return None