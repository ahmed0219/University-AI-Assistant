"""
Metadata Extractor Module
Extracts and classifies document metadata for better organization.
"""
import os
import re
from typing import Dict, Any, List, Optional
from PyPDF2 import PdfReader


class MetadataExtractor:
    """
    Extracts metadata from documents for classification and filtering.
    """
    
    # Keywords for document classification
    DOCUMENT_PATTERNS = {
        "regulations": [
            "regulation", "rule", "policy", "procedure", "guideline",
            "code of conduct", "compliance", "disciplinary"
        ],
        "academic": [
            "course", "syllabus", "curriculum", "prerequisite", "credit",
            "semester", "exam", "grading", "academic", "degree", "major"
        ],
        "administrative": [
            "form", "application", "registration", "deadline", "fee",
            "admission", "enrollment", "office", "contact", "schedule"
        ],
        "financial": [
            "tuition", "scholarship", "financial aid", "payment", "refund",
            "fee structure", "billing", "loan"
        ],
        "student_services": [
            "housing", "health", "counseling", "career", "library",
            "student life", "clubs", "activities", "support"
        ]
    }
    
    def extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Metadata dictionary
        """
        reader = PdfReader(file_path)
        filename = os.path.basename(file_path)
        
        # Basic file metadata
        metadata = {
            "source": filename,
            "file_path": file_path,
            "total_pages": len(reader.pages),
            "file_size_kb": round(os.path.getsize(file_path) / 1024, 1)
        }
        
        # PDF info metadata
        if reader.metadata:
            metadata.update({
                "title": reader.metadata.get("/Title", ""),
                "author": reader.metadata.get("/Author", ""),
                "subject": reader.metadata.get("/Subject", ""),
                "creator": reader.metadata.get("/Creator", ""),
                "creation_date": str(reader.metadata.get("/CreationDate", ""))
            })
        
        # Extract and analyze content
        text_sample = self._extract_text_sample(reader)
        metadata["document_type"] = self._classify_document(text_sample, filename)
        metadata["keywords"] = self._extract_keywords(text_sample)
        
        return metadata
    
    def _extract_text_sample(
        self,
        reader: PdfReader,
        max_pages: int = 3
    ) -> str:
        """Extract text sample from first few pages."""
        text_parts = []
        
        for i, page in enumerate(reader.pages[:max_pages]):
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return " ".join(text_parts)
    
    def _classify_document(self, text: str, filename: str) -> str:
        """
        Classify document type based on content and filename.
        
        Args:
            text: Document text sample
            filename: Document filename
            
        Returns:
            Document type classification
        """
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        scores = {}
        
        for doc_type, keywords in self.DOCUMENT_PATTERNS.items():
            score = 0
            for keyword in keywords:
                # Check in text
                if keyword in text_lower:
                    score += text_lower.count(keyword)
                # Bonus for filename match
                if keyword.replace(" ", "_") in filename_lower or keyword.replace(" ", "-") in filename_lower:
                    score += 5
            
            scores[doc_type] = score
        
        # Return type with highest score (or 'general' if no matches)
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "general"
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract key terms from document."""
        # Simple keyword extraction based on capitalized terms and common patterns
        
        # Find capitalized phrases (likely proper nouns/titles)
        phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Count occurrences
        from collections import Counter
        phrase_counts = Counter(phrases)
        
        # Filter out common words
        stopwords = {
            "The", "This", "That", "These", "Those", "And", "For",
            "With", "From", "Into", "During", "Before", "After"
        }
        
        keywords = [
            phrase for phrase, count in phrase_counts.most_common(max_keywords * 2)
            if phrase not in stopwords and count > 1
        ]
        
        return keywords[:max_keywords]
    
    def batch_extract(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        Extract metadata from all PDFs in a directory.
        
        Args:
            directory_path: Path to directory
            
        Returns:
            List of metadata dictionaries
        """
        results = []
        
        for filename in os.listdir(directory_path):
            if not filename.endswith(".pdf"):
                continue
                
            file_path = os.path.join(directory_path, filename)
            
            try:
                metadata = self.extract_pdf_metadata(file_path)
                results.append(metadata)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                results.append({
                    "source": filename,
                    "error": str(e)
                })
        
        return results
    
    def generate_document_report(self, directory_path: str) -> Dict[str, Any]:
        """
        Generate a report about documents in a directory.
        
        Args:
            directory_path: Path to directory
            
        Returns:
            Report with statistics and classification
        """
        metadata_list = self.batch_extract(directory_path)
        
        # Aggregate statistics
        total_docs = len(metadata_list)
        total_pages = sum(m.get("total_pages", 0) for m in metadata_list)
        total_size_kb = sum(m.get("file_size_kb", 0) for m in metadata_list)
        
        # Document types distribution
        type_counts = {}
        for m in metadata_list:
            doc_type = m.get("document_type", "unknown")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        # All keywords
        all_keywords = []
        for m in metadata_list:
            all_keywords.extend(m.get("keywords", []))
        
        from collections import Counter
        top_keywords = Counter(all_keywords).most_common(20)
        
        return {
            "total_documents": total_docs,
            "total_pages": total_pages,
            "total_size_mb": round(total_size_kb / 1024, 2),
            "document_types": type_counts,
            "top_keywords": [{"keyword": k, "count": c} for k, c in top_keywords],
            "documents": metadata_list
        }


def analyze_pdf_directory(directory_path: str) -> Dict[str, Any]:
    """
    Convenience function to analyze a PDF directory.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Analysis report
    """
    extractor = MetadataExtractor()
    return extractor.generate_document_report(directory_path)
