#!/usr/bin/env python3
import re
import os

def remove_latex_comments(content):
    """Remove LaTeX comments from the content while preserving all other LaTeX expressions"""
    # Split into lines and process each line
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            cleaned_lines.append(line)
            continue
            
        # Handle escaped percent signs
        line = line.replace('\\%', '__PERCENT__')
        
        # Find comment position
        comment_pos = line.find('%')
        
        # Only remove the comment if % is not escaped
        if comment_pos != -1:
            line = line[:comment_pos]
            
        # Restore escaped percent signs
        line = line.replace('__PERCENT__', '\\%')
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def clean_latex_citation(text):
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

# Dictionary of LaTeX patterns by document class
LATEX_PATTERNS = {
    # Common patterns across formats
    "general": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}',  # \title{...} or \title[short title]{...}
            r'\\def\\thetitle\{(.*?)\}',  # \def\thetitle{...}
            r'\\Title\{(.*?)\}',  # \Title{...}
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',  # \begin{abstract}...\end{abstract}
            r'\\abstract\{(.*?)\}'  # \abstract{...}
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem(?:\s*\[([^\]]*?)\])?\s*\{([^}]*)\}(.*?)(?=\\bibitem|\\end\{thebibliography\}|$)',
            "natbib": r'\\bibliography\{([^}]*)\}',
            "biblatex": r'\\printbibliography(?:\[.*?\])?'
        }
    },
    
    # REVTeX (used by APS journals: Physical Review Letters, Physical Review A-E)
    "revtex4-1": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem(?:\s*\[([^\]]*?)\])?\s*\{([^}]*)\}(.*?)(?=\\bibitem|\\end\{thebibliography\}|$)'
        }
    },
    
    # Add support for REVTeX 4-2 (used by APS journals: Physical Review Letters, Physical Review A-E, etc.)
    "revtex4-2": {
        "title": [
            r'\\title\\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem(?:\s*\[([^\]]*?)\])?\s*\{([^}]*)\}(.*?)(?=\\bibitem|\\end\{thebibliography\}|$)'
        }
    },
    
    # American Institute of Physics
    "aip": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}\{([^}]*)\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # Elsevier journals
    "elsarticle": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
            r'\\abstract\{(.*?)\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}\{([^}]*)\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # IOP Publishing
    "iopart": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
            r'\\abstract\{(.*?)\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # Journal of High Energy Physics
    "JHEP": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\abstract\{(.*?)\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}\{([^}]*)\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # Journal of Cosmology and Astroparticle Physics
    "JCAP": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\abstract\{(.*?)\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}\{([^}]*)\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # SPIE conference format
    "spconf": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # APS style
    "apsrev4-1": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # Springer journals
    "svjour3": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # IEEE journals and conferences
    "ieee": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
            r'\\IEEEabstract\{(.*?)\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}\{([^}]*)\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # Monthly Notices of the Royal Astronomical Society
    "mnras": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\[(.*?)\]\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # arXiv papers often use these formats
    "arxiv": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
            r'\\abstract\{(.*?)\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem(?:\[([^\]]*)\])?\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    },
    
    # American Astronomical Society journals
    "aastex": {
        "title": [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}'
        ],
        "abstract": [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
        ],
        "bibliography": {
            "thebibliography": r'\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}',
            "bibitem": r'\\bibitem\[([^\]]*)\]\{([^}]*)\}(.*?)(?=\\bibitem|\n\\end\{thebibliography\}|$)'
        }
    }
}

def extract_bibliography(content, document_class="general"):
    """
    Extract bibliography items from LaTeX content as key-value pairs
    
    Args:
        content (str): The LaTeX content with comments removed
        document_class (str): The LaTeX document class or format
    
    Returns:
        list: List of dictionaries with keys 'key', 'label' (optional), and 'text'
    """
    content = remove_latex_comments(content)
    print("document_class", document_class)
    # Get patterns for the specified document class, fall back to general if not found
    patterns = LATEX_PATTERNS.get(document_class, LATEX_PATTERNS["general"])
    bib_patterns = patterns["bibliography"]
    # print("bib_patterns", bib_patterns)
    # First, find the bibliography section
    bib_section = ""
    thebib_match = re.search(bib_patterns["thebibliography"], content, re.DOTALL)
    
    if thebib_match:
        bib_section = thebib_match.group(1)
    else:
        # Check for BibTeX/BibLaTeX usage
        if "natbib" in bib_patterns and re.search(bib_patterns["natbib"], content):
            return [{"key": "external", "text": "Bibliography uses BibTeX with external .bib file(s)"}]
        if "biblatex" in bib_patterns and re.search(bib_patterns["biblatex"], content):
            return [{"key": "external", "text": "Bibliography uses BibLaTeX with external .bib file(s)"}]
        return []
    # print("bib_section", bib_section)
    # Now extract individual bibliography items
    bib_items = []
    
    bibitem_pattern = bib_patterns["bibitem"]
    # print("bibitem_pattern", bibitem_pattern)
    for match in re.finditer(bibitem_pattern, bib_section, re.DOTALL):
        if len(match.groups()) == 3:  # Pattern with label
            label, key, text = match.groups()
            bib_items.append({
                "key": key.strip(),
                "label": label.strip() if label else None,
                "text": clean_latex_citation(text.strip())
            })
        elif len(match.groups()) == 2:  # Pattern without label
            key, text = match.groups()
            bib_items.append({
                "key": key.strip(),
                "text": clean_latex_citation(text.strip())
            })
    
    return bib_items

def detect_document_class(content):
    """
    Detect the document class from LaTeX content
    
    Args:
        content (str): The LaTeX content with comments removed
    
    Returns:
        str: Detected document class
    """
    doc_class_match = re.search(r'\\documentclass(?:\[.*?\])?\{([^}]*)\}', content)
    document_class = "general"
    if doc_class_match:
        # The class name is always inside the curly braces, e.g. {revtex4-2}
        class_name = doc_class_match.group(1).strip()
        print("class_name", class_name)
        # Use the full class name for matching (do not split on commas)
        if class_name in LATEX_PATTERNS:
            document_class = class_name
        elif class_name.startswith("revtex4-2"):
            document_class = "revtex4-2"
        elif class_name.startswith("revtex"):
            document_class = "revtex4-1"
    return document_class

def extract_title(content, document_class="general"):
    """
    Extract the title from LaTeX content
    
    Args:
        content (str): The LaTeX content with comments removed
        document_class (str): The LaTeX document class or format
    
    Returns:
        str: Extracted title or None if not found
    """
    patterns = LATEX_PATTERNS.get(document_class, LATEX_PATTERNS["general"])
    
    for title_pattern in patterns["title"]:
        title_match = re.search(title_pattern, content, re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
    
    return None

def extract_abstract(content, document_class="general"):
    """
    Extract the abstract from LaTeX content
    
    Args:
        content (str): The LaTeX content with comments removed
        document_class (str): The LaTeX document class or format
    
    Returns:
        str: Extracted abstract or None if not found
    """
    patterns = LATEX_PATTERNS.get(document_class, LATEX_PATTERNS["general"])
    
    for abstract_pattern in patterns["abstract"]:
        abstract_match = re.search(abstract_pattern, content, re.DOTALL)
        if abstract_match:
            return abstract_match.group(1).strip()
    
    return None

def extract_document_structure(tex_content_or_file):
    """
    Extract structured information from LaTeX content or file
    
    Args:
        tex_content_or_file (str): LaTeX content or file path
    
    Returns:
        dict: Dictionary with title, abstract, document_class, and bibliography
    """
    # Check if input is a file path or content
    if os.path.exists(tex_content_or_file):
        with open(tex_content_or_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = tex_content_or_file
    print("I ran")
    # Remove comments
    content = remove_latex_comments(content)
    
    # Detect document class
    document_class = detect_document_class(content)
    
    # Extract title
    title = extract_title(content, document_class)
    
    # Extract abstract
    abstract = extract_abstract(content, document_class)
    
    # Extract bibliography
    bibliography = extract_bibliography(content, document_class)
    
    return {
        "document_class": document_class,
        "title": title,
        "abstract": abstract,
        "bibliography": bibliography
    }

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python latex_patterns.py <tex_file_path> [output_json_path]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    result = extract_document_structure(input_file)
    
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Extracted data saved to: {output_file}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False)) 