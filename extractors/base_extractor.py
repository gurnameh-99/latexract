#!/usr/bin/env python3
"""Base class for all extractors"""

class BaseExtractor:
    """Base class defining the interface for all extractors"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
    
    def log(self, message):
        """Print log message if verbose mode is enabled"""
        if self.verbose:
            print(message)
    
    def extract_title(self, content):
        """Extract title from content"""
        raise NotImplementedError("Subclasses must implement extract_title")
    
    def extract_abstract(self, content):
        """Extract abstract from content"""
        raise NotImplementedError("Subclasses must implement extract_abstract")
    
    def extract_year(self, content):
        """Extract publication year from content"""
        raise NotImplementedError("Subclasses must implement extract_year")
    
    def extract_main_text(self, content):
        """Extract main text from content"""
        raise NotImplementedError("Subclasses must implement extract_main_text")
    
    def extract_citations(self, content):
        """Extract citations from content"""
        raise NotImplementedError("Subclasses must implement extract_citations")
    
    def extract_equations(self, content):
        """Extract equations from content"""
        raise NotImplementedError("Subclasses must implement extract_equations")
    
    def extract_tables(self, content):
        """Extract tables from content"""
        raise NotImplementedError("Subclasses must implement extract_tables")
