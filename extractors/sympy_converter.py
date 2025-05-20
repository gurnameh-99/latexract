#!/usr/bin/env python3
"""Converter for LaTeX equations to sympy format"""
import re
try:
    from sympy.parsing.latex import parse_latex
except ImportError:
    print("Warning: sympy not installed. Equation verification will be skipped.")
    parse_latex = None

class SymPyConverter:
    """Convert LaTeX equations to sympy format for verification"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
    
    def log(self, message):
        """Print log message if verbose mode is enabled"""
        if self.verbose:
            print(message)
    
    def convert_equations(self, equations):
        """Convert LaTeX equations to sympy format
        
        Args:
            equations: List of LaTeX equation strings or dictionaries with 'latex' key
            
        Returns:
            List of dictionaries with the conversion results
        """
        if not parse_latex:
            self.log("SymPy not available, skipping equation conversion")
            
            # Handle both string and dictionary input formats
            if equations and isinstance(equations[0], dict):
                return [{"latex": eq["latex"], "sympy": None, "verified": False} for eq in equations]
            else:
                return [{"latex": eq, "sympy": None, "verified": False} for eq in equations]
        
        sympy_equations = []
        
        for i, eq in enumerate(equations):
            # Extract the LaTeX string depending on input format
            if isinstance(eq, dict) and 'latex' in eq:
                latex_eq = eq['latex']
            else:
                latex_eq = eq
                
            try:
                # Clean up the LaTeX equation
                clean_eq = self._clean_equation(latex_eq)
                
                # Try to parse with sympy
                sympy_eq = parse_latex(clean_eq)
                sympy_equations.append({
                    "latex": latex_eq,
                    "sympy": str(sympy_eq),
                    "verified": True
                })
                self.log(f"Equation {i+1} converted successfully")
            except Exception as e:
                # If parsing fails, keep the LaTeX and mark as unverified
                sympy_equations.append({
                    "latex": latex_eq,
                    "sympy": None,
                    "verified": False,
                    "error": str(e)
                })
                self.log(f"Equation {i+1} conversion failed: {str(e)}")
        
        return sympy_equations
    
    def _clean_equation(self, latex_eq):
        """Clean LaTeX equation for better parsing"""
        # Remove label commands that interfere with parsing
        eq = re.sub(r'\\label\{[^}]*\}', '', latex_eq)
        
        # Remove display math markers if present
        eq = eq.strip()
        if eq.startswith('$$') and eq.endswith('$$'):
            eq = eq[2:-2].strip()
        
        # Replace special function names that SymPy may not recognize
        eq = re.sub(r'\\operatorname\{([^}]+)\}', r'\1', eq)
        eq = re.sub(r'\\text\{([^}]+)\}', r'\1', eq)
        
        # Simplify fractions which often cause issues
        eq = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'((\1)/(\2))', eq)
        
        # Replace LaTeX matrices with simpler notation
        eq = re.sub(r'\\begin\{(p?matrix|bmatrix|vmatrix|Vmatrix)\}(.*?)\\end\{\1\}', 
                   lambda m: self._convert_matrix(m.group(2)), 
                   eq, flags=re.DOTALL)
        
        return eq
    
    def _convert_matrix(self, matrix_content):
        """Convert LaTeX matrix to a format that SymPy can parse"""
        # Replace LaTeX matrix rows with brackets
        rows = matrix_content.split('\\\\')
        processed_rows = []
        
        for row in rows:
            # Clean up the row and split by &
            elements = row.strip().split('&')
            elements = [e.strip() for e in elements if e.strip()]
            if elements:
                processed_rows.append('[' + ', '.join(elements) + ']')
        
        if processed_rows:
            return 'Matrix([' + ', '.join(processed_rows) + '])'
        return 'Matrix([])'
