import sys
import os
import re

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def strip_markdown_code_blocks(text: str) -> str:
    """
    Strip markdown code block delimiters (```) from the input text.
    
    Args:
        text (str): Input markdown text
    
    Returns:
        str: Text with code block delimiters removed, with normalized whitespace
    """
    # Use regex to remove code blocks
    # This handles multiple types of code blocks: ```lang, ```, ```
    pattern = r'```.*?```'
    # Remove code blocks
    stripped_text = re.sub(pattern, '', text, flags=re.DOTALL)
    
    # Normalize whitespace: remove multiple consecutive newlines
    stripped_text = re.sub(r'\n\s*\n', '\n', stripped_text)
    
    return stripped_text.strip()

def test_strip_markdown_code_blocks():
    """Test stripping of markdown code block delimiters"""
    # Test case 1: Simple code block
    input1 = """```
This is a code block
With multiple lines
```
Some other text"""
    expected1 = """Some other text"""
    assert strip_markdown_code_blocks(input1).strip() == expected1.strip()

    # Test case 2: Multiple code blocks
    input2 = """```python
def hello():
    print("world")
```
Some text
```json
{"key": "value"}
```
More text"""
    expected2 = """Some text
More text"""
    assert strip_markdown_code_blocks(input2).strip() == expected2.strip()

    # Test case 3: No code blocks
    input3 = """Just some plain text
With multiple lines"""
    assert strip_markdown_code_blocks(input3).strip() == input3.strip()

    # Test case 4: Empty string
    input4 = ""
    assert strip_markdown_code_blocks(input4) == ""

    # Test case 5: Only code blocks
    input5 = """```
Code block 1
```
```
Code block 2
```"""
    assert strip_markdown_code_blocks(input5) == "" 