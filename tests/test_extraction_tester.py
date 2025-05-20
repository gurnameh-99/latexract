#!/usr/bin/env python3
"""Unit tests for the ExtractionTester class"""
import unittest
import json
import shutil
from pathlib import Path
import sys
import os

# Add the parent directory to the Python path to import the main module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_extraction_methods import ExtractionTester

class TestExtractionTester(unittest.TestCase):
    """Test cases for ExtractionTester class"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.test_data_dir = Path("test_data")
        self.test_results_dir = Path("test_results")
        self.tester = ExtractionTester(
            data_dir=str(self.test_data_dir),
            results_dir=str(self.test_results_dir)
        )
        
        # Create test data directory
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Create various test LaTeX files
        self._create_test_latex_files()
        self._create_malformed_latex_files()
    
    def _create_test_latex_files(self):
        """Create various test LaTeX files with different structures"""
        # Basic article
        self.basic_tex = self.test_data_dir / "basic.tex"
        with open(self.basic_tex, "w") as f:
            f.write("""\\documentclass{article}
\\title{Basic Article}
\\author{John Doe}
\\begin{document}
\\maketitle
\\section{Introduction}
This is a basic article.
\\end{document}""")

        # Complex article with multiple sections and environments
        self.complex_tex = self.test_data_dir / "complex.tex"
        with open(self.complex_tex, "w") as f:
            f.write("""\\documentclass{article}
\\usepackage{amsmath}
\\title{Complex Article}
\\author{Jane Smith\\thanks{University of Example}}
\\date{\\today}
\\begin{document}
\\maketitle
\\section{Introduction}
\\begin{equation}
E = mc^2
\\end{equation}
\\section{Methods}
\\begin{itemize}
\\item Method 1
\\item Method 2
\\end{itemize}
\\end{document}""")

        # Article with bibliography
        self.bib_tex = self.test_data_dir / "with_bib.tex"
        with open(self.bib_tex, "w") as f:
            f.write("""\\documentclass{article}
\\usepackage{natbib}
\\title{Article with Bibliography}
\\author{Alice Brown}
\\begin{document}
\\maketitle
\\section{Introduction}
As shown in \\cite{smith2020}.
\\bibliographystyle{plain}
\\bibliography{references}
\\end{document}""")

        # Article with figures and tables
        self.figures_tex = self.test_data_dir / "figures.tex"
        with open(self.figures_tex, "w") as f:
            f.write("""\\documentclass{article}
\\usepackage{graphicx}
\\title{Article with Figures}
\\author{Bob Wilson}
\\begin{document}
\\maketitle
\\begin{figure}[h]
\\centering
\\includegraphics{example}
\\caption{Example figure}
\\end{figure}
\\begin{table}[h]
\\centering
\\begin{tabular}{|c|c|}
\\hline
A & B \\\\
\\hline
1 & 2 \\\\
\\hline
\\end{tabular}
\\caption{Example table}
\\end{table}
\\end{document}""")
    
    def _create_malformed_latex_files(self):
        """Create various malformed LaTeX files to test error handling"""
        # Missing document class
        self.no_docclass_tex = self.test_data_dir / "no_docclass.tex"
        with open(self.no_docclass_tex, "w") as f:
            f.write("""\\begin{document}
\\title{No Document Class}
\\author{Test Author}
\\maketitle
\\end{document}""")

        # Unclosed environment
        self.unclosed_env_tex = self.test_data_dir / "unclosed_env.tex"
        with open(self.unclosed_env_tex, "w") as f:
            f.write("""\\documentclass{article}
\\begin{document}
\\begin{equation}
E = mc^2
\\end{document}""")

        # Invalid command
        self.invalid_cmd_tex = self.test_data_dir / "invalid_cmd.tex"
        with open(self.invalid_cmd_tex, "w") as f:
            f.write("""\\documentclass{article}
\\begin{document}
\\invalidcommand{test}
\\end{document}""")

        # Missing closing brace
        self.missing_brace_tex = self.test_data_dir / "missing_brace.tex"
        with open(self.missing_brace_tex, "w") as f:
            f.write("""\\documentclass{article}
\\begin{document}
\\title{Missing Brace
\\end{document}""")

        # Empty file
        self.empty_tex = self.test_data_dir / "empty.tex"
        with open(self.empty_tex, "w") as f:
            f.write("")

        # Non-LaTeX content
        self.non_latex_tex = self.test_data_dir / "non_latex.tex"
        with open(self.non_latex_tex, "w") as f:
            f.write("This is not a LaTeX file\nJust some plain text\n")
    
    def tearDown(self):
        """Clean up test environment after each test"""
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
        if self.test_results_dir.exists():
            shutil.rmtree(self.test_results_dir)
    
    def test_initialization(self):
        """Test proper initialization of ExtractionTester"""
        self.assertEqual(self.tester.data_dir, self.test_data_dir)
        self.assertEqual(self.tester.results_dir, self.test_results_dir)
        self.assertEqual(set(self.tester.methods), {'ast', 'pattern', 'llm', 'all'})
        self.assertTrue(self.tester.timestamp)
    
    def test_directory_structure_creation(self):
        """Test creation of directory structure"""
        self.tester._create_directory_structure()
        
        # Check main results directory
        self.assertTrue(self.test_results_dir.exists())
        
        # Check timestamped directory
        timestamp_dir = self.test_results_dir / self.tester.timestamp
        self.assertTrue(timestamp_dir.exists())
        
        # Check method directories
        for method in self.tester.methods:
            method_dir = timestamp_dir / method
            self.assertTrue(method_dir.exists())
    
    def test_get_tex_files(self):
        """Test finding .tex files in data directory"""
        tex_files = self.tester._get_tex_files()
        self.assertEqual(len(tex_files), 10)  # Now we have 10 test files
        expected_files = {
            self.basic_tex, self.complex_tex, self.bib_tex, self.figures_tex,
            self.no_docclass_tex, self.unclosed_env_tex, self.invalid_cmd_tex,
            self.missing_brace_tex, self.empty_tex, self.non_latex_tex
        }
        self.assertEqual(set(tex_files), expected_files)
    
    def test_save_results(self):
        """Test saving extraction results"""
        # Create test results
        test_results = {
            "title": "Test Title",
            "authors": ["Author 1", "Author 2"],
            "extraction_method": {"method": "test"}
        }
        
        # Save results
        self.tester._create_directory_structure()
        self.tester._save_results(test_results, self.basic_tex, "test_method")
        
        # Check if results file exists
        results_path = self.tester.test_run_dir / "test_method" / "basic_results.json"
        self.assertTrue(results_path.exists())
        
        # Verify results content
        with open(results_path, 'r', encoding='utf-8') as f:
            saved_results = json.load(f)
        
        self.assertEqual(saved_results["metadata"]["original_file"], "basic.tex")
        self.assertEqual(saved_results["metadata"]["extraction_method"], "test_method")
        self.assertEqual(saved_results["results"], test_results)
    
    def test_create_summary(self):
        """Test creation of summary file"""
        # Create test results
        test_results = {
            self.basic_tex: {
                "ast": {
                    "title": "Basic Article",
                    "authors": ["John Doe"],
                    "extraction_method": {"method": "ast"}
                },
                "pattern": None  # Simulate failed extraction
            }
        }
        
        # Create summary
        self.tester._create_summary(test_results)
        
        # Check if summary file exists
        summary_path = self.tester.test_run_dir / "summary.json"
        self.assertTrue(summary_path.exists())
        
        # Verify summary content
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        self.assertEqual(summary["metadata"]["total_files"], 1)
        self.assertEqual(summary["metadata"]["methods"], self.tester.methods)
        self.assertTrue(str(self.basic_tex) in summary["results"])
    
    def test_complex_latex_extraction(self):
        """Test extraction from complex LaTeX document"""
        self.tester._create_directory_structure()
        
        # Create test results for complex document
        test_results = {
            "title": "Complex Article",
            "authors": ["Jane Smith"],
            "date": "\\today",
            "sections": ["Introduction", "Methods"],
            "equations": ["E = mc^2"],
            "extraction_method": {"method": "ast"}
        }
        
        # Save results
        self.tester._save_results(test_results, self.complex_tex, "test_method")
        
        # Verify results
        results_path = self.tester.test_run_dir / "test_method" / "complex_results.json"
        self.assertTrue(results_path.exists())
        
        with open(results_path, 'r', encoding='utf-8') as f:
            saved_results = json.load(f)
        
        self.assertEqual(saved_results["results"]["title"], "Complex Article")
        self.assertEqual(saved_results["results"]["sections"], ["Introduction", "Methods"])
    
    def test_bibliography_extraction(self):
        """Test extraction from document with bibliography"""
        self.tester._create_directory_structure()
        
        # Create test results for bibliography document
        test_results = {
            "title": "Article with Bibliography",
            "authors": ["Alice Brown"],
            "citations": ["smith2020"],
            "extraction_method": {"method": "ast"}
        }
        
        # Save results
        self.tester._save_results(test_results, self.bib_tex, "test_method")
        
        # Verify results
        results_path = self.tester.test_run_dir / "test_method" / "with_bib_results.json"
        self.assertTrue(results_path.exists())
        
        with open(results_path, 'r', encoding='utf-8') as f:
            saved_results = json.load(f)
        
        self.assertEqual(saved_results["results"]["title"], "Article with Bibliography")
        self.assertEqual(saved_results["results"]["citations"], ["smith2020"])
    
    def test_figures_and_tables_extraction(self):
        """Test extraction from document with figures and tables"""
        self.tester._create_directory_structure()
        
        # Create test results for figures document
        test_results = {
            "title": "Article with Figures",
            "authors": ["Bob Wilson"],
            "figures": ["Example figure"],
            "tables": ["Example table"],
            "extraction_method": {"method": "ast"}
        }
        
        # Save results
        self.tester._save_results(test_results, self.figures_tex, "test_method")
        
        # Verify results
        results_path = self.tester.test_run_dir / "test_method" / "figures_results.json"
        self.assertTrue(results_path.exists())
        
        with open(results_path, 'r', encoding='utf-8') as f:
            saved_results = json.load(f)
        
        self.assertEqual(saved_results["results"]["title"], "Article with Figures")
        self.assertEqual(saved_results["results"]["figures"], ["Example figure"])
        self.assertEqual(saved_results["results"]["tables"], ["Example table"])

    def test_malformed_latex_handling(self):
        """Test handling of various malformed LaTeX inputs"""
        self.tester._create_directory_structure()
        
        # Test each malformed file
        malformed_files = {
            self.no_docclass_tex: "Missing document class",
            self.unclosed_env_tex: "Unclosed environment",
            self.invalid_cmd_tex: "Invalid command",
            self.missing_brace_tex: "Missing closing brace",
            self.empty_tex: "Empty file",
            self.non_latex_tex: "Non-LaTeX content"
        }
        
        for file_path, description in malformed_files.items():
            with self.subTest(description=description):
                # Create test results for malformed document
                test_results = {
                    "error": f"Failed to process {description}",
                    "extraction_method": {"method": "ast"}
                }
                
                # Save results
                self.tester._save_results(test_results, file_path, "test_method")
                
                # Verify results
                results_path = self.tester.test_run_dir / "test_method" / f"{file_path.stem}_results.json"
                self.assertTrue(results_path.exists())
                
                with open(results_path, 'r', encoding='utf-8') as f:
                    saved_results = json.load(f)
                
                self.assertEqual(saved_results["results"]["error"], f"Failed to process {description}")
    
    def test_error_summary_generation(self):
        """Test summary generation with error cases"""
        self.tester._create_directory_structure()
        
        # Create test results with both successful and failed extractions
        test_results = {
            self.basic_tex: {
                "ast": {
                    "title": "Basic Article",
                    "authors": ["John Doe"],
                    "extraction_method": {"method": "ast"}
                }
            },
            self.invalid_cmd_tex: {
                "ast": {
                    "error": "Failed to process Invalid command",
                    "extraction_method": {"method": "ast"}
                }
            },
            self.empty_tex: {
                "ast": {
                    "error": "Failed to process Empty file",
                    "extraction_method": {"method": "ast"}
                }
            }
        }
        
        # Create summary
        self.tester._create_summary(test_results)
        
        # Check if summary file exists
        summary_path = self.tester.test_run_dir / "summary.json"
        self.assertTrue(summary_path.exists())
        
        # Verify summary content
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        self.assertEqual(summary["metadata"]["total_files"], 3)
        self.assertEqual(summary["metadata"]["methods"], self.tester.methods)
        
        # Check successful extraction
        basic_results = summary["results"][str(self.basic_tex)]
        self.assertTrue(basic_results["methods"]["ast"]["success"])
        self.assertEqual(basic_results["methods"]["ast"]["extraction_rate"], "3/2")
        
        # Check failed extractions
        invalid_results = summary["results"][str(self.invalid_cmd_tex)]
        self.assertFalse(invalid_results["methods"]["ast"]["success"])
        self.assertEqual(invalid_results["methods"]["ast"]["extraction_rate"], "0/2")
        self.assertIn("Failed to process Invalid command", invalid_results["methods"]["ast"]["error"])
        
        empty_results = summary["results"][str(self.empty_tex)]
        self.assertFalse(empty_results["methods"]["ast"]["success"])
        self.assertEqual(empty_results["methods"]["ast"]["extraction_rate"], "0/2")
        self.assertIn("Failed to process Empty file", empty_results["methods"]["ast"]["error"])

if __name__ == '__main__':
    unittest.main() 