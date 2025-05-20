#!/usr/bin/env python3
"""Verification script for LaTeX extraction results"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime


class ExtractionVerifier:
    """Class to verify the extraction results against common validation criteria"""
    
    def __init__(self, test_result_dir: str, data_dir: str, report_dir: str = None):
        """Initialize the verifier
        
        Args:
            test_result_dir: Directory containing extraction results (typically a timestamped folder in test_results)
            data_dir: Directory containing original LaTeX files
            report_dir: Directory to save verification reports (default: same as test_result_dir)
        """
        self.result_dir = Path(test_result_dir)
        self.data_dir = Path(data_dir)
        self.report_dir = Path(report_dir) if report_dir else self.result_dir / "verification"
        self.methods = ['ast', 'pattern', 'llm', 'all']
        self.extraction_timestamp = self.result_dir.name
        
        # Create report directory
        self.report_dir.mkdir(exist_ok=True, parents=True)
        
        # Load summary if it exists
        self.summary_path = self.result_dir / "summary.json"
        self.summary = self._load_summary() if self.summary_path.exists() else None
        
    def _load_summary(self) -> Dict[str, Any]:
        """Load the summary JSON file"""
        with open(self.summary_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_result_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a result JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_tex_file(self, file_path: Path) -> str:
        """Load a LaTeX file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _get_result_files(self, method: str) -> List[Path]:
        """Get all result files for a specific method"""
        method_dir = self.result_dir / method
        return list(method_dir.glob("**/*_results.json"))
    
    def _validate_title(self, title: str) -> Tuple[bool, str]:
        """Validate the extracted title
        
        Args:
            title: The extracted title
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not title:
            return False, "Title is empty"
        
        if len(title) < 3:
            return False, f"Title too short ({len(title)} chars)"
            
        if len(title) > 300:
            return False, f"Title suspiciously long ({len(title)} chars)"
        
        if title.count('\n') > 0:
            return False, "Title contains newlines"
            
        if re.search(r'\\begin|\\end|\\section|\\subsection', title):
            return False, "Title contains LaTeX commands"
            
        return True, "Valid"
    
    def _validate_abstract(self, abstract: str) -> Tuple[bool, str]:
        """Validate the extracted abstract
        
        Args:
            abstract: The extracted abstract
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not abstract:
            return False, "Abstract is empty"
            
        if len(abstract) < 50:
            return False, f"Abstract too short ({len(abstract)} chars)"
            
        if len(abstract) > 3000:
            return False, f"Abstract suspiciously long ({len(abstract)} chars)"
            
        if re.search(r'\\begin{document}|\\end{document}|\\maketitle', abstract):
            return False, "Abstract contains LaTeX document commands"
            
        return True, "Valid"
    
    def _validate_year(self, year: str) -> Tuple[bool, str]:
        """Validate the extracted year
        
        Args:
            year: The extracted year
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not year:
            return False, "Year is empty"
            
        # Try to convert to integer
        try:
            year_int = int(year)
        except ValueError:
            return False, f"Year '{year}' is not a valid number"
            
        # Check if year is in reasonable range (1900-current year + 1)
        current_year = datetime.now().year
        if year_int < 1900 or year_int > current_year + 1:
            return False, f"Year {year_int} outside reasonable range (1900-{current_year+1})"
            
        return True, "Valid"
    
    def _validate_equations(self, equations: List[Dict[str, Any]], 
                          is_display: bool = True) -> Tuple[bool, str]:
        """Validate the extracted equations
        
        Args:
            equations: List of equation dictionaries
            is_display: Whether these are display equations
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not equations:
            return True, "No equations to validate"
            
        for i, eq in enumerate(equations):
            # Check required fields
            if 'latex' not in eq:
                return False, f"Equation {i} missing 'latex' field"
                
            # Validate latex content
            latex = eq['latex']
            if not latex or latex.strip() == '':
                return False, f"Equation {i} has empty LaTeX content"
                
            # Check for balanced delimiters
            open_delims = latex.count('{') + latex.count('[') + latex.count('(')
            close_delims = latex.count('}') + latex.count(']') + latex.count(')')
            if open_delims != close_delims:
                return False, f"Equation {i} has unbalanced delimiters: {latex}"
                
            # Check for display equations
            if is_display and ('is_display' not in eq or not eq['is_display']):
                return False, f"Equation in display list but is_display=False: {latex}"
                
        return True, "Valid"
    
    def _validate_citations(self, citations: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Validate the extracted citations
        
        Args:
            citations: List of citation dictionaries
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not citations:
            return True, "No citations to validate"
            
        for i, cit in enumerate(citations):
            # Check for key required fields
            if 'key' not in cit:
                return False, f"Citation {i} missing 'key' field"
                
            # Citation key should not be empty
            if not cit['key'] or cit['key'].strip() == '':
                return False, f"Citation {i} has empty key"
                
        return True, "Valid"
    
    def _validate_tables(self, tables: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Validate the extracted tables
        
        Args:
            tables: List of table dictionaries
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not tables:
            return True, "No tables to validate"
            
        for i, table in enumerate(tables):
            # Check for content field
            if 'content' not in table:
                return False, f"Table {i} missing 'content' field"
                
            # Table content should not be empty
            if not table['content'] or table['content'].strip() == '':
                return False, f"Table {i} has empty content"
                
        return True, "Valid"
    
    def _validate_main_text(self, main_text: Dict[str, str]) -> Tuple[bool, str]:
        """Validate the extracted main text
        
        Args:
            main_text: Dictionary with text samples
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Handle different formats of main_text
        if isinstance(main_text, str):
            if len(main_text) < 100:
                return False, f"Main text too short ({len(main_text)} chars)"
            return True, "Valid"
            
        elif isinstance(main_text, dict):
            # Check if it has samples
            if 'first_500' not in main_text and 'last_500' not in main_text:
                return False, "Main text missing sample keys"
                
            # Validate first_500 if present
            if 'first_500' in main_text:
                first_sample = main_text['first_500']
                if not first_sample or len(first_sample) < 100:
                    return False, f"First text sample too short ({len(first_sample) if first_sample else 0} chars)"
                    
            # Validate last_500 if present
            if 'last_500' in main_text:
                last_sample = main_text['last_500']
                if not last_sample or len(last_sample) < 100:
                    return False, f"Last text sample too short ({len(last_sample) if last_sample else 0} chars)"
                    
            return True, "Valid"
            
        else:
            return False, f"Unexpected main_text format: {type(main_text)}"
    
    def verify_extraction(self, file_path: Path, method: str) -> Dict[str, Any]:
        """Verify a single extraction result
        
        Args:
            file_path: Path to the extraction result file
            method: Extraction method
            
        Returns:
            Dictionary with verification results
        """
        # Load result file
        result_data = self._load_result_file(file_path)
        results = result_data.get('results', {})
        
        verification = {
            "metadata": {
                "original_file": result_data.get('metadata', {}).get('original_file', ''),
                "extraction_method": method,
                "verification_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            },
            "verifications": {}
        }
        
        # Validate title
        title = results.get('title')
        if title is not None:
            is_valid, reason = self._validate_title(title)
            verification['verifications']['title'] = {
                "is_valid": is_valid,
                "reason": reason,
                "extracted_value": title
            }
        else:
            verification['verifications']['title'] = {
                "is_valid": False,
                "reason": "Not extracted",
                "extracted_value": None
            }
        
        # Validate abstract
        abstract = results.get('abstract')
        if abstract is not None:
            is_valid, reason = self._validate_abstract(abstract)
            verification['verifications']['abstract'] = {
                "is_valid": is_valid,
                "reason": reason,
                "extracted_value": abstract[:100] + "..." if abstract and len(abstract) > 100 else abstract
            }
        else:
            verification['verifications']['abstract'] = {
                "is_valid": False,
                "reason": "Not extracted",
                "extracted_value": None
            }
        
        # Validate year
        year = results.get('year')
        if year is not None:
            is_valid, reason = self._validate_year(year)
            verification['verifications']['year'] = {
                "is_valid": is_valid,
                "reason": reason,
                "extracted_value": year
            }
        else:
            verification['verifications']['year'] = {
                "is_valid": False,
                "reason": "Not extracted",
                "extracted_value": None
            }
        
        # Validate main_text
        main_text = results.get('main_text')
        if main_text is None:
            main_text = results.get('main_text_sample')
            
        if main_text is not None:
            is_valid, reason = self._validate_main_text(main_text)
            verification['verifications']['main_text'] = {
                "is_valid": is_valid,
                "reason": reason,
                "extracted_value": "Text sample available" if is_valid else "Invalid text sample"
            }
        else:
            verification['verifications']['main_text'] = {
                "is_valid": False,
                "reason": "Not extracted",
                "extracted_value": None
            }
        
        # Validate display_equations
        display_equations = results.get('display_equations', [])
        is_valid, reason = self._validate_equations(display_equations, is_display=True)
        verification['verifications']['display_equations'] = {
            "is_valid": is_valid,
            "reason": reason,
            "count": len(display_equations)
        }
        
        # Validate inline_equations
        inline_equations = results.get('inline_equations', [])
        is_valid, reason = self._validate_equations(inline_equations, is_display=False)
        verification['verifications']['inline_equations'] = {
            "is_valid": is_valid,
            "reason": reason,
            "count": len(inline_equations)
        }
        
        # Validate citations
        citations = results.get('citations', [])
        is_valid, reason = self._validate_citations(citations)
        verification['verifications']['citations'] = {
            "is_valid": is_valid,
            "reason": reason,
            "count": len(citations)
        }
        
        # Validate tables
        tables = results.get('tables', [])
        is_valid, reason = self._validate_tables(tables)
        verification['verifications']['tables'] = {
            "is_valid": is_valid,
            "reason": reason,
            "count": len(tables)
        }
        
        # Calculate overall validity score
        valid_count = sum(1 for item in verification['verifications'].values() if item['is_valid'])
        total_count = len(verification['verifications'])
        verification['overall_score'] = round(valid_count / total_count * 100, 2) if total_count > 0 else 0
        
        return verification
    
    def _save_verification(self, verification: Dict[str, Any], file_path: Path, method: str):
        """Save verification results to a JSON file
        
        Args:
            verification: Verification results
            file_path: Path to the original extraction result file
            method: Extraction method used
        """
        # Create a verification file path
        verification_dir = self.report_dir / method
        verification_dir.mkdir(parents=True, exist_ok=True)
        
        # Get original filename
        original_filename = file_path.stem
        if original_filename.endswith('_results'):
            original_filename = original_filename[:-8]
            
        verification_path = verification_dir / f"{original_filename}_verification.json"
        
        # Save verification results
        with open(verification_path, 'w', encoding='utf-8') as f:
            json.dump(verification, f, indent=2, ensure_ascii=False)
            
        return verification_path
    
    def _create_verification_summary(self, verifications: Dict[str, Dict[str, Any]]):
        """Create a summary of verification results
        
        Args:
            verifications: Dictionary of verification results for each file and method
        """
        summary = {
            "metadata": {
                "extraction_timestamp": self.extraction_timestamp,
                "verification_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "total_files": len(verifications)
            },
            "results": {}
        }
        
        # Process results for each file
        for file_path, method_results in verifications.items():
            file_summary = {
                "file": str(file_path),
                "methods": {}
            }
            
            # Process results for each method
            for method, verification in method_results.items():
                file_summary["methods"][method] = {
                    "overall_score": verification.get('overall_score', 0),
                    "verifications": {}
                }
                
                # Add field-specific verification results
                for field, field_verification in verification.get('verifications', {}).items():
                    file_summary["methods"][method]["verifications"][field] = {
                        "is_valid": field_verification.get('is_valid', False),
                        "reason": field_verification.get('reason', '')
                    }
            
            summary["results"][str(file_path)] = file_summary
        
        # Save summary
        summary_path = self.report_dir / "verification_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
            
        return summary_path
    
    def run_verification(self):
        """Run verification for all extracted results"""
        verifications = {}
        
        # Verify results for each method
        for method in self.methods:
            method_dir = self.result_dir / method
            if not method_dir.exists():
                print(f"Method directory not found: {method_dir}")
                continue
                
            print(f"\nVerifying results for method: {method}")
            result_files = self._get_result_files(method)
            
            for file_path in result_files:
                print(f"  Verifying: {file_path.name}")
                original_file = file_path.stem
                if original_file.endswith('_results'):
                    original_file = original_file[:-8]
                
                # Store verification results
                try:
                    verification = self.verify_extraction(file_path, method)
                    verification_path = self._save_verification(verification, file_path, method)
                    print(f"    Verification saved to: {verification_path}")
                    
                    # Store for summary
                    if original_file not in verifications:
                        verifications[original_file] = {}
                    verifications[original_file][method] = verification
                    
                except Exception as e:
                    print(f"    Error verifying {file_path}: {str(e)}")
        
        # Create verification summary
        summary_path = self._create_verification_summary(verifications)
        print(f"\nVerification summary saved to: {summary_path}")
        
        return summary_path


def main():
    """Main function to run the verification"""
    parser = argparse.ArgumentParser(description='Verify LaTeX extraction results')
    parser.add_argument('--result-dir', type=str, required=True,
                        help='Directory containing extraction results (e.g., test_results/20250520_084843)')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Directory containing original LaTeX files')
    parser.add_argument('--report-dir', type=str, default=None,
                        help='Directory to save verification reports (default: within result-dir)')
    
    args = parser.parse_args()
    
    # Create and run verifier
    verifier = ExtractionVerifier(args.result_dir, args.data_dir, args.report_dir)
    verifier.run_verification()


if __name__ == "__main__":
    main() 