#!/usr/bin/env python3
"""
LLM1 - Gemini API Call Function
Simple function to make Gemini API calls with configurable parameters.
"""

import base64
import os
from pathlib import Path
from typing import List, Union, Optional
from google import genai
from google.genai import types


def generate_marking_scheme(
    api_key: str,
    system_instruction: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    thinking_budget: int,
    response_mime_type: str,
    stream: bool,
    text_input: Optional[str] = None,
    image_paths: Optional[List[str]] = None,
    response_schema: Optional[dict] = None
) -> Union[tuple[str, types.UsageMetadata], None]:
    """
    Generate a marking scheme using Gemini API.
    
    Args:
        api_key: Gemini API key
        system_instruction: System instruction for the model
        model: Gemini model to use (e.g., "gemini-2.5-flash")
        temperature: Temperature for generation (0.0-1.0)
        max_output_tokens: Maximum tokens in response
        thinking_budget: Budget for thinking process
        response_mime_type: MIME type for response (e.g., "text/plain", "application/json", "text/x.enum")
        stream: Whether to stream the response (True) or return complete response (False)
        text_input: Text description of the question or additional context (optional)
        image_paths: List of paths to image files containing questions (optional)
        response_schema: Schema for structured output when response_mime_type is "application/json" or "text/x.enum" (optional)
        
    Returns:
        A tuple of (marking scheme, usage_metadata) if stream=False, None if stream=True
    """
    try:
        # Initialize client
        client = genai.Client(api_key=api_key)
        
        # Create content parts
        parts = []
        
        # Add text input if provided
        if text_input:
            parts.append(types.Part.from_text(text=text_input))
        
        # Add images if provided
        if image_paths:
            for image_path in image_paths:
                if not Path(image_path).exists():
                    raise FileNotFoundError(f"Image file not found: {image_path}")
                
                # Determine MIME type based on file extension
                ext = Path(image_path).suffix.lower()
                mime_type_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp',
                    '.heic': 'image/heic',
                    '.heif': 'image/heif'
                }
                
                mime_type = mime_type_map.get(ext, 'image/jpeg')
                
                # Read and add image using the correct pattern from official docs
                with open(image_path, 'rb') as image_file:
                    image_bytes = image_file.read()
                
                # Use the official pattern: types.Part.from_bytes()
                parts.append(types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                ))
        
        if not parts:
            raise ValueError("At least one of text_input or image_paths must be provided")
        
        # Create contents
        contents = [
            types.Content(
                role="user",
                parts=parts
            )
        ]
        
        # Configure generation
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(
                thinking_budget=thinking_budget,
            ),
            response_mime_type=response_mime_type,
            system_instruction=[
                types.Part.from_text(text=system_instruction)
            ],
        )
        
        # Add response schema if provided and appropriate mime type
        if response_schema:
            if response_mime_type in ["application/json", "text/x.enum"]:
                generate_content_config.response_schema = response_schema
            else:
                print("Warning: response_schema provided but response_mime_type is not 'application/json' or 'text/x.enum'. Schema will be ignored.")
        elif response_mime_type in ["application/json", "text/x.enum"]:
            print("Warning: response_mime_type is set for structured output but no response_schema provided. Results may be inconsistent.")
        
        if stream:
            # Stream the response
            print("Generating marking scheme...\n")
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                print(chunk.text, end="", flush=True)
            print("\n")  # Add final newline
            return None
        else:
            # Get complete response
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )
            print("Thoughts tokens:",response.usage_metadata.thoughts_token_count)
            print("Output tokens:",response.usage_metadata.candidates_token_count)
            print("Prompt tokens:",response.usage_metadata.prompt_token_count)
            # print(max_output_tokens)
            # print(thinking_budget)
            # print(text_input)
            # print(model)
            # print(text_input)
            # # print(response)
            # print(response.text)
            return (response.text, response.usage_metadata)
            
    except Exception as e:
        print(f"Error generating marking scheme: {e}")
        raise


def main():
    """Simple test function."""
    print("LLM1 API Function")
    print("This module contains the generate_marking_scheme function.")
    print("Use example_usage.py for complete examples.")


if __name__ == "__main__":
    main()
