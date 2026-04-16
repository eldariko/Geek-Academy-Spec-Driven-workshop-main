"""Handbook service for loading and searching support policies"""
from pathlib import Path
from typing import Optional, List, Dict
import re


class HandbookService:
    """Load and search the support handbook for policy information"""
    
    def __init__(self, handbook_path: str):
        """Initialize handbook service
        
        Args:
            handbook_path: Path to support_handbook.md file
        """
        self.handbook_path = Path(handbook_path)
        self.content = ""
        self.sections: Dict[str, str] = {}
        self.load()
    
    def load(self):
        """Load and parse the handbook"""
        if not self.handbook_path.exists():
            raise FileNotFoundError(f"Handbook not found at {self.handbook_path}")
        
        with open(self.handbook_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        
        # Parse sections by heading (## Section Name)
        sections = re.split(r'^## ', self.content, flags=re.MULTILINE)
        
        for section in sections[1:]:  # Skip preamble
            lines = section.split('\n', 1)
            if len(lines) == 2:
                section_name = lines[0].strip()
                section_content = lines[1]
                self.sections[section_name] = section_content
    
    def get_section(self, section_name: str) -> Optional[str]:
        """Get a handbook section by name
        
        Args:
            section_name: Name of the section (e.g., "Refunds", "Cancellations")
        
        Returns:
            Section content or None if not found
        """
        # Try exact match first
        if section_name in self.sections:
            return self.sections[section_name]
        
        # Try case-insensitive match
        for key, value in self.sections.items():
            if key.lower() == section_name.lower():
                return value
        
        return None
    
    def search(self, query: str, context: Optional[str] = None) -> List[str]:
        """Search the handbook for content matching a query
        
        Args:
            query: Search term or phrase
            context: Optional context filter (e.g., "refunds", "billing")
        
        Returns:
            List of matching text snippets
        """
        query_lower = query.lower()
        matches = []
        
        # Search in specific context if provided
        content_to_search = self.content
        if context:
            section_content = self.get_section(context)
            if section_content:
                content_to_search = section_content
        
        # Split content into paragraphs and search
        paragraphs = re.split(r'\n\n+', content_to_search)
        for paragraph in paragraphs:
            if query_lower in paragraph.lower():
                # Return first 200 chars of matching paragraph
                matches.append(paragraph.strip()[:200])
        
        return matches
    
    def get_all_sections(self) -> Dict[str, str]:
        """Get all handbook sections
        
        Returns:
            Dictionary of {section_name: section_content}
        """
        return self.sections.copy()
