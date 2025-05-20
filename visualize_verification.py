#!/usr/bin/env python3
"""Visualization script for verification results"""

import os
import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Any, List


class VerificationVisualizer:
    """Class to visualize verification results"""
    
    def __init__(self, verification_dir: str, output_dir: str = None):
        """Initialize the visualizer
        
        Args:
            verification_dir: Directory containing verification results
            output_dir: Directory to save visualizations
        """
        self.verification_dir = Path(verification_dir)
        self.output_dir = Path(output_dir) if output_dir else self.verification_dir / "visualizations"
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Load summary if it exists
        self.summary_path = self.verification_dir / "verification_summary.json"
        self.summary = self._load_summary() if self.summary_path.exists() else None
        
        # Color scheme
        self.colors = {
            'ast': '#2C82C9',   # Blue
            'pattern': '#2CC990', # Green
            'llm': '#EEE657',   # Yellow
            'all': '#FC6042'    # Red
        }
    
    def _load_summary(self) -> Dict[str, Any]:
        """Load the verification summary JSON file"""
        with open(self.summary_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def plot_overall_scores(self):
        """Plot overall verification scores for each method and file"""
        if not self.summary:
            print("Summary file not found")
            return
        
        # Prepare data
        files = []
        methods = ['ast', 'pattern', 'llm', 'all']
        method_scores = {method: [] for method in methods}
        
        for file_name, file_data in self.summary['results'].items():
            files.append(file_name)
            for method in methods:
                if method in file_data['methods']:
                    method_scores[method].append(file_data['methods'][method]['overall_score'])
                else:
                    method_scores[method].append(0)
        
        # Plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        x = np.arange(len(files))
        width = 0.2
        offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
        
        for i, method in enumerate(methods):
            ax.bar(x + offsets[i], method_scores[method], width, label=method, color=self.colors[method])
        
        ax.set_xlabel('Files')
        ax.set_ylabel('Overall Score (%)')
        ax.set_title('Verification Scores by Method and File')
        ax.set_xticks(x)
        ax.set_xticklabels(files, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save
        chart_path = self.output_dir / "overall_scores.png"
        plt.savefig(chart_path)
        plt.close()
        
        return chart_path
    
    def plot_field_success_rates(self):
        """Plot success rates for each extraction field"""
        if not self.summary:
            print("Summary file not found")
            return
        
        # Prepare data
        methods = ['ast', 'pattern', 'llm', 'all']
        fields = ['title', 'abstract', 'year', 'main_text', 'display_equations', 'inline_equations', 'citations', 'tables']
        
        success_rates = {method: {field: 0 for field in fields} for method in methods}
        file_count = 0
        
        for file_name, file_data in self.summary['results'].items():
            file_count += 1
            for method in methods:
                if method in file_data['methods']:
                    method_data = file_data['methods'][method]
                    for field in fields:
                        if field in method_data['verifications'] and method_data['verifications'][field]['is_valid']:
                            success_rates[method][field] += 1
        
        # Calculate percentages
        for method in methods:
            for field in fields:
                success_rates[method][field] = (success_rates[method][field] / file_count) * 100
        
        # Plot
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(fields))
        width = 0.2
        offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
        
        for i, method in enumerate(methods):
            field_rates = [success_rates[method][field] for field in fields]
            ax.bar(x + offsets[i], field_rates, width, label=method, color=self.colors[method])
        
        ax.set_xlabel('Extraction Fields')
        ax.set_ylabel('Success Rate (%)')
        ax.set_title('Field Extraction Success Rates by Method')
        ax.set_xticks(x)
        ax.set_xticklabels(fields, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save
        chart_path = self.output_dir / "field_success_rates.png"
        plt.savefig(chart_path)
        plt.close()
        
        return chart_path
    
    def plot_method_comparison(self):
        """Plot a comparison of different extraction methods"""
        if not self.summary:
            print("Summary file not found")
            return
        
        # Prepare data
        methods = ['ast', 'pattern', 'llm', 'all']
        method_scores = {method: [] for method in methods}
        
        for file_name, file_data in self.summary['results'].items():
            for method in methods:
                if method in file_data['methods']:
                    method_scores[method].append(file_data['methods'][method]['overall_score'])
        
        # Calculate statistics
        method_stats = {}
        for method in methods:
            if method_scores[method]:
                method_stats[method] = {
                    'mean': np.mean(method_scores[method]),
                    'median': np.median(method_scores[method]),
                    'min': np.min(method_scores[method]),
                    'max': np.max(method_scores[method])
                }
            else:
                method_stats[method] = {'mean': 0, 'median': 0, 'min': 0, 'max': 0}
        
        # Plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Bar chart for means
        method_means = [method_stats[method]['mean'] for method in methods]
        ax1.bar(methods, method_means, color=[self.colors[method] for method in methods])
        ax1.set_xlabel('Methods')
        ax1.set_ylabel('Mean Score (%)')
        ax1.set_title('Mean Verification Scores by Method')
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # Box plot for distributions
        box_data = [method_scores[method] for method in methods]
        box = ax2.boxplot(box_data, labels=methods, patch_artist=True)
        
        # Set box colors
        for i, method in enumerate(methods):
            box['boxes'][i].set_facecolor(self.colors[method])
        
        ax2.set_xlabel('Methods')
        ax2.set_ylabel('Score Distribution (%)')
        ax2.set_title('Score Distributions by Method')
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save
        chart_path = self.output_dir / "method_comparison.png"
        plt.savefig(chart_path)
        plt.close()
        
        return chart_path
    
    def plot_error_analysis(self):
        """Plot the most common error reasons"""
        if not self.summary:
            print("Summary file not found")
            return
        
        # Prepare data
        error_reasons = {}
        methods = ['ast', 'pattern', 'llm', 'all']
        
        for file_name, file_data in self.summary['results'].items():
            for method in methods:
                if method in file_data['methods']:
                    method_data = file_data['methods'][method]
                    for field, field_verification in method_data['verifications'].items():
                        if not field_verification['is_valid']:
                            reason = field_verification['reason']
                            if reason not in error_reasons:
                                error_reasons[reason] = 0
                            error_reasons[reason] += 1
        
        # Sort reasons by frequency
        sorted_reasons = sorted(error_reasons.items(), key=lambda x: x[1], reverse=True)
        top_reasons = sorted_reasons[:10]  # Top 10 reasons
        
        # Plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        reasons = [reason for reason, count in top_reasons]
        counts = [count for reason, count in top_reasons]
        
        ax.barh(reasons, counts, color='#FF6B6B')
        ax.set_xlabel('Count')
        ax.set_ylabel('Error Reason')
        ax.set_title('Top Error Reasons Across All Methods')
        ax.grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        # Save
        chart_path = self.output_dir / "error_analysis.png"
        plt.savefig(chart_path)
        plt.close()
        
        return chart_path
    
    def generate_visualizations(self):
        """Generate all visualizations"""
        if not self.summary:
            print("Summary file not found. Cannot generate visualizations.")
            return
        
        print("Generating visualizations...")
        
        overall_chart = self.plot_overall_scores()
        print(f"Overall scores chart saved to: {overall_chart}")
        
        field_chart = self.plot_field_success_rates()
        print(f"Field success rates chart saved to: {field_chart}")
        
        method_chart = self.plot_method_comparison()
        print(f"Method comparison chart saved to: {method_chart}")
        
        error_chart = self.plot_error_analysis()
        print(f"Error analysis chart saved to: {error_chart}")
        
        print("All visualizations generated successfully!")


def main():
    """Main function to run the visualization"""
    parser = argparse.ArgumentParser(description='Visualize LaTeX extraction verification results')
    parser.add_argument('--verification-dir', type=str, required=True,
                        help='Directory containing verification results')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory to save visualizations (default: within verification-dir)')
    
    args = parser.parse_args()
    
    # Create and run visualizer
    visualizer = VerificationVisualizer(args.verification_dir, args.output_dir)
    visualizer.generate_visualizations()


if __name__ == "__main__":
    main() 