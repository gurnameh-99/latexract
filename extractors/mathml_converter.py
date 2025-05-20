#!/usr/bin/env python3
"""Converter for LaTeX equations to MathML format"""
import re
try:
    from latex2mathml.converter import convert
except ImportError:
    print("Warning: latex2mathml not installed. MathML conversion will be skipped.")
    convert = None

class MathMLConverter:
    """Convert LaTeX equations to MathML format"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
    
    def log(self, message):
        """Print log message if verbose mode is enabled"""
        if self.verbose:
            print(message)
    
    def convert_equations(self, equations):
        """Convert LaTeX equations to MathML format
        
        Args:
            equations: List of LaTeX equation strings or dictionaries with 'latex' key
            
        Returns:
            List of dictionaries with the conversion results
        """
        if not convert:
            self.log("latex2mathml not available, skipping equation conversion")
            
            # Handle both string and dictionary input formats
            if equations and isinstance(equations[0], dict):
                return [{"latex": eq["latex"], "mathml": None, "verified": False} for eq in equations]
            else:
                return [{"latex": eq, "mathml": None, "verified": False} for eq in equations]
        
        mathml_equations = []
        
        for i, eq in enumerate(equations):
            # Extract the LaTeX string depending on input format
            if isinstance(eq, dict) and 'latex' in eq:
                latex_eq = eq['latex']
            else:
                latex_eq = eq
                
            try:
                # Clean up the LaTeX equation
                clean_eq = self._clean_equation(latex_eq)
                
                # Convert to MathML
                mathml = convert(clean_eq)
                mathml_equations.append({
                    "latex": latex_eq,
                    "mathml": mathml,
                    "verified": True
                })
                self.log(f"Equation {i+1} converted successfully to MathML")
            except Exception as e:
                # If conversion fails, keep the LaTeX and mark as unverified
                mathml_equations.append({
                    "latex": latex_eq,
                    "mathml": None,
                    "verified": False,
                    "error": str(e)
                })
                self.log(f"Equation {i+1} MathML conversion failed: {str(e)}")
        
        return mathml_equations
    
    def _clean_equation(self, latex_eq):
        """Clean LaTeX equation for better parsing"""
        # Remove label commands that interfere with parsing
        eq = re.sub(r'\\label\{[^}]*\}', '', latex_eq)
        
        # Remove display math markers if present
        eq = eq.strip()
        if eq.startswith('$$') and eq.endswith('$$'):
            eq = eq[2:-2].strip()
        elif eq.startswith('\\[') and eq.endswith('\\]'):
            eq = eq[2:-2].strip()
        
        # Remove equation environment markers
        eq = re.sub(r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', r'\1', eq, flags=re.DOTALL)
        eq = re.sub(r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', r'\1', eq, flags=re.DOTALL)
        eq = re.sub(r'\\begin\{eqnarray\*?\}(.*?)\\end\{eqnarray\*?\}', r'\1', eq, flags=re.DOTALL)
        eq = re.sub(r'\\begin\{gather\*?\}(.*?)\\end\{gather\*?\}', r'\1', eq, flags=re.DOTALL)
        eq = re.sub(r'\\begin\{aligned\}(.*?)\\end\{aligned\}', r'\1', eq, flags=re.DOTALL)
        
        # Remove alignment characters
        eq = re.sub(r'&', '', eq)
        eq = re.sub(r'\\\\', '', eq)
        
        # Remove non-breaking spaces
        eq = eq.replace('~', ' ')
        
        # Normalize whitespace
        eq = re.sub(r'\s+', ' ', eq)
        eq = eq.strip()
        
        return eq 