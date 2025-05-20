#!/usr/bin/env python3
"""Script to extract information from LaTeX files using a specific extractor method"""
import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from extractors.ast_extractor import AstExtractor
from extractors.pattern_extractor import PatternExtractor
from extractors.llm_extractor import LaTeXExtractor
from extract_controller import ExtractController

def update_results(results, new_results, method):
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

def extract_with_method(
    tex_file_path: str,
    method: str,
    output_file: Optional[str] = None,
    output_format: str = 'mathml',
    verbose: bool = False
) -> Dict[str, Any]:
    """Extract information from a LaTeX file using a specific method
    
    Args:
        tex_file_path: Path to the LaTeX file
        method: Extraction method to use ('ast', 'pattern', 'llm', or 'all')
        output_file: Optional path to save the results
        output_format: Format for equation conversion ('mathml' or 'sympy')
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary containing extracted information
    """
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
        "extraction_method": {
            "title": None,
            "abstract": None,
            "year": None,
            "main_text": None,
            "citations": None,
            "display_equations": None,
            "inline_equations": None,
            "tables": None
        }
    }
    
    try:
        if method == 'all':
            # Use the full controller with all methods
            controller = ExtractController(verbose=verbose)
            results = controller.extract_from_file(tex_file_path, output_file, output_format)
        else:
            # Use specific extractor
            if method == 'ast':
                extractor = AstExtractor(verbose=verbose)
            elif method == 'pattern':
                extractor = PatternExtractor(verbose=verbose)
            elif method == 'llm':
                extractor = LaTeXExtractor()
            else:
                raise ValueError(f"Unknown extraction method: {method}")
            
            # Extract information
            if method == 'llm':
                with open(tex_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                extracted = extractor.extract_from_content(content)
            else:
                extracted = extractor.extract_from_file(tex_file_path)
            
            # Update results with extracted information using the same method as ExtractController
            update_results(results, extracted, method)
            
            # Save results if output file is specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                if verbose:
                    print(f"Results saved to: {output_file}")
        
        return results
    
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        return None

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="Extract information from LaTeX files using a specific method"
    )
    parser.add_argument(
        "input",
        help="Input LaTeX file"
    )
    parser.add_argument(
        "-m", "--method",
        choices=['ast', 'pattern', 'llm', 'all'],
        default='all',
        help="Extraction method to use (default: all)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path"
    )
    parser.add_argument(
        "-f", "--format",
        choices=['mathml', 'sympy'],
        default='mathml',
        help="Format for equation conversion (default: mathml)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Process the file
    results = extract_with_method(
        args.input,
        args.method,
        args.output,
        args.format,
        args.verbose
    )
    
    if results:
        if not args.output:
            # Print results to console if no output file specified
            print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("Extraction failed")

if __name__ == "__main__":
    main() 