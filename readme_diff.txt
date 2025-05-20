commit 87ee1d2096624347b63cdad8b4b55c7fa3c6c52e
Author: gurnameh singh <27gur@Mac.lan>
Date:   Tue May 20 00:23:24 2025 -0400

    final update

diff --git a/README.md b/README.md
new file mode 100644
index 0000000..60cec74
--- /dev/null
+++ b/README.md
@@ -0,0 +1,229 @@
+# LaTeX Document Extraction System
+
+A comprehensive system for extracting structured information from LaTeX documents using multiple extraction methods.
+
+## Overview
+
+This system provides a flexible and robust way to extract various elements from LaTeX documents, including:
+- Title
+- Abstract
+- Publication Year
+- Main Text
+- Citations
+- Equations (both display and inline)
+- Tables
+
+The extraction is performed using three different methods, which can be used individually or in combination:
+1. AST-based extraction (fastest, most structured)
+2. Pattern-based extraction (medium speed, regex-based)
+3. LLM-based extraction (most flexible, but slower)
+
+## Installation
+
+1. Clone the repository:
+```bash
+git clone <repository-url>
+cd latex_extract
+```
+
+2. Create and activate a virtual environment:
+```bash
+python -m venv env
+source env/bin/activate  # On Windows: env\Scripts\activate
+```
+
+3. Install dependencies:
+```bash
+pip install -r requirements.txt
+```
+
+4. Set up environment variables:
+Create a `.env` file with your OpenAI API key (required for LLM extraction):
+```
+OPENAI_API_KEY=your_api_key_here
+```
+
+## Usage
+
+### Basic Usage
+
+The main script `extract_with_method.py` allows you to extract information from LaTeX files using different methods:
+
+```bash
+python extract_with_method.py input.tex -m [method] -o output.json
+```
+
+Where:
+- `input.tex` is your LaTeX file
+- `method` is one of:
+  - `ast`: AST-based extraction
+  - `pattern`: Pattern-based extraction
+  - `llm`: LLM-based extraction
+  - `all`: Use all methods in sequence (default)
+
+### Command Line Options
+
+```bash
+python extract_with_method.py --help
+```
+
+Options:
+- `-m, --method`: Extraction method to use (ast, pattern, llm, or all)
+- `-o, --output`: Output JSON file path
+- `-f, --format`: Format for equation conversion (mathml or sympy)
+- `-v, --verbose`: Enable verbose output
+
+### Example Commands
+
+1. Extract using AST method:
+```bash
+python extract_with_method.py paper.tex -m ast -o results/ast_output.json
+```
+
+2. Extract using pattern matching:
+```bash
+python extract_with_method.py paper.tex -m pattern -o results/pattern_output.json
+```
+
+3. Extract using LLM:
+```bash
+python extract_with_method.py paper.tex -m llm -o results/llm_output.json
+```
+
+4. Extract using all methods (fallback approach):
+```bash
+python extract_with_method.py paper.tex -m all -o results/complete_output.json
+```
+
+## Extraction Methods
+
+### 1. AST-based Extraction
+- Uses Pandoc to convert LaTeX to an Abstract Syntax Tree (AST)
+- Fastest method
+- Most structured and reliable for well-formatted documents
+- Best for extracting equations and tables
+
+### 2. Pattern-based Extraction
+- Uses regular expressions to identify document elements
+- Medium speed
+- Good for extracting citations and basic document structure
+- Works well with less structured documents
+
+### 3. LLM-based Extraction
+- Uses OpenAI's language models for extraction
+- Most flexible and capable of handling complex cases
+- Slower and requires API key
+- Best used as a fallback when other methods fail
+
+## Output Format
+
+The extraction results are saved in JSON format with the following structure:
+
+```json
+{
+    "title": "Paper Title",
+    "abstract": "Abstract text...",
+    "year": "2024",
+    "main_text_sample": {
+        "first_500": "First 500 characters...",
+        "last_500": "Last 500 characters..."
+    },
+    "citations": [
+        {
+            "key": "citation_key",
+            "text": "Citation text..."
+        }
+    ],
+    "display_equations": [
+        {
+            "latex": "\\frac{dx}{dt}",
+            "mathml": "<math>...</math>",
+            "is_display": true
+        }
+    ],
+    "inline_equations": [
+        {
+            "latex": "E = mc^2",
+            "mathml": "<math>...</math>",
+            "is_display": false
+        }
+    ],
+    "tables": [
+        {
+            "content": "\\begin{tabular}...",
+            "structured_format": {
+                "column_spec": "{ll}",
+                "column_count": 2,
+                "rows": [["Header 1", "Header 2"], ["Data 1", "Data 2"]]
+            }
+        }
+    ],
+    "extraction_method": {
+        "title": "ast",
+        "abstract": "pattern",
+        "year": "llm",
+        "main_text": "ast",
+        "citations": "pattern",
+        "display_equations": "ast",
+        "inline_equations": "ast",
+        "tables": "ast"
+    }
+}
+```
+
+## Testing
+
+Run the test suite:
+```bash
+python -m unittest discover tests
+```
+
+Or run a specific test file:
+```bash
+python -m unittest tests/test_extraction_tester.py
+```
+
+The test suite covers:
+- Extraction from well-formed LaTeX documents (including title, author, sections, equations, tables, citations, and more)
+- Extraction from documents with complex structures (multiple sections, environments, figures, tables, bibliography)
+- Robust handling of malformed or invalid LaTeX input (missing document class, unclosed environments, invalid commands, missing braces, empty files, and non-LaTeX content)
+- Summary generation and error reporting
+
+### Error Handling for Malformed LaTeX
+
+If a LaTeX file is malformed or cannot be processed, the extraction system will:
+- Mark the extraction as unsuccessful (`success: false` in the summary)
+- Set the extraction rate to `0/2` (or another appropriate denominator)
+- Include an error message in the summary output
+
+#### Example summary output for a malformed file
+```json
+{
+  "file": "test_data/invalid_cmd.tex",
+  "methods": {
+    "ast": {
+      "success": false,
+      "extraction_rate": "0/2",
+      "error": "Failed to process Invalid command",
+      "extraction_methods": {"method": "ast"}
+    }
+  }
+}
+```
+
+## Project Structure
+
+```
+latex_extract/
+├── extractors/           # Extraction method implementations
+│   ├── ast_extractor.py
+│   ├── pattern_extractor.py
+│   └── llm_extractor.py
+├── tests/               # Test files
+├── data/               # Sample LaTeX files
+├── results/            # Output directory
+├── extract_with_method.py  # Main script
+├── extract_controller.py   # Controller logic
+└── requirements.txt    # Dependencies
+```
+ 
\ No newline at end of file
