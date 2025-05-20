#!/usr/bin/env python3
"""Extractor using regex patterns"""
import os
import re
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from latex_patterns import (
    remove_latex_comments,
    extract_title,
    extract_abstract,
    extract_bibliography,
    detect_document_class
)
from .base_extractor import BaseExtractor

class PatternExtractor(BaseExtractor):
    """Extract information from LaTeX using regex patterns"""
    
    def extract_from_file(self, tex_file_path):
        """Extract all information from a LaTeX file"""
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        document_class = detect_document_class(content)
        # Clean LaTeX content first
        clean_content = remove_latex_comments(content)
        
        return {
            "title": self.extract_title(clean_content),
            "abstract": self.extract_abstract(clean_content),
            "year": self.extract_year(clean_content),
            "main_text": self.extract_main_text(clean_content),
            "citations": self.extract_citations(clean_content, document_class),
            "equations": self.extract_equations(clean_content),
            "tables": self.extract_tables(clean_content)
        }
    
    def extract_title(self, content):
        """Extract title using existing pattern extractor"""
        return extract_title(content)
    
    def extract_abstract(self, content):
        """Extract abstract using existing pattern extractor"""
        return extract_abstract(content)
    
    def extract_year(self, content):
        """Extract year using regex patterns with improved precision"""
        # Check if \today is used for date
        if re.search(r'\\date\{\\today\}', content) or re.search(r'\\date\s*\{?\s*\\today', content):
            self.log("Date uses \\today, will require API fallback")
            return None
        
        # Look for date/year in specific publication contexts
        publication_patterns = [
            # Years in specific publication contexts (more reliable)
            r'(?:received|accepted|published|revised)(?:\s+on)?(?:\s+\w+)?\s+\w+\s+(\d{1,2})?\s*,?\s*(19|20)\d{2}',
            r'copyright\s*(?:\(c\)|©)?\s*(19|20)\d{2}',
            r'(?:journal|conference)\s+\w+\s*,?\s*(?:vol\.?|volume)\s*\d+\s*,?\s*(?:no\.?|number)\s*\d+\s*,?\s*(19|20)\d{2}',
            r'(?:updated\s+)(\w+\s+\d{1,2}\s*,?\s*(19|20)\d{2})',
            r'\d{1,2}\s+\w+\s+(19|20)\d{2}',  # Date format like "12 January 2022"
            r'\w+\s+\d{1,2}\s*,?\s*(19|20)\d{2}',  # Date format like "January 12, 2022"
        ]
        
        # Exclude address/affiliation sections from content for year search
        content_no_address = content
        address_sections = re.finditer(r'\\(?:address|affiliation|institute|email|thanks)[^{]*\{[^}]*\}', content, re.DOTALL)
        for match in address_sections:
            content_no_address = content_no_address.replace(match.group(0), '')
        
        # Look for year pattern in specific publication contexts
        for pattern in publication_patterns:
            match = re.search(pattern, content_no_address, re.IGNORECASE)
            if match:
                # Extract the last group that should contain the year
                year_groups = [g for g in match.groups() if g and re.match(r'(19|20)\d{2}', g)]
                if year_groups:
                    return year_groups[-1]
                
                # If no explicit capture group, find the year in the matched text
                year_match = re.search(r'(19|20)\d{2}', match.group(0))
                if year_match:
                    return year_match.group(0)
        
        # Look for date/year in standard LaTeX commands
        date_patterns = [
            r'\\date\{.*?((?:19|20)\d{2}).*?\}',  # \date{...2023...}
            r'\\year\{((?:19|20)\d{2})\}',        # \year{2023}
            r'\\copyright\{((?:19|20)\d{2})\}'    # \copyright{2023}
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content_no_address)
            if match:
                for group in match.groups():
                    if group and re.match(r'(19|20)\d{2}', group):
                        return group
        
        return None
    
    def extract_main_text(self, content):
        """Extract main text using regex patterns"""  
        
        # look for text after abstract but before references/bibliography
        abstract_text = extract_abstract(content)
        if abstract_text:
            # Try to find where the abstract ends
            abstract_patterns = [
                r'\\end\{abstract\}',
                r'\\keywords',
                r'\\begin\{keywords\}',
                r'\\begin\{IEEEkeywords\}',
                r'\\maketitle',
            ]
            
            abstract_end_pos = -1
            for pattern in abstract_patterns:
                match = re.search(pattern, content)
                if match and (abstract_end_pos == -1):
                    abstract_end_pos = match.end()
            
            bibliography_start_pos = len(content)
            bibliography_patterns = [
                r'\\begin\{thebibliography\}',
                r'\\bibliography\{',
                r'\\section\{references\}',
                r'\\section\{bibliography\}',
                r'\\renewcommand\{\\refname\}',
                r'\\bibliographystyle\{',
            ]
            
            for pattern in bibliography_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match and match.start() < bibliography_start_pos:
                    bibliography_start_pos = match.start()
            
            if abstract_end_pos > 0 and bibliography_start_pos > abstract_end_pos:
                main_text = content[abstract_end_pos:bibliography_start_pos]
                
                # Save debug files only in verbose mode
                if self.verbose:
                    with open('main_text.txt', 'w') as f:
                        f.write(main_text)
                    with open('cleaned_main_text.txt', 'w') as f:
                        f.write(self.clean_tex_content(main_text))
                
                return self.clean_tex_content(main_text)
        
        # If no introduction or abstract found, extract text from the body part
        content_body_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', content, re.DOTALL)
        if content_body_match:
            # Save debug files only in verbose mode
            if self.verbose:
                with open('content_body_match.txt', 'w') as f:
                    f.write(content_body_match.group(1))
                with open('cleaned_content_body_match.txt', 'w') as f:
                    f.write(self.clean_tex_content(content_body_match.group(1)))
            
            return self.clean_tex_content(content_body_match.group(1))
        
        # Fallback: just clean the whole content
        return self.clean_tex_content(content)
    
    def clean_tex_content(self, tex_content):
        """Clean LaTeX content to extract plain text"""
        # Remove LaTeX commands and environments
        cleaned = tex_content
        
        # Remove figures and tables
        cleaned = re.sub(r'\\begin\{figure\}.*?\\end\{figure\}', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\\begin\{table\}.*?\\end\{table\}', '', cleaned, flags=re.DOTALL)
        
        # Remove equations
        cleaned = re.sub(r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\\begin\{align\*?\}.*?\\end\{align\*?\}', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\\begin\{eqnarray\*?\}.*?\\end\{eqnarray\*?\}', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\$\$(.*?)\$\$', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\$(.*?)\$', '', cleaned)
        
        # Remove other LaTeX commands
        cleaned = re.sub(r'\\[a-zA-Z]+(\{.*?\}|\[.*?\])*', '', cleaned)
        
        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def extract_citations(self, content, document_class):
        """Extract citations using existing pattern extractor"""
        return extract_bibliography(content, document_class) or []
    
    def extract_equations(self, content):
        """Extract equations using regex patterns - including inline math"""
        equations = []
        
        # Find displayed equations
        env_patterns = [
            (r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', 1, True),  # Always an equation
            (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', 1, True),
            (r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', 1, True),
            (r'\\begin\{displaymath\}(.*?)\\end\{displaymath\}', 1, True),
            (r'\$\$(.*?)\$\$', 1, True),  # Display math is usually an equation
            (r'\\\[(.*?)\\\]', 1, True)
        ]
        
        for pattern, group, is_equation in env_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                equations.append({
                    "latex": match.group(group).strip(),
                    "is_display": True,
                    "is_equation": is_equation
                })
                if len(equations) >= 5:  # Only need the first 5
                    return equations
        
        # Find inline math and check if it's an equation
        inline_pattern = r'\$(.*?)\$'
        for match in re.finditer(inline_pattern, content):
            math_content = match.group(1).strip()
            
            # Check if this is an equation (contains =, <, >, \approx, etc.)
            is_equation = bool(re.search(r'[=<>]|\\approx|\\sim|\\cong|\\equiv|\\neq|\\ne|\\leq|\\geq', math_content))
            
            if is_equation:
                equations.append({
                    "latex": math_content,
                    "is_display": False,
                    "is_equation": True
                })
                
                if len(equations) >= 5:  # Only need the first 5
                    return equations
        
        return equations
    
    def extract_tables(self, content):
        """Extract tables using regex patterns"""
        tables = []
        
        # Find table environments
        table_patterns = [
            r'\\begin\{table\*?\}(.*?)\\end\{table\*?\}',
            r'\\begin\{tabular\}(.*?)\\end\{tabular\}'
        ]
        
        for pattern in table_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                table_content = match.group(0)
                
                # Try to extract caption
                caption_match = re.search(r'\\caption\{(.*?)\}', table_content, re.DOTALL)
                caption = caption_match.group(1) if caption_match else "Unknown caption"
                
                tables.append({
                    "caption": caption,
                    "content": table_content
                })
                
                if tables:  # Only need the first table
                    return [tables[0]]
        
        return []
