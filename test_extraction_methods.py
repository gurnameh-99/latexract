#!/usr/bin/env python3
"""Test script to evaluate different extraction methods on LaTeX files"""
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from extract_with_method import extract_with_method

class ExtractionTester:
    """Class to test different extraction methods on LaTeX files"""
    
    def __init__(self, data_dir: str = "data", results_dir: str = "test_results"):
        """Initialize the tester
        
        Args:
            data_dir: Directory containing LaTeX files to test
            results_dir: Directory to save test results
        """
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.methods = ['ast', 'pattern', 'llm', 'all']
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create results directory structure
        self._create_directory_structure()
    
    def _create_directory_structure(self):
        """Create the directory structure for test results"""
        # Create main results directory
        self.results_dir.mkdir(exist_ok=True)
        
        # Create timestamped directory for this test run
        self.test_run_dir = self.results_dir / self.timestamp
        self.test_run_dir.mkdir(exist_ok=True)
        
        # Create directories for each method
        for method in self.methods:
            method_dir = self.test_run_dir / method
            method_dir.mkdir(exist_ok=True)
    
    def _get_tex_files(self) -> List[Path]:
        """Get all .tex files from the data directory"""
        return list(self.data_dir.glob("**/*.tex"))
    
    def _save_results(self, results: Dict[str, Any], file_path: Path, method: str):
        """Save extraction results to a JSON file
        
        Args:
            results: Extraction results
            file_path: Path to the original LaTeX file
            method: Extraction method used
        """
        # Create a results file path
        rel_path = file_path.relative_to(self.data_dir)
        results_path = self.test_run_dir / method / f"{rel_path.stem}_results.json"
        
        # Create parent directories if they don't exist
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add metadata to results
        results_with_metadata = {
            "metadata": {
                "original_file": str(rel_path),
                "extraction_method": method,
                "timestamp": self.timestamp
            },
            "results": results
        }
        
        # Save results
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results_with_metadata, f, indent=2, ensure_ascii=False)
    
    def _create_summary(self, results: Dict[str, Dict[str, Any]]):
        """Create a summary of test results
        
        Args:
            results: Dictionary of test results for each file and method
        """
        summary = {
            "metadata": {
                "timestamp": self.timestamp,
                "total_files": len(results),
                "methods": self.methods
            },
            "results": {}
        }
        
        # Process results for each file
        for file_path, method_results in results.items():
            file_summary = {
                "file": str(file_path),
                "methods": {}
            }
            
            # Process results for each method
            for method, result in method_results.items():
                if result is None:
                    file_summary["methods"][method] = {
                        "success": False,
                        "error": "Extraction failed"
                    }
                elif "error" in result:
                    # Malformed or failed extraction
                    expected_fields = 2  # Default expected fields (e.g., title, authors)
                    file_summary["methods"][method] = {
                        "success": False,
                        "extraction_rate": f"0/{expected_fields}",
                        "error": result["error"],
                        "extraction_methods": result.get("extraction_method", {})
                    }
                else:
                    # Count extracted elements
                    extracted_count = sum(1 for v in result.values() 
                                       if v is not None and v != [] and v != {})
                    total_elements = len(result) - 1  # Exclude extraction_method
                    file_summary["methods"][method] = {
                        "success": True,
                        "extraction_rate": f"{extracted_count}/{total_elements}",
                        "extraction_methods": result.get("extraction_method", {})
                    }
            
            summary["results"][str(file_path)] = file_summary
        
        # Save summary
        summary_path = self.test_run_dir / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def run_tests(self):
        """Run tests for all methods on all LaTeX files"""
        tex_files = self._get_tex_files()
        if not tex_files:
            print(f"No .tex files found in {self.data_dir}")
            return
        
        print(f"Found {len(tex_files)} LaTeX files to test")
        results = {}
        
        # Test each file with each method
        for file_path in tex_files:
            print(f"\nTesting file: {file_path}")
            file_results = {}
            
            for method in self.methods:
                print(f"  Testing method: {method}")
                start_time = time.time()
                
                try:
                    # Extract information using the specified method
                    result = extract_with_method(
                        str(file_path),
                        method,
                        verbose=True
                    )
                    
                    # Save results
                    self._save_results(result, file_path, method)
                    
                    # Record results
                    file_results[method] = result
                    
                    # Print timing
                    elapsed_time = time.time() - start_time
                    print(f"    Completed in {elapsed_time:.2f} seconds")
                    
                except Exception as e:
                    print(f"    Error: {str(e)}")
                    file_results[method] = None
            
            results[file_path] = file_results
        
        # Create summary
        self._create_summary(results)
        print(f"\nTest results saved to: {self.test_run_dir}")

def main():
    """Main function to run the tests"""
    # Get the script directory
    script_dir = Path(__file__).parent
    
    # Set up paths
    data_dir = script_dir / "data"
    results_dir = script_dir / "test_results"
    
    # Create and run tester
    tester = ExtractionTester(data_dir, results_dir)
    tester.run_tests()

if __name__ == "__main__":
    main() 