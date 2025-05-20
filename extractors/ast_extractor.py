#!/usr/bin/env python3
"""Extractor using Pandoc AST"""
import os
import json
import subprocess
import tempfile
import re
from .base_extractor import BaseExtractor

class AstExtractor(BaseExtractor):
    """Extract information from LaTeX using Pandoc AST"""
    
    def extract_from_file(self, tex_file_path):
        """Extract all information from a LaTeX file"""
        # Create temporary file for JSON AST
        fd, temp_json = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        
        try:
            # Run pandoc to create JSON AST
            cmd = ['pandoc', tex_file_path, '-t', 'json', '-o', temp_json, '--mathml']
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Read the AST
            with open(temp_json, 'r', encoding='utf-8') as f:
                ast_data = json.load(f)
            
            # Save debug files only in verbose mode
            if self.verbose:
                with open('ast.json', 'w', encoding='utf-8') as f:
                    json.dump(ast_data, f, indent=4)
                with open('metadata.json', 'w', encoding='utf-8') as f:
                    json.dump(ast_data.get('meta', {}), f, indent=4)
                with open('blocks.json', 'w', encoding='utf-8') as f:
                    json.dump(ast_data.get('blocks', []), f, indent=4)
            
            # Extract information
            blocks = ast_data.get('blocks', [])
            metadata = ast_data.get('meta', {})
            
            # Get equations (now returns a dict with separate lists)
            equation_results = self.extract_equations(blocks)
            
            result = {
                "title": self.extract_title(blocks, metadata),
                "abstract": self.extract_abstract(blocks),
                "year": self.extract_year(blocks, metadata, tex_file_path),
                "main_text": self.extract_main_text(blocks),
                "citations": self.extract_citations(blocks),
                "display_equations": equation_results.get("equations", []), 
                "inline_equations": equation_results.get("inline_equations", []),
                "tables": self.extract_tables(blocks)
            }
            
            # Clean up
            os.unlink(temp_json)
            return result
            
        except Exception as e:
            self.log(f"Error in AST-based extraction: {str(e)}")
            if os.path.exists(temp_json):
                os.unlink(temp_json)
            return None
    
    def extract_title(self, blocks, metadata=None):
        """Extract title from AST blocks or metadata"""
        # Check metadata first
        if metadata and 'title' in metadata:
            meta_title = metadata.get('title')
            if isinstance(meta_title, dict):
                if meta_title.get('t') == 'MetaInlines':
                    title_blocks = meta_title.get('c', [])
                    return self.extract_text_from_inlines(title_blocks)
            elif isinstance(meta_title, str):
                return meta_title
        
        # # Check blocks for headers level 1 for title
        # for block in blocks:
        #     if block.get('t') == 'Header' and block.get('c', [0])[0] == 1:
        #         header_content = block.get('c', [None, None, []])[2]
        #         return self.extract_text_from_inlines(header_content)
        
        return None
    
    def extract_abstract(self, blocks):
        """Extract abstract from AST blocks"""
        in_abstract = False
        abstract_text = ""
        
        # Look for abstract section
        for block in blocks:
            if block.get('t') == 'Header' and self.extract_text_from_inlines(block.get('c', [None, None, []])[2]).lower() == 'abstract':
                in_abstract = True
                continue
            elif block.get('t') == 'Header' and in_abstract:
                break
            elif in_abstract and block.get('t') in ['Para', 'Plain']:
                abstract_text += self.extract_text_from_inlines(block.get('c', [])) + " "
        
        # Look for abstract environment
        if not abstract_text:
            for i, block in enumerate(blocks):
                if (block.get('t') == 'RawBlock' and 
                    'abstract' in block.get('c', ['', ''])[1].lower()):
                    # Look for following paragraphs
                    for j in range(i+1, min(i+10, len(blocks))):
                        if blocks[j].get('t') in ['Para', 'Plain']:
                            abstract_text += self.extract_text_from_inlines(blocks[j].get('c', [])) + " "
                        elif blocks[j].get('t') == 'Header':
                            break
                    break
        
        return abstract_text.strip() if abstract_text else None
    
    def extract_year(self, blocks, metadata=None, tex_file_path=None):
        """Extract publication year from AST blocks or metadata"""
        # Check for \today in metadata or date field
        if metadata and 'date' in metadata:
            date_text = str(metadata['date'])
            if '\\today' in date_text:
                self.log("Date uses \\today, will require API fallback")
                
                # For arXiv papers, try to extract year from filename
                if tex_file_path:
                    # ArXiv ID pattern: YYMM.NNNN or newer format YYMM.NNNNN
                    # where YY=year, MM=month
                    arxiv_match = re.search(r'(\d{2})(\d{2})\.(\d+)', os.path.basename(tex_file_path))
                    if arxiv_match:
                        year_prefix = arxiv_match.group(1)
                        month = arxiv_match.group(2)
                        # Convert 2-digit year to 4-digit
                        full_year = ""
                        # ArXiv started in 1991, so any year < 91 must be 20xx
                        if int(year_prefix) < 91:
                            full_year = "20" + year_prefix
                        else:
                            full_year = "19" + year_prefix
                        
                        self.log(f"Extracted year {full_year} from arXiv ID {arxiv_match.group(0)}")
                        return full_year
                
                return None
        
        # Check for explicit date fields in metadata
        if metadata:
            # Check for year field directly
            if 'year' in metadata:
                year_text = str(metadata['year'])
                year_match = re.search(r'(19|20)\d{2}', year_text)
                if year_match:
                    return year_match.group(0)
            
            # Check in date field
            if 'date' in metadata:
                date_text = str(metadata['date'])
                year_match = re.search(r'(19|20)\d{2}', date_text)
                if year_match:
                    return year_match.group(0)
        
        # Gather text from blocks excluding address/affiliation sections
        all_text = ""
        in_address = False
        
        for block in blocks:
            # Skip address/affiliation sections
            if block.get('t') == 'RawBlock':
                raw_text = block.get('c', ['', ''])[1]
                if any(pattern in raw_text.lower() for pattern in ['\\address{', '\\affiliation{', '\\institute{', '\\email{', '\\thanks{']):
                    in_address = True
                elif in_address and any(pattern in raw_text.lower() for pattern in ['\\end{', '}']):
                    in_address = False
            
            # Collect text from paragraphs outside address sections
            if not in_address and block.get('t') in ['Para', 'Plain']:
                all_text += self.extract_text_from_inlines(block.get('c', [])) + " "
        
        # Look for publication context years
        pub_contexts = [
            r'(?:received|accepted|published|revised)(?:\s+on)?(?:\s+\w+)?\s+\w+\s+\d{1,2}?\s*,?\s*(19|20)\d{2}',
            r'copyright\s*(?:\(c\)|©)?\s*(19|20)\d{2}',
            r'(?:journal|conference)\s+\w+\s*,?\s*(?:vol\.?|volume)\s*\d+\s*,?\s*(?:no\.?|number)\s*\d+\s*,?\s*(19|20)\d{2}',
        ]
        
        for pattern in pub_contexts:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                year_match = re.search(r'(19|20)\d{2}', match.group(0))
                if year_match:
                    return year_match.group(0)
        
        # Last resort: check for date formats
        date_formats = [
            r'\d{1,2}\s+\w+\s+(19|20)\d{2}',  # "12 January 2022"
            r'\w+\s+\d{1,2}\s*,?\s*(19|20)\d{2}',  # "January 12, 2022"
        ]
        
        for pattern in date_formats:
            match = re.search(pattern, all_text)
            if match:
                for group in match.groups():
                    if group and re.match(r'(19|20)\d{2}', group):
                        return group
                
                # If no explicit group matched, find the year in the matched text
                year_match = re.search(r'(19|20)\d{2}', match.group(0))
                if year_match:
                    return year_match.group(0)
        
        return None
    
    def extract_main_text(self, blocks):
        """Extract main text from AST blocks, excluding non-body content"""
        # For physics papers, extract ALL paragraphs before the bibliography section.
        # Identify the bibliography by looking for a Div block with class "thebibliography".
        text_blocks = []
        in_main_text = True # Start in main text mode

        for block in blocks:
            # Check if this is the bibliography block
            if block.get('t') == 'Div' and block.get('c', [None, None, []])[1] == ["thebibliography"]:
                in_main_text = False # Stop collecting text

            if in_main_text:
                # Collect text from relevant blocks (Paragraphs and Plain text)
                if block.get('t') in ['Para', 'Plain']:
                    text_blocks.append(self.extract_text_from_inlines(block.get('c', [])))
                # Optionally, add other block types if needed (e.g., lists, quotes, etc.)
                # elif block.get('t') == 'BulletList':
                #     text_blocks.append(" ".join([self.extract_text_from_inlines(item) for sublist in block.get('c', []) for item in sublist]))
                # ... add other block types as necessary

        return " ".join(text_blocks)
    
    def extract_citations(self, blocks):
        """Extract citations from AST blocks"""
        citations = []
        
        # Look for bibliography section
        in_bibliography = False
        for i, block in enumerate(blocks):
            if block.get('t') == 'Header':
                header_text = self.extract_text_from_inlines(block.get('c', [None, None, []])[2]).lower()
                if any(word in header_text for word in ['references', 'bibliography']):
                    in_bibliography = True
                    continue
            
            # Process bibliography items
            if in_bibliography and block.get('t') in ['Para', 'Plain']:
                citation_text = self.extract_text_from_inlines(block.get('c', []))
                key_match = re.match(r'^\s*\[([^\]]+)\]|^\s*(\d+)\.', citation_text)
                if key_match:
                    key = key_match.group(1) or key_match.group(2)
                    # Clean up LaTeX commands in the citation text
                    cleaned_text = self.clean_latex_citation(citation_text)
                    citations.append({
                        "key": key,
                        "text": cleaned_text.strip()
                    })
        
        return citations
    
    def clean_latex_citation(self, text):
        """Clean up LaTeX commands in citation text"""
        # Remove citation key and number at the start
        text = re.sub(r'^\s*\[[^\]]+\]\s*|^\s*\d+\.\s*', '', text)
        
        # Replace common LaTeX citation commands
        replacements = [
            (r'\\bibinfo\{[^}]+\}\{([^}]+)\}', r'\1'),  # \bibinfo{field}{text} -> text
            (r'\\bibfnamefont\{([^}]+)\}', r'\1'),      # \bibfnamefont{text} -> text
            (r'\\bibnamefont\{([^}]+)\}', r'\1'),       # \bibnamefont{text} -> text
            (r'\\natexlab\{[^}]+\}', ''),              # Remove \natexlab{...}
            (r'\\textbf\{([^}]+)\}', r'\1'),           # \textbf{text} -> text
            (r'\\textit\{([^}]+)\}', r'\1'),           # \textit{text} -> text
            (r'\\emph\{([^}]+)\}', r'\1'),             # \emph{text} -> text
            (r'\\text\{([^}]+)\}', r'\1'),             # \text{text} -> text
            (r'\\url\{([^}]+)\}', r'\1'),              # \url{text} -> text
            (r'\\href\{[^}]+\}\{([^}]+)\}', r'\1'),    # \href{url}{text} -> text
            (r'\\cite\{[^}]+\}', ''),                  # Remove \cite{...}
            (r'\\citep\{[^}]+\}', ''),                 # Remove \citep{...}
            (r'\\citet\{[^}]+\}', ''),                 # Remove \citet{...}
            (r'\\ref\{[^}]+\}', ''),                   # Remove \ref{...}
            (r'\\label\{[^}]+\}', ''),                 # Remove \label{...}
            (r'\\vspace\{[^}]+\}', ' '),               # Replace \vspace{...} with space
            (r'\\hspace\{[^}]+\}', ' '),               # Replace \hspace{...} with space
            (r'\\newline', ' '),                       # Replace \newline with space
            (r'\\par', ' '),                           # Replace \par with space
            (r'\\[a-zA-Z]+', ''),                      # Remove other LaTeX commands
            (r'\{([^}]+)\}', r'\1'),                   # Remove remaining braces
            (r'\s+', ' '),                             # Normalize whitespace
        ]
        
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)
        
        # Clean up any remaining LaTeX artifacts
        text = text.replace('~', ' ')  # Replace non-breaking spaces
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace again
        text = text.strip()
        
        return text
    
    def extract_equations(self, blocks):
        """Extract equations from AST blocks including inline math"""
        display_equations = []
        inline_equations = []
        
        # Process math in blocks
        for block in blocks:
            # Look for math blocks
            if block.get('t') == 'Para':
                for element in block.get('c', []):
                    if element.get('t') == 'Math' and element.get('c', [{'t': ''}])[0].get('t') == 'DisplayMath':
                        display_equations.append({
                            "latex": element.get('c', [None, ''])[1],
                            "is_display": True,
                            "is_equation": True  # Assume display math is an equation
                        })
                    elif element.get('t') == 'Math' and element.get('c', [{'t': ''}])[0].get('t') == 'InlineMath':
                        # Check if inline math is an equation
                        math_content = element.get('c', [None, ''])[1]
                        is_equation = bool(re.search(r'[=<>]|\\approx|\\sim|\\cong|\\equiv|\\neq|\\ne|\\leq|\\geq', math_content))
                        
                        if is_equation:
                            inline_equations.append({
                                "latex": math_content,
                                "is_display": False,
                                "is_equation": True
                            })
            
            # Also check RawBlock for LaTeX equations
            elif block.get('t') == 'RawBlock' and block.get('c', ['', ''])[0] == 'tex':
                tex = block.get('c', ['', ''])[1]
                
                # Check for display math environments
                env_matches = [
                    (r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', 1),
                    (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', 1),
                    (r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', 1),
                    (r'\\begin\{gather\*?\}(.*?)\\end\{gather\*?\}', 1),
                    (r'\\begin\{aligned\}(.*?)\\end\{aligned\}', 1),
                    (r'\\begin\{array\}.*?\}(.*?)\\end\{array\}', 1),
                    (r'\\begin\{displaymath\}(.*?)\\end\{displaymath\}', 1),
                ]
                
                for pattern, group in env_matches:
                    for match in re.finditer(pattern, tex, re.DOTALL):
                        display_equations.append({
                            "latex": match.group(group).strip(),
                            "is_display": True,
                            "is_equation": True
                        })
                
                # Physics papers also commonly have $$ ... $$ equations
                for match in re.finditer(r'\$\$(.*?)\$\$', tex, re.DOTALL):
                    display_equations.append({
                        "latex": match.group(1).strip(),
                        "is_display": True,
                        "is_equation": True
                    })
                
                # Capture inline math with equation symbols
                for match in re.finditer(r'\$([^$]*?[=<>].*?)\$', tex):
                    inline_equations.append({
                        "latex": match.group(1).strip(),
                        "is_display": False,
                        "is_equation": True
                    })
        
        # Physics papers often have equations wrapped in special environments
        # Do a second pass for complex equations in RawBlocks
        for block in blocks:
            if block.get('t') == 'RawBlock' and block.get('c', ['', ''])[0] == 'tex':
                tex = block.get('c', ['', ''])[1]
                
                # Look for complex aligned equations with & alignment characters
                if '&=' in tex or '\\\\' in tex:
                    # This might be an equation environment not properly captured
                    if not any(env in tex for env in ['\\begin{equation', '\\begin{align', '\\begin{eqnarray}']):
                        # Might be a loose display math environment
                        equation_match = re.search(r'\$(.*?&.*?=.*?)\$', tex, re.DOTALL)
                        if equation_match:
                            display_equations.append({
                                "latex": equation_match.group(1).strip(),
                                "is_display": True,
                                "is_equation": True
                            })
        
        # For AST extraction, we return both display and inline equations
        result = {
            "equations": display_equations[:5] if len(display_equations) > 5 else display_equations,
            "inline_equations": inline_equations[:5] if len(inline_equations) > 5 else inline_equations
        }
        
        return result
    
    def extract_tables(self, blocks):
        """Extract tables from AST blocks"""
        tables = []
        
        for i, block in enumerate(blocks):
            # Look for Table blocks
            if block.get('t') == 'Table':
                caption = self.extract_text_from_inlines(block.get('c', [[], None, None, None, None])[0])
                tables.append({
                    "caption": caption,
                    "content": "Table detected in AST"
                })
            
            # Also check RawBlock for LaTeX tables
            elif block.get('t') == 'RawBlock' and block.get('c', ['', ''])[0] == 'tex':
                tex = block.get('c', ['', ''])[1]
                if '\\begin{table' in tex or '\\begin{tabular' in tex:
                    caption_match = re.search(r'\\caption\{(.*?)\}', tex, re.DOTALL)
                    caption = caption_match.group(1) if caption_match else "Unknown caption"
                    
                    tables.append({
                        "caption": caption,
                        "content": tex
                    })
            
            if tables:
                return [tables[0]]  # Return only first table
        
        return []
    
    def extract_text_from_inlines(self, inlines):
        """Extract plain text from Pandoc AST inline elements"""
        if not inlines:
            return ""
        
        text = ""
        for inline in inlines:
            if isinstance(inline, dict):
                if inline.get('t') == 'Str':
                    text += inline.get('c', '')
                elif inline.get('t') == 'Space':
                    text += ' '
                elif inline.get('t') == 'SoftBreak':
                    text += ' '
                elif inline.get('t') == 'LineBreak':
                    text += '\n'
                elif inline.get('t') in ['Emph', 'Strong']:
                    text += self.extract_text_from_inlines(inline.get('c', []))
                elif inline.get('t') == 'Cite':
                    text += self.extract_text_from_inlines(inline.get('c', [None, []])[1])
                elif inline.get('t') == 'Math':
                    text += f"[MATH: {inline.get('c', [None, ''])[1]}]"
            elif isinstance(inline, list):
                text += self.extract_text_from_inlines(inline)
        
        return text
