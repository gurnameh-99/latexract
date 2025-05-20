# LaTeX Extraction Verification

This repository contains tools for extracting information from LaTeX files and verifying the extraction results.

## Verification Script

The `verify_extraction_results.py` script validates extraction results produced by the `test_extraction_methods.py` script.

### Overview

The verification script:
- Validates multiple aspects of the extracted data
- Generates detailed verification reports for each extraction method and file
- Creates a summary of verification results
- Calculates validity scores

### Validation Criteria

The script validates the following extracted elements:

| Element | Validation Criteria |
|---------|---------------------|
| Title | Not empty, reasonable length, no LaTeX commands |
| Abstract | Not empty, reasonable length, no document commands |
| Year | Valid number in reasonable range (1900-current) |
| Main Text | Sufficient length, proper structure |
| Equations | Balanced delimiters, proper format |
| Citations | Required fields (key), not empty |
| Tables | Required fields (content), not empty |

### Usage

Run the verification script on a specific extraction results directory:

```bash
python verify_extraction_results.py --result-dir test_results/20250520_084843
```

Options:
- `--result-dir`: Directory containing extraction results (required)
- `--data-dir`: Directory containing original LaTeX files (default: "data")
- `--report-dir`: Directory to save verification reports (default: within result-dir)

### Output

The script creates:
1. Individual verification files for each extraction result
2. A comprehensive verification summary file

Verification results are stored in a "verification" subdirectory within the results directory.

Example verification result structure:
```json
{
  "metadata": {
    "original_file": "0704.0978.tex",
    "extraction_method": "ast",
    "verification_timestamp": "20250520_123456"
  },
  "verifications": {
    "title": {
      "is_valid": true,
      "reason": "Valid",
      "extracted_value": "Distribution of the molecular absorption..."
    },
    "abstract": {
      "is_valid": false,
      "reason": "Not extracted",
      "extracted_value": null
    },
    ...
  },
  "overall_score": 75.0
}
```

Example verification summary structure:
```json
{
  "metadata": {
    "extraction_timestamp": "20250520_084843",
    "verification_timestamp": "20250520_123456",
    "total_files": 5
  },
  "results": {
    "0704.0978": {
      "file": "0704.0978",
      "methods": {
        "ast": {
          "overall_score": 75.0,
          "verifications": {
            "title": {
              "is_valid": true,
              "reason": "Valid"
            },
            ...
          }
        },
        ...
      }
    },
    ...
  }
}
```