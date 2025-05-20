# LaTeX Patterns for Physics Papers

This module provides a comprehensive set of patterns and extraction functions for identifying and extracting key elements from LaTeX documents, particularly physics papers from various journals and conferences.

## Features

- **Multiple Extraction Methods**:
  - Pattern-based extraction using regex
  - AST-based extraction using Pandoc
  - LLM-based extraction using OpenAI models
  - Fallback mechanisms between methods
- **Pattern Dictionary** for common physics journals and conferences
- **Title Extraction** from various document classes
- **Abstract Extraction** from different formats
- **Bibliography Extraction** with full citation details as key-value pairs
- **LaTeX Comment Removal** to clean up the source before processing
- **Document Class Detection** to apply the appropriate patterns
- **Equation Extraction** for both display and inline equations
- **Table Extraction** with captions and content

## Supported Document Classes

The module supports patterns for these document classes/publishers:

- **General** (fallback for unknown formats)
- **REVTeX 4-1** (APS journals: Physical Review Letters, Physical Review A-E)
- **AIP** (American Institute of Physics)
- **Elsevier** journals
- **IOP Publishing** journals
- **JHEP** (Journal of High Energy Physics)
- **JCAP** (Journal of Cosmology and Astroparticle Physics)
- **SPIE** conference format
- **IEEE** journals and conferences
- **MNRAS** (Monthly Notices of the Royal Astronomical Society)
- **arXiv** common formats
- **AASTeX** (American Astronomical Society journals)

## Usage

### As a Command Line Tool

```bash
# Extract using a specific method
python extract_with_method.py --method pattern input.tex [output.json]
python extract_with_method.py --method ast input.tex [output.json]
python extract_with_method.py --method llm input.tex [output.json]

# Extract using pattern-based approach
python latex_patterns.py input.tex [output.json]
```

This will extract title, abstract, bibliography, equations, and tables from the provided LaTeX file and either output the result to the console or save it to the specified JSON file.

### As a Python Module

```python
from latex_patterns import (
    remove_latex_comments,
    detect_document_class,
    extract_title,
    extract_abstract,
    extract_bibliography,
    extract_document_structure
)

# Process a file
result = extract_document_structure("path/to/paper.tex")
print(result["title"])
print(result["abstract"])

# Or process content directly
with open("path/to/paper.tex", "r") as f:
    content = f.read()

# Remove comments
clean_content = remove_latex_comments(content)

# Detect document class
doc_class = detect_document_class(clean_content)
print(f"Document class: {doc_class}")

# Extract elements individually
title = extract_title(clean_content, doc_class)
abstract = extract_abstract(clean_content, doc_class)
bibliography = extract_bibliography(clean_content, doc_class)

# Bibliography items include key, label (optional), and text
for item in bibliography:
    print(f"Citation key: {item['key']}")
    if 'label' in item and item['label']:
        print(f"Label: {item['label']}")
    print(f"Text: {item['text']}")
```

## Extraction Methods

### Pattern-Based Extraction
Uses regex patterns to identify and extract elements from LaTeX source. Best for:
- Simple document structures
- Standard LaTeX commands
- Quick processing
- No external dependencies

### AST-Based Extraction
Uses Pandoc to parse LaTeX into an Abstract Syntax Tree. Best for:
- Complex document structures
- Nested environments
- Accurate equation extraction
- Cross-references

### LLM-Based Extraction
Uses OpenAI models to extract information. Best for:
- Unusual document formats
- Complex structures
- When other methods fail
- High accuracy requirements

## Integration with Existing Extraction Tools

The module can be used with the main extraction system:

```python
from extract_controller import ExtractController

# Initialize with default settings
controller = ExtractController()

# Extract using all methods with fallback
result = controller.extract_from_file("path/to/paper.tex")

# Or use a specific method
result = controller.extract_with_method("path/to/paper.tex", method="pattern")
```

## Running Tests

The repository includes test scripts to evaluate different extraction methods:

```bash
# Test all extraction methods
python test_extraction_methods.py

# Test pattern-based extraction
python test_latex_patterns.py
```

This will process test files and save results in a structured format under the `test_results` directory.

## Limitations

- Complex nested LaTeX structures might not be correctly parsed by pattern-based extraction
- AST-based extraction requires Pandoc to be installed
- LLM-based extraction requires an OpenAI API key
- Some document-specific commands might be missed
- The pattern-based approach is less comprehensive than full LaTeX parsing but more targeted for specific elements
- LLM extraction may incur API costs

## Verbose Mode

All extraction methods support a verbose mode for debugging:

```python
# Enable verbose mode
controller = ExtractController(verbose=True)
result = controller.extract_from_file("path/to/paper.tex")
```

This will output additional information about the extraction process and save debug files when needed. 