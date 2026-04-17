#!/usr/bin/env python3
"""
Test script for the text analyzer function.
This demonstrates how to use the analyze_policy_text function.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.text_analyzer import analyze_policy_text

def test_with_sample_policy():
    """Test the analyzer with a sample insurance policy text."""
    
    sample_policy_text = """
    LIC JEEVAN ANAND POLICY DOCUMENT
    
    This is a 20-year endowment policy with a sum assured of Rs 10,00,000.
    The premium is payable for 15 years only. The policy provides life insurance 
    coverage along with savings benefits.
    
    KEY BENEFITS:
    - Maturity benefit includes sum assured plus reversionary bonus
    - Death benefit is payable to nominee immediately
    - Tax benefits are available under Section 80C of Income Tax Act
    - Guaranteed additions are provided at 5% per annum
    - Accidental benefit is double the sum assured
    
    EXCLUSIONS:
    - Suicide is not covered in the first year of the policy
    - War and nuclear risks are excluded from coverage
    - Claims related to criminal activities are not payable
    
    IMPORTANT CONDITIONS:
    - Surrender charges apply if policy is surrendered within 5 years
    - Loyalty additions are payable only if all premiums are paid regularly
    - Premium waiver is available subject to disability conditions
    - Policy loan facility is available after 3 years
    - Partial withdrawals are allowed only after 5 years
    
    The policy offers financial protection and helps in long-term wealth creation.
    Premium amounts are fixed for the entire term and do not increase.
    """
    
    print("=" * 60)
    print("TESTING INSURANCE POLICY TEXT ANALYZER")
    print("=" * 60)
    
    # Analyze the policy text
    result = analyze_policy_text(sample_policy_text)
    
    print("\n📋 POLICY SUMMARY:")
    print(result["policy_summary"])
    
    print("\n💰 KEY BENEFITS:")
    for i, benefit in enumerate(result["key_benefits"], 1):
        print(f"  {i}. {benefit}")
    
    print("\n⚠️  EXCLUSIONS:")
    for i, exclusion in enumerate(result["exclusions"], 1):
        print(f"  {i}. {exclusion}")
    
    print("\n🔍 HIDDEN CLAUSES:")
    for i, clause in enumerate(result["hidden_clauses"], 1):
        print(f"  {i}. {clause}")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    
    return result

def test_with_empty_text():
    """Test the analyzer with empty text."""
    print("\n" + "=" * 60)
    print("TESTING WITH EMPTY TEXT")
    print("=" * 60)
    
    result = analyze_policy_text("")
    
    print(f"Summary: {result['policy_summary']}")
    print(f"Benefits count: {len(result['key_benefits'])}")
    print(f"Exclusions count: {len(result['exclusions'])}")
    print(f"Hidden clauses count: {len(result['hidden_clauses'])}")

def test_with_malformed_text():
    """Test the analyzer with malformed text."""
    print("\n" + "=" * 60)
    print("TESTING WITH MALFORMED TEXT")
    print("=" * 60)
    
    malformed_text = "This is not a policy text. Just random words."
    result = analyze_policy_text(malformed_text)
    
    print(f"Summary: {result['policy_summary']}")
    print(f"Benefits: {result['key_benefits']}")
    print(f"Exclusions: {result['exclusions']}")
    print(f"Hidden clauses: {result['hidden_clauses']}")

if __name__ == "__main__":
    # Run all tests
    test_with_sample_policy()
    test_with_empty_text()
    test_with_malformed_text()
    
    print("\n✅ All tests completed successfully!")
