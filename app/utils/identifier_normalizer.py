"""
Utility module for normalizing question identifiers across the application.
This ensures consistent identifier format by stripping 'ANS-' prefix when present.
"""

import re
from typing import Union


def normalize_identifier(identifier: Union[str, int]) -> str:
    """
    Normalize a question identifier by stripping 'ANS-' prefix if present.
    
    Args:
        identifier: The identifier to normalize (can be string or int)
        
    Returns:
        Normalized identifier as string (just the number)
        
    Examples:
        normalize_identifier("ANS-1") -> "1"
        normalize_identifier("ANS-15") -> "15"
        normalize_identifier("1") -> "1"
        normalize_identifier(1) -> "1"
    """
    if identifier is None:
        return ""
    
    # Convert to string if it's an integer
    identifier_str = str(identifier).strip()
    
    # Strip 'ANS-' prefix if present
    if identifier_str.upper().startswith("ANS-"):
        return identifier_str[4:]  # Remove "ANS-" prefix
    
    return identifier_str


def is_ans_identifier(identifier: Union[str, int]) -> bool:
    """
    Check if an identifier has the 'ANS-' prefix.
    
    Args:
        identifier: The identifier to check
        
    Returns:
        True if identifier starts with 'ANS-', False otherwise
    """
    if identifier is None:
        return False
    
    identifier_str = str(identifier).strip()
    return identifier_str.upper().startswith("ANS-")


def extract_number_from_identifier(identifier: Union[str, int]) -> str:
    """
    Extract just the number part from an identifier.
    
    Args:
        identifier: The identifier to extract number from
        
    Returns:
        The number as string
        
    Examples:
        extract_number_from_identifier("ANS-1") -> "1"
        extract_number_from_identifier("Question 15") -> "15"
        extract_number_from_identifier("1") -> "1"
    """
    if identifier is None:
        return ""
    
    identifier_str = str(identifier).strip()
    
    # First try to strip ANS- prefix
    if identifier_str.upper().startswith("ANS-"):
        return identifier_str[4:]
    
    # Extract any number from the string
    numbers = re.findall(r'\d+', identifier_str)
    if numbers:
        return numbers[0]
    
    return identifier_str


def normalize_identifier_list(identifiers: list) -> list:
    """
    Normalize a list of identifiers.
    
    Args:
        identifiers: List of identifiers to normalize
        
    Returns:
        List of normalized identifiers
    """
    return [normalize_identifier(identifier) for identifier in identifiers]


def normalize_identifier_dict(identifier_dict: dict) -> dict:
    """
    Normalize identifiers in a dictionary where keys are identifiers.
    
    Args:
        identifier_dict: Dictionary with identifiers as keys
        
    Returns:
        Dictionary with normalized identifiers as keys
    """
    return {normalize_identifier(key): value for key, value in identifier_dict.items()} 