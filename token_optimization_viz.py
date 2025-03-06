#!/usr/bin/env python
"""
Visualizes the token optimization system and shows token savings.
"""

import sys
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Token usage data
    formats = ['COMPACT', 'SUMMARY', 'FULL']
    token_usage = [120, 221, 619]
    
    # Calculate savings
    full_tokens = token_usage[2]
    savings = [(full_tokens - tokens) / full_tokens * 100 for tokens in token_usage]
    
    # Create figure and axis
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot token usage
    bars = ax1.bar(formats, token_usage, color=['#5cb85c', '#f0ad4e', '#d9534f'])
    ax1.set_ylabel('Token Count')
    ax1.set_title('Token Usage by Format Type', fontsize=14)
    
    # Add token count labels
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', fontsize=12)
    
    # Plot token savings compared to FULL
    savings_percent = savings
    colors = ['#5cb85c', '#f0ad4e', '#d9534f']
    bars2 = ax2.bar(formats, savings_percent, color=colors)
    ax2.set_ylabel('Percentage Saved (%)')
    ax2.set_title('Token Savings vs FULL Format', fontsize=14)
    
    # Add percentage labels
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=12)
    
    # Set y-axis limit for the savings chart
    ax2.set_ylim(0, 100)
    
    # Add overall title
    plt.suptitle('Deep Research Token Optimization', fontsize=16)
    
    # Add text explaining the formats
    explanation = """
    FORMAT DETAILS:
    
    COMPACT (120 tokens): Essential conclusions only
    - Key findings as simple text list
    - Minimal metadata
    
    SUMMARY (221 tokens): Moderate detail
    - Key findings with confidence scores
    - Evidence summary
    - Basic exploration statistics
    
    FULL (619 tokens): Complete details
    - Full query tree
    - Detailed findings with metadata
    - All evidence items
    - Complete exploration paths
    """
    
    plt.figtext(0.5, -0.05, explanation, ha='center', fontsize=10, 
                bbox={'facecolor': 'lightgray', 'alpha': 0.5, 'pad': 10})
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    # Save the figure
    plt.savefig('token_optimization.png', dpi=300, bbox_inches='tight')
    print("Visualization saved as 'token_optimization.png'")
    
    # Show the figure if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--show':
        plt.show()

if __name__ == "__main__":
    main()
