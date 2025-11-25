"""
Monitoring service for development environment.
Tracks comprehensive metrics throughout the research process and generates detailed .md reports.
Only active when DEBUG=True to avoid production overhead.
"""

import os
import json
import datetime
import threading
from typing import Dict, List, Any, Optional
from django.conf import settings
from pathlib import Path

# Thread-safe file writing lock
file_lock = threading.Lock()

class ProcessMonitor:
    """Thread-safe monitor for tracking research process metrics."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = datetime.datetime.now()
        self.metrics = {
            'session_info': {
                'session_id': session_id,
                'start_time': self.start_time.isoformat(),
                'topics': [],
                'info_queries': [],
                'direct_urls': [],
                'is_url_only_search': False
            },
            'search_terms': {},
            'arxiv_search': {
                'queries_generated': [],
                'total_papers_found': 0,
                'search_duration': 0
            },
            'pre_filtering': {
                'total_papers': 0,
                'relevant_papers': 0,
                'filtered_papers': 0,
                'filtering_duration': 0
            },
            'pdf_processing': {
                'papers_processed': [],
                'total_processing_time': 0,
                'processing_strategy': {}
            },
            'note_extraction': {
                'total_notes_extracted': 0,
                'notes_per_paper': {},
                'final_notes_returned': 0,
                'notes_filtered_out': 0
            },
            'performance': {
                'total_duration': 0,
                'bottlenecks': []
            }
        }
        
        # Only create monitoring in development
        self.is_active = getattr(settings, 'DEBUG', False)
        
        if self.is_active:
            self.output_dir = self._setup_output_directory()
        else:
            self.output_dir = None
    
    def _setup_output_directory(self) -> str:
        """Set up the testing output directory."""
        base_dir = Path(settings.BASE_DIR)
        testing_dir = base_dir / "testing"
        testing_dir.mkdir(exist_ok=True)
        
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        session_dir = testing_dir / f"full_process_{timestamp}_{self.session_id[:8]}"
        session_dir.mkdir(exist_ok=True)
        
        return str(session_dir)
    
    def log_session_start(self, topics: List[str], info_queries: List[str], direct_urls: List[str]):
        """Log session initialization."""
        if not self.is_active:
            return
            
        self.metrics['session_info']['topics'] = topics
        self.metrics['session_info']['info_queries'] = info_queries  
        self.metrics['session_info']['direct_urls'] = direct_urls
        self.metrics['session_info']['is_url_only_search'] = len(topics) == 0 and len(direct_urls) > 0
        
        print(f"[MONITOR] Session {self.session_id[:8]} started - URL-only: {self.metrics['session_info']['is_url_only_search']}")
    
    def log_structured_search_terms(self, search_structure: Dict[str, List[str]]):
        """Log generated structured search terms."""
        if not self.is_active:
            return
            
        self.metrics['search_terms'] = search_structure
        
        total_terms = sum(len(terms) for terms in search_structure.values())
        print(f"[MONITOR] Generated {total_terms} structured search terms across {len(search_structure)} categories")
    
    def log_arxiv_search(self, queries: List[str], papers_found: int, duration: float):
        """Log arXiv search results."""
        if not self.is_active:
            return
            
        self.metrics['arxiv_search']['queries_generated'] = queries
        self.metrics['arxiv_search']['total_papers_found'] = papers_found
        self.metrics['arxiv_search']['search_duration'] = duration
        
        print(f"[MONITOR] arXiv search: {len(queries)} queries → {papers_found} papers in {duration:.2f}s")
    
    def log_pre_filtering(self, total_papers: int, relevant_papers: int, filtered_papers: int, duration: float):
        """Log pre-filtering results."""
        if not self.is_active:
            return
            
        self.metrics['pre_filtering']['total_papers'] = total_papers
        self.metrics['pre_filtering']['relevant_papers'] = relevant_papers
        self.metrics['pre_filtering']['filtered_papers'] = filtered_papers
        self.metrics['pre_filtering']['filtering_duration'] = duration
        
        filter_rate = (filtered_papers / total_papers * 100) if total_papers > 0 else 0
        print(f"[MONITOR] Pre-filtering: {relevant_papers}/{total_papers} papers kept ({filter_rate:.1f}% filtered)")
    
    def log_pdf_processing_start(self, paper_id: str, paper_url: str, paper_title: str, total_pages: int):
        """Log start of PDF processing for a paper."""
        if not self.is_active:
            return
            
        paper_info = {
            'paper_id': paper_id,
            'url': paper_url,
            'title': paper_title,
            'total_pages': total_pages,
            'start_time': datetime.datetime.now().isoformat(),
            'processing_strategy': '',
            'relevant_pages': [],
            'page_similarities': {},
            'chunks_processed': [],
            'notes_extracted': 0,
            'processing_time': 0,
            'status': 'processing'
        }
        
        self.metrics['pdf_processing']['papers_processed'].append(paper_info)
        print(f"[MONITOR] PDF processing started: {paper_title[:50]}... ({total_pages} pages)")
    
    def log_processing_strategy(self, paper_id: str, strategy: str):
        """Log which processing strategy was used (Simple/Advanced Path)."""
        if not self.is_active:
            return
            
        for paper in self.metrics['pdf_processing']['papers_processed']:
            if paper['paper_id'] == paper_id:
                paper['processing_strategy'] = strategy
                break
        
        print(f"[MONITOR] Paper {paper_id[:8]}: Using {strategy} processing strategy")
    
    def log_relevant_pages(self, paper_id: str, relevant_pages: List[int], page_similarities: Dict[int, float]):
        """Log relevant pages and their similarity scores."""
        if not self.is_active:
            return
            
        for paper in self.metrics['pdf_processing']['papers_processed']:
            if paper['paper_id'] == paper_id:
                paper['relevant_pages'] = relevant_pages
                paper['page_similarities'] = {str(k): v for k, v in page_similarities.items()}
                break
        
        avg_similarity = sum(page_similarities.values()) / len(page_similarities) if page_similarities else 0
        print(f"[MONITOR] Paper {paper_id[:8]}: {len(relevant_pages)} relevant pages (avg similarity: {avg_similarity:.3f})")
    
    def log_chunk_processing(self, paper_id: str, chunk_pages: tuple, notes_found: int):
        """Log chunk processing results."""
        if not self.is_active:
            return
            
        chunk_info = {
            'pages': f"{chunk_pages[0]+1}-{chunk_pages[1]+1}",
            'notes_found': notes_found
        }
        
        for paper in self.metrics['pdf_processing']['papers_processed']:
            if paper['paper_id'] == paper_id:
                paper['chunks_processed'].append(chunk_info)
                break
        
        print(f"[MONITOR] Paper {paper_id[:8]}: Chunk pages {chunk_info['pages']} → {notes_found} notes")
    
    def log_pdf_processing_complete(self, paper_id: str, notes_extracted: int, processing_time: float, status: str):
        """Log completion of PDF processing."""
        if not self.is_active:
            return
            
        for paper in self.metrics['pdf_processing']['papers_processed']:
            if paper['paper_id'] == paper_id:
                paper['notes_extracted'] = notes_extracted
                paper['processing_time'] = processing_time
                paper['status'] = status
                break
        
        self.metrics['note_extraction']['notes_per_paper'][paper_id] = notes_extracted
        self.metrics['note_extraction']['total_notes_extracted'] += notes_extracted
        
        print(f"[MONITOR] Paper {paper_id[:8]}: Complete - {notes_extracted} notes in {processing_time:.2f}s")
    
    def log_final_notes(self, final_notes_count: int, notes_filtered_count: int):
        """Log final note validation results."""
        if not self.is_active:
            return
            
        self.metrics['note_extraction']['final_notes_returned'] = final_notes_count
        self.metrics['note_extraction']['notes_filtered_out'] = notes_filtered_count
        
        filter_rate = (notes_filtered_count / (final_notes_count + notes_filtered_count) * 100) if (final_notes_count + notes_filtered_count) > 0 else 0
        print(f"[MONITOR] Final validation: {final_notes_count} notes returned ({notes_filtered_count} filtered, {filter_rate:.1f}%)")
    
    def finalize_and_save(self):
        """Finalize metrics and save comprehensive report."""
        if not self.is_active or not self.output_dir:
            return
            
        # Calculate final metrics
        end_time = datetime.datetime.now()
        self.metrics['session_info']['end_time'] = end_time.isoformat()
        self.metrics['performance']['total_duration'] = (end_time - self.start_time).total_seconds()
        
        # Calculate total PDF processing time
        total_pdf_time = sum(paper['processing_time'] for paper in self.metrics['pdf_processing']['papers_processed'])
        self.metrics['pdf_processing']['total_processing_time'] = total_pdf_time
        
        # Generate comprehensive markdown report
        self._generate_markdown_report()
        
        # Save raw JSON data
        self._save_json_data()
        
        print(f"[MONITOR] Session {self.session_id[:8]} complete - Report saved to {self.output_dir}")
    
    def _generate_markdown_report(self):
        """Generate a comprehensive markdown report."""
        if not self.output_dir:
            return
            
        report_path = os.path.join(self.output_dir, "full_process_report.md")
        
        with file_lock:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(self._build_markdown_content())
    
    def _build_markdown_content(self) -> str:
        """Build the markdown report content."""
        session_info = self.metrics['session_info']
        search_terms = self.metrics['search_terms']
        arxiv_search = self.metrics['arxiv_search']
        pre_filtering = self.metrics['pre_filtering']
        pdf_processing = self.metrics['pdf_processing']
        note_extraction = self.metrics['note_extraction']
        performance = self.metrics['performance']
        
        md_content = f"""# Full Research Process Report

**Session ID:** `{session_info['session_id']}`  
**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Duration:** {performance['total_duration']:.2f} seconds

---

## 📋 Session Information

| Parameter | Value |
|-----------|-------|
| **Start Time** | {session_info['start_time']} |
| **End Time** | {session_info['end_time']} |
| **Topics** | {len(session_info['topics'])} |
| **Info Queries** | {len(session_info['info_queries'])} |
| **Direct URLs** | {len(session_info['direct_urls'])} |
| **URL-Only Search** | {'✅ Yes' if session_info['is_url_only_search'] else '❌ No'} |

### Research Topics
{self._format_list_items(session_info['topics'])}

### Information Queries
{self._format_list_items(session_info['info_queries'])}

### Direct URLs
{self._format_list_items(session_info['direct_urls'])}

---

## 🔍 Generated Structured Search Terms

| Category | Count | Terms |
|----------|-------|-------|"""
        
        for category, terms in search_terms.items():
            category_name = category.replace('_', ' ').title()
            terms_str = ', '.join(f'`{term}`' for term in terms) if terms else 'None'
            md_content += f"\n| **{category_name}** | {len(terms)} | {terms_str} |"
        
        md_content += f"""

**Total Search Terms Generated:** {sum(len(terms) for terms in search_terms.values())}

---

## 📚 arXiv Search Results

| Metric | Value |
|--------|-------|
| **Queries Generated** | {len(arxiv_search['queries_generated'])} |
| **Papers Found** | {arxiv_search['total_papers_found']} |
| **Search Duration** | {arxiv_search['search_duration']:.2f} seconds |

### Generated arXiv Queries
"""
        
        for i, query in enumerate(arxiv_search['queries_generated'], 1):
            md_content += f"{i}. `{query}`\n"
        
        md_content += f"""
---

## 🔬 Pre-filtering Results

| Metric | Value | Percentage |
|--------|-------|------------|
| **Total Papers** | {pre_filtering['total_papers']} | 100% |
| **Relevant Papers** | {pre_filtering['relevant_papers']} | {(pre_filtering['relevant_papers']/pre_filtering['total_papers']*100) if pre_filtering['total_papers'] > 0 else 0:.1f}% |
| **Filtered Out** | {pre_filtering['filtered_papers']} | {(pre_filtering['filtered_papers']/pre_filtering['total_papers']*100) if pre_filtering['total_papers'] > 0 else 0:.1f}% |
| **Filtering Duration** | {pre_filtering['filtering_duration']:.2f} seconds | - |

---

## 📄 PDF Processing Details

| Metric | Value |
|--------|-------|
| **Papers Processed** | {len(pdf_processing['papers_processed'])} |
| **Total Processing Time** | {pdf_processing['total_processing_time']:.2f} seconds |
| **Average Time per Paper** | {(pdf_processing['total_processing_time']/len(pdf_processing['papers_processed'])) if pdf_processing['papers_processed'] else 0:.2f} seconds |

### Processing Strategy Distribution
"""
        
        strategy_counts = {}
        for paper in pdf_processing['papers_processed']:
            strategy = paper['processing_strategy']
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        for strategy, count in strategy_counts.items():
            percentage = (count / len(pdf_processing['papers_processed']) * 100) if pdf_processing['papers_processed'] else 0
            md_content += f"- **{strategy}:** {count} papers ({percentage:.1f}%)\n"
        
        md_content += "\n### Individual Paper Processing\n\n"
        
        for i, paper in enumerate(pdf_processing['papers_processed'], 1):
            status_emoji = {'success': '✅', 'error': '❌', 'no_relevant_info': '⚠️'}.get(paper['status'], '🔄')
            
            md_content += f"""#### {i}. {paper['title'][:60]}{'...' if len(paper['title']) > 60 else ''}

| Detail | Value |
|--------|-------|
| **Status** | {status_emoji} {paper['status']} |
| **Strategy** | {paper['processing_strategy']} |
| **Total Pages** | {paper['total_pages']} |
| **Relevant Pages** | {len(paper['relevant_pages'])} |
| **Chunks Processed** | {len(paper['chunks_processed'])} |
| **Notes Extracted** | {paper['notes_extracted']} |
| **Processing Time** | {paper['processing_time']:.2f} seconds |

"""
            
            if paper['relevant_pages']:
                md_content += "**Relevant Pages & Similarity Scores:**\n"
                for page in paper['relevant_pages']:
                    similarity = paper['page_similarities'].get(str(page), 0)
                    md_content += f"- Page {page + 1}: {similarity:.3f}\n"
                md_content += "\n"
            
            if paper['chunks_processed']:
                md_content += "**Chunk Processing Results:**\n"
                for chunk in paper['chunks_processed']:
                    md_content += f"- Pages {chunk['pages']}: {chunk['notes_found']} notes\n"
                md_content += "\n"
            
            md_content += "---\n\n"
        
        md_content += f"""
## 📝 Note Extraction Summary

| Metric | Value |
|--------|-------|
| **Total Notes Extracted** | {note_extraction['total_notes_extracted']} |
| **Notes After Validation** | {note_extraction['final_notes_returned']} |
| **Notes Filtered Out** | {note_extraction['notes_filtered_out']} |
| **Final Filter Rate** | {(note_extraction['notes_filtered_out']/(note_extraction['final_notes_returned']+note_extraction['notes_filtered_out'])*100) if (note_extraction['final_notes_returned']+note_extraction['notes_filtered_out']) > 0 else 0:.1f}% |

### Notes per Paper
"""
        
        for paper_id, note_count in note_extraction['notes_per_paper'].items():
            # Find paper title for readability
            paper_title = "Unknown Paper"
            for paper in pdf_processing['papers_processed']:
                if paper['paper_id'] == paper_id:
                    paper_title = paper['title'][:40] + ('...' if len(paper['title']) > 40 else '')
                    break
            
            md_content += f"- **{paper_title}**: {note_count} notes\n"
        
        md_content += f"""
---

## ⚡ Performance Analysis

| Metric | Value |
|--------|-------|
| **Total Session Duration** | {performance['total_duration']:.2f} seconds |
| **PDF Processing Time** | {pdf_processing['total_processing_time']:.2f} seconds |
| **PDF Processing %** | {(pdf_processing['total_processing_time']/performance['total_duration']*100) if performance['total_duration'] > 0 else 0:.1f}% |
| **Pre-filtering Time** | {pre_filtering['filtering_duration']:.2f} seconds |
| **arXiv Search Time** | {arxiv_search['search_duration']:.2f} seconds |

### Processing Efficiency
- **Papers per Minute**: {(len(pdf_processing['papers_processed'])/(pdf_processing['total_processing_time']/60)) if pdf_processing['total_processing_time'] > 0 else 0:.1f}
- **Notes per Minute**: {(note_extraction['total_notes_extracted']/(pdf_processing['total_processing_time']/60)) if pdf_processing['total_processing_time'] > 0 else 0:.1f}
- **Average Notes per Paper**: {(note_extraction['total_notes_extracted']/len(pdf_processing['papers_processed'])) if pdf_processing['papers_processed'] else 0:.1f}

---

*Report generated by ResearchAssistant Monitoring Service*
"""
        
        return md_content
    
    def _format_list_items(self, items: List[str]) -> str:
        """Format list items for markdown."""
        if not items:
            return "- None\n"
        return "\n".join(f"- {item}" for item in items) + "\n"
    
    def _save_json_data(self):
        """Save raw metrics data as JSON."""
        if not self.output_dir:
            return
            
        json_path = os.path.join(self.output_dir, "metrics_data.json")
        
        with file_lock:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2, default=str)

# Global monitor instance (thread-safe)
_current_monitor: Optional[ProcessMonitor] = None
_monitor_lock = threading.Lock()

def start_monitoring(session_id: str) -> ProcessMonitor:
    """Start monitoring for a session (development only)."""
    global _current_monitor
    
    # Only monitor in development
    if not getattr(settings, 'DEBUG', False):
        return ProcessMonitor(session_id)  # Return inactive monitor
    
    with _monitor_lock:
        _current_monitor = ProcessMonitor(session_id)
        return _current_monitor

def get_current_monitor() -> Optional[ProcessMonitor]:
    """Get the current active monitor."""
    return _current_monitor

def finalize_monitoring():
    """Finalize and save the current monitoring session."""
    global _current_monitor
    
    with _monitor_lock:
        if _current_monitor:
            _current_monitor.finalize_and_save()
            _current_monitor = None
