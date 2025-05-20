#!/usr/bin/env python3
"""Controller for LaTeX extraction process"""
import os
import json
import re
import requests
from bs4 import BeautifulSoup
from extractors.ast_extractor import AstExtractor
from extractors.pattern_extractor import PatternExtractor
from extractors.sympy_converter import SymPyConverter
from extractors.mathml_converter import MathMLConverter
from extractors.llm_extractor import LaTeXExtractor

class ExtractController:
    """Controller class that orchestrates the extraction process"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.ast_extractor = AstExtractor(verbose)
        self.pattern_extractor = PatternExtractor(verbose)
        self.sympy_converter = SymPyConverter(verbose)
        self.mathml_converter = MathMLConverter(verbose)
        self.llm_extractor = LaTeXExtractor()
        
        # To track which method was used for extraction
        self.extraction_methods = {
            "title": None,
            "abstract": None,
            "year": None,
            "main_text": None,
            "citations": None,
            "display_equations": None,
            "inline_equations": None,
            "tables": None
        }
    
    def log(self, message):
        """Print log message if verbose mode is enabled"""
        if self.verbose:
            print(message)
    
    def extract_from_file(self, tex_file_path, output_file=None, output_format='mathml'):
        """Extract information from a LaTeX file with multiple fallback methods
        
        Args:
            tex_file_path: Path to the LaTeX file
            output_file: Optional path to save the results
            output_format: Format for equation conversion ('mathml' or 'sympy')
            
        Returns:
            Dictionary containing extracted information
        """
        self.log(f"Processing LaTeX file: {tex_file_path}")
        
        # First, check if the file exists
        if not os.path.exists(tex_file_path):
            raise FileNotFoundError(f"LaTeX file not found: {tex_file_path}")
        
        # Initialize results structure
        results = {
            "title": None,
            "abstract": None,
            "year": None,
            "main_text_sample": {
                "first_500": None,
                "last_500": None
            },
            "citations": [],
            "display_equations": [],
            "inline_equations": [],
            "tables": [],
            "extraction_method": self.extraction_methods.copy()
        }
        
        # Always try to extract year from arXiv ID in filename first
        arxiv_year = self._extract_arxiv_year(tex_file_path)
        if arxiv_year:
            self.log(f"Found year {arxiv_year} from arXiv ID in filename")
            results['year'] = arxiv_year
            results['extraction_method']['year'] = "arxiv_id"
        
        # If no arXiv ID year found, check for \today
        if results['year'] is None:
            uses_today = self._check_for_today(tex_file_path)
            if uses_today:
                self.log("\\today detected in date, year will require alternative extraction")
        
        # Standard extraction flow: AST first, pattern as fallback
        self.log("Attempting AST-based extraction...")
        ast_results = self.ast_extractor.extract_from_file(tex_file_path)
        if ast_results:
            self.update_results(results, ast_results, "ast")
        
        # If elements are missing, try pattern-based extraction
        if self.has_missing_elements(results):
            self.log("Some elements missing, trying pattern-based extraction...")
            pattern_results = self.pattern_extractor.extract_from_file(tex_file_path)
            self.update_results(results, pattern_results, "pattern")
            
            # If year is still missing and we have a title, try Google Scholar lookup before LLM
            if results['year'] is None and results['title']:
                self.log("Year not found, attempting Google Scholar lookup...")
                year = self.lookup_year_from_scholar(results['title'])
                if year:
                    # Only use Google Scholar year if it's a full 4-digit year
                    if len(year) == 4 and year.isdigit():
                        results['year'] = year
                        results['extraction_method']['year'] = "scholar_api"
                    else:
                        self.log(f"Ignoring invalid year format from Google Scholar: {year}")
            
            # If still missing elements, try LLM-based extraction as final fallback
            if self.has_missing_elements(results):
                self.log("Some elements still missing, trying LLM-based extraction...")
                try:
                    with open(tex_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    llm_results = self.llm_extractor.extract_from_content(content)
                    self.update_results(results, llm_results, "llm")
                except Exception as e:
                    self.log(f"LLM extraction failed: {str(e)}")
        
        # Convert equations based on the specified format
        if output_format == 'mathml':
            # Process display equations
            if results['display_equations']:
                self.log("Converting display equations to MathML format...")
                latex_equations = [eq['latex'] for eq in results['display_equations']]
                mathml_results = self.mathml_converter.convert_equations(latex_equations)
                
                # Merge back the conversion results
                for i, eq in enumerate(results['display_equations']):
                    if i < len(mathml_results):
                        eq['mathml'] = mathml_results[i].get('mathml')
                        eq['verified'] = mathml_results[i].get('verified', False)
                        if 'error' in mathml_results[i]:
                            eq['error'] = mathml_results[i]['error']
            
            # Process inline equations
            if results['inline_equations']:
                self.log("Converting inline equations to MathML format...")
                latex_equations = [eq['latex'] for eq in results['inline_equations']]
                mathml_results = self.mathml_converter.convert_equations(latex_equations)
                
                # Merge back the conversion results
                for i, eq in enumerate(results['inline_equations']):
                    if i < len(mathml_results):
                        eq['mathml'] = mathml_results[i].get('mathml')
                        eq['verified'] = mathml_results[i].get('verified', False)
                        if 'error' in mathml_results[i]:
                            eq['error'] = mathml_results[i]['error']
        else:  # Default to SymPy conversion
            # Process display equations
            if results['display_equations']:
                self.log("Converting display equations to sympy format...")
                latex_equations = [eq['latex'] for eq in results['display_equations']]
                sympy_results = self.sympy_converter.convert_equations(latex_equations)
                
                # Merge back the conversion results
                for i, eq in enumerate(results['display_equations']):
                    if i < len(sympy_results):
                        eq['sympy'] = sympy_results[i].get('sympy')
                        eq['verified'] = sympy_results[i].get('verified', False)
                        if 'error' in sympy_results[i]:
                            eq['error'] = sympy_results[i]['error']
            
            # Process inline equations
            if results['inline_equations']:
                self.log("Converting inline equations to sympy format...")
                latex_equations = [eq['latex'] for eq in results['inline_equations']]
                sympy_results = self.sympy_converter.convert_equations(latex_equations)
                
                # Merge back the conversion results
                for i, eq in enumerate(results['inline_equations']):
                    if i < len(sympy_results):
                        eq['sympy'] = sympy_results[i].get('sympy')
                        eq['verified'] = sympy_results[i].get('verified', False)
                        if 'error' in sympy_results[i]:
                            eq['error'] = sympy_results[i]['error']
        
        # Convert tables to readable format
        if results['tables']:
            self.log("Converting tables to readable format...")
            for table in results['tables']:
                self._convert_table_to_readable(table)
        
        # Save the results if output file is specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.log(f"Extracted data saved to: {output_file}")
        
        return results
    
    def _check_for_today(self, tex_file_path):
        """Check if the LaTeX file uses \today in date command"""
        try:
            with open(tex_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for \today in date command
            return bool(re.search(r'\\date\{[^}]*\\today[^}]*\}', content) or 
                       re.search(r'\\date\s*\\today', content))
        except Exception as e:
            self.log(f"Error checking for \\today: {str(e)}")
            return False
    
    def _extract_arxiv_year(self, tex_file_path):
        """Extract year from arXiv ID in filename"""
        # ArXiv ID pattern: YYMM.NNNN or newer format YYMM.NNNNN
        # where YY=year, MM=month
        arxiv_match = re.search(r'(\d{2})(\d{2})\.(\d+)', os.path.basename(tex_file_path))
        if arxiv_match:
            year_prefix = arxiv_match.group(1)
            # Convert 2-digit year to 4-digit
            # ArXiv started in 1991, so any year < 91 must be 20xx
            full_year = ""
            if int(year_prefix) < 91:
                full_year = "20" + year_prefix
            else:
                full_year = "19" + year_prefix
            
            return full_year
        
        return None
    
    def _convert_table_to_readable(self, table):
        """Convert LaTeX table to a readable format and verify it"""
        if 'content' not in table or not isinstance(table['content'], str):
            return
        
        latex_content = table['content']
        
        # Extract tabular environment
        tabular_match = re.search(r'\\begin\{(tabular|array)\}(\{[^}]*\})(.*?)\\end\{\1\}', 
                                 latex_content, re.DOTALL)
        
        if not tabular_match:
            return
        
        # Get column specification and content
        column_spec = tabular_match.group(2)
        tabular_content = tabular_match.group(3)
        
        # Parse column spec to count columns
        column_count = len(re.findall(r'[lcr]', column_spec))
        
        # Split rows
        rows = re.split(r'\\\\', tabular_content)
        structured_rows = []
        
        for row in rows:
            # Skip empty rows
            if not row.strip():
                continue
                
            # Split cells by &
            cells = row.split('&')
            
            # Clean cells: remove LaTeX commands
            cleaned_cells = []
            for cell in cells:
                # Basic cleanup - remove common LaTeX formatting
                cell = re.sub(r'\\textbf\{([^}]*)\}', r'\1', cell)  # Bold
                cell = re.sub(r'\\textit\{([^}]*)\}', r'\1', cell)  # Italic
                cell = re.sub(r'\\underline\{([^}]*)\}', r'\1', cell)  # Underline
                cell = re.sub(r'\\emph\{([^}]*)\}', r'\1', cell)  # Emphasis
                
                # Remove math-mode markers but keep content
                cell = re.sub(r'\$([^$]*)\$', r'\1', cell)
                
                # Remove other LaTeX commands
                cell = re.sub(r'\\[a-zA-Z]+(?:\[[^]]*\])?(?:\{[^}]*\})?', '', cell)
                
                cleaned_cells.append(cell.strip())
            
            # Verify row has correct number of cells
            if len(cleaned_cells) > 0:
                # Pad or truncate to match column count
                if len(cleaned_cells) < column_count:
                    cleaned_cells.extend([''] * (column_count - len(cleaned_cells)))
                elif len(cleaned_cells) > column_count:
                    cleaned_cells = cleaned_cells[:column_count]
                
                structured_rows.append(cleaned_cells)
        
        # Store structured format
        table['structured_format'] = {
            'column_spec': column_spec,
            'column_count': column_count,
            'rows': structured_rows,
            'verified': len(structured_rows) > 0
        }
    
    def lookup_year_from_scholar(self, title):
        """Look up paper year from Google Scholar using the title"""
        if not title:
            return None
            
        try:
            # Prepare the search query
            query = title.replace(' ', '+')
            url = f"https://scholar.google.com/scholar?q={query}"
            
            # Set a user agent to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Parse the HTML response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the search results
                results = soup.find_all('div', class_='gs_ri')
                
                for result in results:
                    # Get the title
                    result_title = result.find('h3', class_='gs_rt')
                    
                    if result_title and self._title_similarity(title, result_title.text.strip()) > 0.7:
                        # Find the footer with publication details
                        footer = result.find('div', class_='gs_a')
                        if footer:
                            # Look for a full 4-digit year in the footer
                            year_match = re.search(r'(?:19|20)\d{2}', footer.text)
                            if year_match:
                                return year_match.group(0)
                            
                            # If not found, look for arXiv ID with YYMM format
                            arxiv_match = re.search(r'arxiv.org/abs/(\d{2})(\d{2})\.', footer.text, re.IGNORECASE)
                            if arxiv_match:
                                year_prefix = arxiv_match.group(1)
                                century = '19' if int(year_prefix) > 90 else '20'
                                return century + year_prefix
            
            return None
        except Exception as e:
            self.log(f"Error in Google Scholar lookup: {str(e)}")
            return None
    
    def _title_similarity(self, title1, title2):
        """Calculate similarity between two titles"""
        # Simple similarity calculation
        t1 = title1.lower()
        t2 = title2.lower()
        
        # Remove common prefixes from Google Scholar results
        t2 = re.sub(r'^\[[^\]]+\]', '', t2).strip()
        
        # Count matching words
        words1 = set(re.findall(r'\w+', t1))
        words2 = set(re.findall(r'\w+', t2))
        
        if not words1 or not words2:
            return 0
            
        common_words = words1.intersection(words2)
        return len(common_words) / max(len(words1), len(words2))
    
    def update_results(self, results, new_results, method):
        """Update results with new results, tracking the extraction method"""
        # Update title if not already found
        if not results['title'] and new_results.get('title'):
            results['title'] = new_results['title']
            results['extraction_method']['title'] = method
        
        # Update abstract if not already found
        if not results['abstract'] and new_results.get('abstract'):
            results['abstract'] = new_results['abstract']
            results['extraction_method']['abstract'] = method
        
        # Update year if not already found
        if not results['year'] and new_results.get('year'):
            results['year'] = new_results['year']
            results['extraction_method']['year'] = method
        
        # Update main text if not already found
        if not results['main_text_sample']['first_500'] and new_results.get('main_text'):
            main_text = new_results['main_text']
            first_500 = main_text[:500] if len(main_text) > 500 else main_text
            last_500 = main_text[-500:] if len(main_text) > 500 else main_text
            results['main_text_sample']['first_500'] = first_500
            results['main_text_sample']['last_500'] = last_500
            results['extraction_method']['main_text'] = method
        
        # Update citations if not already found
        if not results['citations'] and new_results.get('citations'):
            results['citations'] = new_results['citations']
            results['extraction_method']['citations'] = method
        
        # Handle display equations
        if not results['display_equations'] and new_results.get('display_equations'):
            # Direct assignment if the result is already correctly formatted
            results['display_equations'] = new_results['display_equations']
            results['extraction_method']['display_equations'] = method
        elif not results['display_equations'] and new_results.get('equations'):
            # For backward compatibility or pattern extractor
            if isinstance(new_results['equations'], list):
                # Determine if equations are already structured or just latex strings
                if new_results['equations'] and isinstance(new_results['equations'][0], dict):
                    # Filter for display equations
                    display_eqs = [eq for eq in new_results['equations'] if eq.get('is_display', True)]
                    if display_eqs:
                        results['display_equations'] = display_eqs[:5]  # First 5
                        results['extraction_method']['display_equations'] = method
                else:
                    # Legacy format - assume all are display equations
                    results['display_equations'] = [{"latex": eq, "is_display": True, "is_equation": True} 
                                                 for eq in new_results['equations'][:5]]
                    results['extraction_method']['display_equations'] = method
            
        # Handle inline equations
        if not results['inline_equations'] and new_results.get('inline_equations'):
            # Direct assignment if the result is already correctly formatted
            results['inline_equations'] = new_results['inline_equations']
            results['extraction_method']['inline_equations'] = method
        elif not results['inline_equations'] and new_results.get('equations'):
            # For backward compatibility or pattern extractor
            if isinstance(new_results['equations'], list):
                # Check if equations are already structured
                if new_results['equations'] and isinstance(new_results['equations'][0], dict):
                    # Filter for inline equations
                    inline_eqs = [eq for eq in new_results['equations'] if not eq.get('is_display', True)]
                    if inline_eqs:
                        results['inline_equations'] = inline_eqs[:5]  # First 5
                        results['extraction_method']['inline_equations'] = method
        
        # Update tables if not already found
        if not results['tables'] and new_results.get('tables'):
            results['tables'] = new_results['tables']
            results['extraction_method']['tables'] = method
    
    def has_missing_elements(self, results):
        """Check if any essential elements are missing from extraction results"""
        return (
            results['title'] is None or
            results['abstract'] is None or
            results['year'] is None or
            results['main_text_sample']['first_500'] is None or
            not results['citations'] or
            (not results['display_equations'] and not results['inline_equations']) or
            not results['tables']
        )
