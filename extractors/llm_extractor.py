#!/usr/bin/env python3
"""Extractor using LangChain agents for LaTeX extraction"""
import os
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
import json
import re
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain_community.callbacks import get_openai_callback
from pydantic import BaseModel, Field, PrivateAttr

from extractors.ast_extractor import AstExtractor
from extractors.pattern_extractor import PatternExtractor
from .base_extractor import BaseExtractor
from .examples import FEW_SHOT_EXAMPLES

# Load environment variables from .env file
load_dotenv()

class LaTeXExtractionTool(BaseTool):
    """Tool for extracting information from LaTeX content"""
    
    name: str = "latex_extraction"
    description: str = "Extract information from LaTeX content"
    llm: ChatOpenAI = Field(default=None)
    field: str = Field(default="")
    format_instructions: str = Field(default="")
    _prompt: Any = PrivateAttr()
    _chain: Any = PrivateAttr()
    verbose: bool = False
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, llm: ChatOpenAI, field: str, format_instructions: str):
        """Initialize the tool with LLM and field-specific instructions"""
        super().__init__()
        self.llm = llm
        self.field = field
        self.format_instructions = format_instructions
        
        # Create the prompt template with examples
        self._prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a LaTeX paper information extractor. Your task is to extract specific information from LaTeX content and return it in valid JSON format.

IMPORTANT RULES:
1. ALWAYS return valid JSON
2. DO NOT include any explanatory text
3. DO NOT include the field name in the output
4. DO NOT use markdown formatting
5. DO NOT include any extra text or comments

Example outputs for different fields:
- For title: "The Title of the Paper"
- For abstract: "This is the abstract text..."
- For year: "2024"
- For main_text_sample: {"first_500": "First 500 chars...", "last_500": "Last 500 chars..."}
- For citations: [{"key": "cite1", "text": "Citation text..."}]
- For equations: [{"latex": "E = mc^2", "is_display": true}]
- For tables: [{"caption": "Table caption", "content": "Table content..."}]

Remember: Your response must be valid JSON that can be parsed by json.loads()."""),
            MessagesPlaceholder(variable_name="context"),
            HumanMessage(content=f"""Task: Extract the {field} from the context above.

Your response must be in the following format:
{format_instructions}

Remember: Return ONLY the JSON value, no other text or formatting.""")
        ])
        
        # Create the chain
        self._chain = (
            {"context": RunnablePassthrough(), "field": lambda _: self.field, "format_instructions": lambda _: self.format_instructions}
            | self._prompt
            | self.llm
            | StrOutputParser()
        )
    
    def _run(self, context: str) -> str:
        """Run the tool with the given context"""
        try:
            with get_openai_callback() as cb:
                # Wrap context in a list of HumanMessage
                result = self._chain.invoke([HumanMessage(content=context)])
                if self.verbose:
                    print(f"Total Tokens: {cb.total_tokens}")
                    print(f"Prompt Tokens: {cb.prompt_tokens}")
                    print(f"Completion Tokens: {cb.completion_tokens}")
                    print(f"Total Cost (USD): ${cb.total_cost}")
            return result
        except Exception as e:
            print(f"Error in {self.field} extraction: {str(e)}")
            return ""
    
    async def _arun(self, context: str) -> str:
        """Run the tool asynchronously"""
        return self._run(context)

class FormattingAgent:
    """Agent that fixes malformed JSON outputs from LLM"""
    
    def __init__(self, llm: ChatOpenAI, verbose: bool):
        """Initialize the formatting agent with LLM"""
        self.llm = llm
        self.verbose = verbose
        self._prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a JSON formatting specialist. Your task is to fix malformed JSON outputs and ensure they match the required format.

IMPORTANT RULES:
1. ALWAYS return valid JSON
2. DO NOT include any explanatory text
3. DO NOT include the field name in the output
4. DO NOT use markdown formatting
5. DO NOT include any extra text or comments
6. Preserve all LaTeX expressions exactly as they appear
7. Fix only the JSON structure, not the content

Example formats for different fields:
- For title: "The Title of the Paper"
- For abstract: "This is the abstract text..."
- For year: "2024"
- For main_text_sample: {"first_500": "First 500 chars...", "last_500": "Last 500 chars..."}
- For citations: [{"key": "cite1", "text": "Citation text..."}]
- For equations: [{"latex": "E = mc^2", "is_display": true}]
- For tables: [{"caption": "Table caption", "content": "Table content..."}]

Remember: Your response must be valid JSON that can be parsed by json.loads()."""),
            MessagesPlaceholder(variable_name="context"),
            HumanMessage(content="""Task: Fix the malformed JSON output to match the required format.

Field: {field}
Required Format: {format_instructions}
Error: {error}
Raw Output: {raw_output}

Remember: Return ONLY the fixed JSON value, no other text or formatting.""")
        ])
        
        # Create the chain
        self._chain = (
            {"context": RunnablePassthrough(), "field": lambda x: x["field"], 
             "format_instructions": lambda x: x["format_instructions"],
             "error": lambda x: x["error"],
             "raw_output": lambda x: x["raw_output"]}
            | self._prompt
            | self.llm
            | StrOutputParser()
        )
    
    def fix_output(self, field: str, format_instructions: str, error: str, raw_output: str) -> str:
        """Fix malformed JSON output"""
        try:
            with get_openai_callback() as cb:
                result = self._chain.invoke({
                    "field": field,
                    "format_instructions": format_instructions,
                    "error": error,
                    "raw_output": raw_output
                })
                if self.verbose:
                    print(f"Formatting Agent - Total Tokens: {cb.total_tokens}")
                    print(f"Formatting Agent - Total Cost (USD): ${cb.total_cost}")
            return result
        except Exception as e:
            print(f"Error in formatting agent: {str(e)}")
            return raw_output

class LaTeXExtractor:
    """Extract information from LaTeX using LangChain"""
    
    def __init__(self, openai_api_key: Optional[str] = None, model_name: str = "gpt-4o-mini", verbose: bool = False):
        """Initialize the extractor with OpenAI API key and model name"""
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided")
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.1,
            api_key=api_key
        )
        self.preprocessor = LaTeXPreprocessor()
        self.formatting_agent = FormattingAgent(self.llm, verbose)
        
        # Define format instructions for each field
        self.format_instructions = {
            "title": "Return the title as a string. Respond with only valid JSON. Do not include any extra text or explanation.",
            "abstract": "Return the abstract as a string. The response should be a single string, not an object or array. Example: \"This is the abstract text...\"",
            "year": "Return the publication year as a string. Respond with only valid JSON. Do not include any extra text or explanation.",
            "main_text_sample": "Return a string containing the first and last 500 characters of the main text, separated by newlines. Respond with only valid JSON. Do not include any extra text or explanation.",
            "citations": "Return a list of citation objects, each with 'key' and 'text' fields. Respond with only valid JSON. Do not include any extra text or explanation.",
            "display_equations": "Return a list of equation objects, each with 'latex' and 'is_display' fields. Respond with only valid JSON. Do not include any extra text or explanation.",
            "inline_equations": "Return a list of equation objects, each with 'latex' and 'is_display' fields. Respond with only valid JSON. Do not include any extra text or explanation.",
            "tables": "Return a list of table objects, each with 'caption' and 'content' fields. Respond with only valid JSON. Do not include any extra text or explanation."
        }
        
        # Initialize tools for each field
        self.tools = {
            field: LaTeXExtractionTool(
                self.llm,
                field,
                format_instructions
            )
            for field, format_instructions in self.format_instructions.items()
        }
    
    def safe_json_loads(self, text: str, default: Any) -> Any:
        """Safely parse JSON string with error handling"""
        if not text:
            return default
        
        try:
            # First clean LaTeX escape sequences
            cleaned_text = self.clean_latex_escapes(text)
            
            # Try to parse the cleaned text
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                # If first attempt fails, try to fix common JSON issues
                fixed_text = cleaned_text
                # Fix unescaped quotes in strings
                fixed_text = re.sub(r'(?<!\\)"([^"]*?)(?<!\\)"', r'"\1"', fixed_text)
                # Fix missing quotes around keys
                fixed_text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed_text)
                # Fix trailing commas
                fixed_text = re.sub(r',\s*}', '}', fixed_text)
                fixed_text = re.sub(r',\s*]', ']', fixed_text)
                
                try:
                    return json.loads(fixed_text)
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for field. Raw output:\n{text}")
                    print(f"Cleaned output:\n{cleaned_text}")
                    print(f"Fixed output:\n{fixed_text}")
                    print(f"Error: {str(e)}")
                    return default
        except Exception as e:
            print(f"Unexpected error in JSON parsing: {str(e)}")
            return default
    
    def clean_latex_escapes(self, obj):
        """Recursively clean LaTeX escape sequences from strings in dicts/lists/strings."""
        if isinstance(obj, str):
            # First handle LaTeX commands that should be preserved
            preserved_commands = {
                r'\\begin\{([^}]+)\}': r'\\begin{\1}',
                r'\\end\{([^}]+)\}': r'\\end{\1}',
                r'\\[a-zA-Z]+(?:\[[^]]*\])?(?:\{[^}]*\})?': r'\\\0'  # Preserve LaTeX commands
            }
            
            for pattern, replacement in preserved_commands.items():
                obj = re.sub(pattern, replacement, obj)
            
            # Handle LaTeX escape sequences
            replacements = {
                '\\"': '"', '\\\'': "'", '\\`': '`', '\\^': '^', '\\~': '~',
                '\\c': 'c', '\\k': 'k', '\\l': 'l', '\\=': '=', '\\.': '.',
                '\\u': 'u', '\\v': 'v', '\\H': 'H', '\\t': 't', '\\r': 'r',
                '\\b': 'b', '\\d': 'd', '\\%': '%', '\\&': '&', '\\$': '$',
                '\\#': '#', '\\_': '_', '\\{': '{', '\\}': '}', '\\\\': '\\',
                '\\textbackslash': '\\', '\\textasciitilde': '~',
                '\\textasciicircum': '^', '\\textquotedblleft': '"',
                '\\textquotedblright': '"', '\\textquotesingle': "'",
                '\\textemdash': '—', '\\textendash': '–', '\\textbullet': '•',
                '\\textregistered': '®', '\\textcopyright': '©',
                '\\texttrademark': '™', '\\textdegree': '°', '\\textmu': 'μ',
                '\\textohm': 'Ω', '\\textcelsius': '°C', '\\textfahrenheit': '°F',
                '\\textperthousand': '‰', '\\textpertenthousand': '‱',
                '\\textonehalf': '½', '\\textonequarter': '¼',
                '\\textthreequarters': '¾', '\\textoneeighth': '⅛',
                '\\textthreeeighths': '⅜', '\\textfiveeighths': '⅝',
                '\\textseveneighths': '⅞'
            }
            
            for latex, unicode in replacements.items():
                obj = obj.replace(latex, unicode)
            
            # Handle LaTeX commands with arguments
            obj = re.sub(r'\\[a-zA-Z]+{([^}]*)}', r'\1', obj)
            
            # Handle remaining LaTeX commands
            obj = re.sub(r'\\[^a-zA-Z]', '', obj)
            
            # Handle special LaTeX spacing commands
            obj = re.sub(r'\\[hv]space\*?\{[^}]*\}', ' ', obj)
            obj = re.sub(r'\\[hv]fill', ' ', obj)
            
            # Handle LaTeX quotes
            obj = re.sub(r'``', '"', obj)
            obj = re.sub(r"''", '"', obj)
            
            # Handle LaTeX dashes
            obj = re.sub(r'--', '–', obj)
            obj = re.sub(r'---', '—', obj)
            
            # Normalize whitespace
            obj = re.sub(r'\s+', ' ', obj)
            obj = obj.strip()
            
            return obj
        elif isinstance(obj, dict):
            return {k: self.clean_latex_escapes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.clean_latex_escapes(x) for x in obj]
        else:
            return obj

    def _format_llm_output(self, output, field: str, format_instructions: str):
        """Format LLM output and handle JSON parsing errors"""
        try:
            # First attempt to parse the output directly
            return json.loads(output)
        except json.JSONDecodeError as e:
            try:
                # Try to fix common JSON formatting issues
                # Replace unescaped quotes in LaTeX expressions
                fixed_output = re.sub(r'(?<!\\)"([^"]*?\\[^"]*?)"', r'"\1"', output)
                # Fix unescaped backslashes
                fixed_output = fixed_output.replace('\\', '\\\\')
                # Try parsing again
                return json.loads(fixed_output)
            except json.JSONDecodeError:
                # If still fails, use the formatting agent
                formatted_output = self.formatting_agent.fix_output(
                    field=field,
                    format_instructions=format_instructions,
                    error=str(e),
                    raw_output=output
                )
                try:
                    return json.loads(formatted_output)
                except json.JSONDecodeError:
                    # If formatting agent fails, return error info and raw output
                    return {
                        "error": {
                            "type": "JSONDecodeError",
                            "message": str(e),
                            "position": e.pos,
                            "line": e.lineno,
                            "column": e.colno
                        },
                        "raw_output": output,
                        "formatted_output": formatted_output
                    }

    def extract_from_content(self, content: str) -> Dict:
        """Extract information from LaTeX content"""
        # Preprocess content for each field
        title_context = self.preprocessor.preprocess_for_title(content)
        abstract_context = self.preprocessor.preprocess_for_abstract(content)
        year_context = self.preprocessor.preprocess_for_year(content)
        main_text_context = self.preprocessor.preprocess_for_main_text(content)
        citations_context = self.preprocessor.preprocess_for_citations(content)
        equations_context = self.preprocessor.preprocess_for_equations(content)
        tables_context = self.preprocessor.preprocess_for_tables(content)
        
        # Extract information using LLM
        result = {
            "title": self.clean_latex_escapes(self._format_llm_output(
                self.tools["title"]._run(title_context or content),
                "title",
                self.format_instructions["title"]
            )),
            "abstract": str(self.clean_latex_escapes(self._format_llm_output(
                self.tools["abstract"]._run(abstract_context or content),
                "abstract",
                self.format_instructions["abstract"]
            ))),
            "year": self.clean_latex_escapes(self._format_llm_output(
                self.tools["year"]._run(year_context or content),
                "year",
                self.format_instructions["year"]
            )),
            "main_text_sample": self.clean_latex_escapes(self._format_llm_output(
                self.tools["main_text_sample"]._run(main_text_context or content),
                "main_text_sample",
                self.format_instructions["main_text_sample"]
            )),
            "citations": [{"key": self.clean_latex_escapes(c["key"]), "text": self.clean_latex_escapes(c["text"])} 
                         for c in self._format_llm_output(
                             self.tools["citations"]._run(citations_context or content),
                             "citations",
                             self.format_instructions["citations"]
                         )],
            "display_equations": [{"latex": self.clean_latex_escapes(eq["latex"]), "is_display": eq["is_display"]} 
                                for eq in self._format_llm_output(
                                    self.tools["display_equations"]._run(equations_context or content),
                                    "display_equations",
                                    self.format_instructions["display_equations"]
                                )],
            "inline_equations": [{"latex": self.clean_latex_escapes(eq["latex"]), "is_display": eq["is_display"]} 
                               for eq in self._format_llm_output(
                                   self.tools["inline_equations"]._run(equations_context or content),
                                   "inline_equations",
                                   self.format_instructions["inline_equations"]
                               )],
            "tables": [{"caption": self.clean_latex_escapes(t["caption"]), "content": self.clean_latex_escapes(t["content"])} 
                      for t in self._format_llm_output(
                          self.tools["tables"]._run(tables_context or content),
                          "tables",
                          self.format_instructions["tables"]
                      )]
        }
        
        return result

class LaTeXPreprocessor:
    """Preprocess LaTeX content to provide focused context for LLM extraction"""
    
    def __init__(self):
        self.pattern_extractor = PatternExtractor()
        self.ast_extractor = AstExtractor()
    
    def preprocess_for_title(self, content):
        """Extract title-specific context following specific steps"""
        # Step 1: Look for exact title tag or similar
        title_patterns = [
            r'\\title\s*(?:\[.*?\])?\{(.*?)\}',
            r'\\def\\thetitle\{(.*?)\}',
            r'\\Title\{(.*?)\}'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return f"Title: {match.group(1).strip()}"
        
        # If no title tag found, get content before \maketitle
        maketitle_match = re.search(r'(.*?)\\maketitle', content, re.DOTALL)
        if maketitle_match:
            return f"Title context: {maketitle_match.group(1).strip()}"
        
        return None
    
    def preprocess_for_main_text(self, content):
        """Extract main text context following specific steps"""
        # Step 2: Use pattern_extractor's extract_main_text
        main_text = self.pattern_extractor.extract_main_text(content)
        
        if main_text and len(main_text) >= 1000:
            return f"First 500 characters: {main_text[:500]}\n\nLast 500 characters: {main_text[-500:]}"
        elif main_text:
            # If text is shorter than 1000 chars, split it in half
            mid = len(main_text) // 2
            return f"First half: {main_text[:mid]}\n\nSecond half: {main_text[mid:]}"
        
        # If empty, return empty string
        return ""
    
    def preprocess_for_abstract(self, content):
        """Extract abstract context following specific steps"""
        # Step 3: Look for abstract tag or variants
        abstract_patterns = [
            r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
            r'\\abstract\{(.*?)\}',
            r'\\begin\{abstract\*?\}(.*?)\\end\{abstract\*?\}'
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return f"Abstract: {match.group(1).strip()}"
        
        # If no abstract tag found, get content above first section
        first_section_match = re.search(r'(.*?)\\section\{', content, re.DOTALL)
        if first_section_match:
            return f"Pre-section content: {first_section_match.group(1).strip()}"
        
        # If both above fail, get first 100 lines
        lines = content.split('\n')
        first_hundred = '\n'.join(lines[:100])
        return f"First 100 lines: {first_hundred}"
    
    def preprocess_for_citations(self, content):
        """Extract citation context following specific steps"""
        # Step 4: Look for bibliography tag and variants
        bib_patterns = [
            r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',
            r'\\begin\{references\}.*?\\end\{references\}',
            r'\\bibliography\{.*?\}',
            r'\\printbibliography'
        ]
        
        # First try to find bibliography section
        for pattern in bib_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                bib_section = match.group(0)
                
                # Clean up LaTeX escape sequences
                cleaned_bib = bib_section.replace('\\\'', "'")  # Handle accented characters
                cleaned_bib = cleaned_bib.replace('\\"', '"')   # Handle umlauts
                cleaned_bib = cleaned_bib.replace('\\`', '`')   # Handle grave accents
                cleaned_bib = cleaned_bib.replace('\\^', '^')   # Handle circumflex
                cleaned_bib = cleaned_bib.replace('\\~', '~')   # Handle tilde
                cleaned_bib = cleaned_bib.replace('\\c', 'c')   # Handle cedilla
                cleaned_bib = cleaned_bib.replace('\\k', 'k')   # Handle ogonek
                cleaned_bib = cleaned_bib.replace('\\l', 'l')   # Handle stroke
                cleaned_bib = cleaned_bib.replace('\\=', '=')   # Handle macron
                cleaned_bib = cleaned_bib.replace('\\.', '.')   # Handle dot
                cleaned_bib = cleaned_bib.replace('\\u', 'u')   # Handle breve
                cleaned_bib = cleaned_bib.replace('\\v', 'v')   # Handle caron
                cleaned_bib = cleaned_bib.replace('\\H', 'H')   # Handle double acute
                cleaned_bib = cleaned_bib.replace('\\t', 't')   # Handle tie
                cleaned_bib = cleaned_bib.replace('\\r', 'r')   # Handle ring
                cleaned_bib = cleaned_bib.replace('\\b', 'b')   # Handle bar
                cleaned_bib = cleaned_bib.replace('\\d', 'd')   # Handle dot under
                
                # Extract individual citations
                citations = []
                for bibitem in re.finditer(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|$)', cleaned_bib, re.DOTALL):
                    key = bibitem.group(1)
                    text = bibitem.group(2).strip()
                    citations.append({
                        "key": key,
                        "text": text
                    })
                
                if citations:
                    return f"Citations:\n" + "\n".join([f"{c['key']}: {c['text']}" for c in citations])
                
                return f"Bibliography section: {cleaned_bib}"
        
        # If no bibliography found, look for \cite commands
        cite_pattern = r'\\cite\{([^}]+)\}'
        cites = re.findall(cite_pattern, content)
        if cites:
            return f"Citation keys found: {', '.join(cites)}"
        
        # If no citations found, return last 100 lines
        lines = content.split('\n')
        last_hundred = '\n'.join(lines[-100:])
        return f"Last 100 lines: {last_hundred}"
    
    def preprocess_for_equations(self, content):
        """Extract equation context following specific steps"""
        # Step 5: Look for equation tags in main text
        display_eq_patterns = [
            (r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', True),  # Always an equation
            (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', True),
            (r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', True),
            (r'\\begin\{displaymath\}(.*?)\\end\{displaymath\}', True),
            (r'\$\$(.*?)\$\$', True),  # Display math is usually an equation
            (r'\\\[(.*?)\\\]', True)
        ]
        
        inline_eq_patterns = [
            (r'\$(.*?)\$', False)
        ]
        
        display_equations = []
        inline_equations = []
        
        # Extract display equations
        for pattern, is_display in display_eq_patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                if len(display_equations) < 5:
                    display_equations.append({
                        "latex": match.group(1).strip(),
                        "is_display": is_display
                    })
        
        # Extract inline equations
        for pattern, is_display in inline_eq_patterns:
            for match in re.finditer(pattern, content):
                if len(inline_equations) < 5:
                    inline_equations.append({
                        "latex": match.group(1).strip(),
                        "is_display": is_display
                    })
        
        if display_equations or inline_equations:
            equation_texts = []
            for eq in display_equations:
                equation_texts.append(f"Display equation: {eq['latex']}")
            for eq in inline_equations:
                equation_texts.append(f"Inline equation: {eq['latex']}")
            return "Equations:\n" + "\n".join(equation_texts)
        
        # If no equations found, return main text without figures and tables
        cleaned_content = re.sub(r'\\begin\{figure\}.*?\\end\{figure\}', '', content, flags=re.DOTALL)
        cleaned_content = re.sub(r'\\begin\{table\}.*?\\end\{table\}', '', cleaned_content, flags=re.DOTALL)
        return f"Main text without figures/tables: {cleaned_content}"
    
    def preprocess_for_tables(self, content):
        """Extract table context following specific steps"""
        # Step 6: Look for table tags
        table_patterns = [
            r'\\begin\{table\*?\}(.*?)\\end\{table\*?\}',
            r'\\begin\{tabular\}(.*?)\\end\{tabular\}',
            r'\\begin\{array\}(.*?)\\end\{array\}',
            r'\\begin\{tabular\*?\}(.*?)\\end\{tabular\*?\}'
        ]
        
        for pattern in table_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                table_content = match.group(0)
                
                # Extract caption
                caption_match = re.search(r'\\caption\{(.*?)\}', table_content, re.DOTALL)
                caption = caption_match.group(1) if caption_match else "Unknown caption"
                
                # Return simple format for LLM
                return f"Table caption: {caption}\nTable content: {table_content}"
        
        return None

    def preprocess_for_year(self, content):
        """Extract year-specific context following specific steps"""
        # Look for year in specific publication contexts
        publication_patterns = [
            r'(?:received|accepted|published|revised)(?:\s+on)?(?:\s+\w+)?\s+\w+\s+\d{1,2}?\s*,?\s*(19|20)\d{2}',
            r'copyright\s*(?:\(c\)|©)?\s*(19|20)\d{2}',
            r'(?:journal|conference)\s+\w+\s*,?\s*(?:vol\.?|volume)\s*\d+\s*,?\s*(?:no\.?|number)\s*\d+\s*,?\s*(19|20)\d{2}'
        ]
        
        for pattern in publication_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                year_match = re.search(r'(19|20)\d{2}', match.group(0))
                if year_match:
                    return f"Year context: {match.group(0)}"
        
        # Look for year in standard LaTeX commands
        date_patterns = [
            r'\\date\{.*?((?:19|20)\d{2}).*?\}',  # \date{...2023...}
            r'\\year\{((?:19|20)\d{2})\}',        # \year{2023}
            r'\\copyright\{((?:19|20)\d{2})\}'    # \copyright{2023}
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                return f"Year command: {match.group(0)}"
        
        # If no specific year context found, return content before first section
        first_section_match = re.search(r'(.*?)\\section\{', content, re.DOTALL)
        if first_section_match:
            return f"Pre-section content: {first_section_match.group(1).strip()}"
        
        return None

def structured_output_match(example, prediction, trace=None):
    """Custom metric for evaluating structured outputs"""
    score = 0
    total_fields = 0
    
    # Compare each field
    for field in ['title', 'abstract', 'year']:
        if getattr(example, field, None) == getattr(prediction, field, None):
            score += 1
        total_fields += 1
    
    # Compare main text
    if (example.main_text_sample.get("first_500") == prediction.main_text_sample.get("first_500") and 
        example.main_text_sample.get("last_500") == prediction.main_text_sample.get("last_500")):
        score += 1
    total_fields += 1
    
    # Compare citations
    if len(example.citations) == len(prediction.citations):
        citations_match = all(
            ex.get("key") == pred.get("key") and ex.get("text") == pred.get("text")
            for ex, pred in zip(example.citations, prediction.citations)
        )
        if citations_match:
            score += 1
    total_fields += 1
    
    # Compare display equations
    if len(example.display_equations) == len(prediction.display_equations):
        display_eq_match = all(
            ex.get("latex") == pred.get("latex")
            for ex, pred in zip(example.display_equations, prediction.display_equations)
        )
        if display_eq_match:
            score += 1
    total_fields += 1
    
    # Compare inline equations
    if len(example.inline_equations) == len(prediction.inline_equations):
        inline_eq_match = all(
            ex.get("latex") == pred.get("latex")
            for ex, pred in zip(example.inline_equations, prediction.inline_equations)
        )
        if inline_eq_match:
            score += 1
    total_fields += 1
    
    # Compare tables
    if len(example.tables) == len(prediction.tables):
        tables_match = all(
            ex.get("caption") == pred.get("caption") and 
            ex.get("content") == pred.get("content")
            for ex, pred in zip(example.tables, prediction.tables)
        )
        if tables_match:
            score += 1
    total_fields += 1
    
    return score / total_fields 