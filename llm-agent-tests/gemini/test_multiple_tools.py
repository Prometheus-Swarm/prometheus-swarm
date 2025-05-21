#!/usr/bin/env python3
"""
Testing multiple types of tools with the FallbackGeminiClient.
"""

import os
from dotenv import load_dotenv
from prometheus_swarm.clients import setup_client

def main():
    # Load API key from environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("Error: GEMINI_API_KEY not found or is a placeholder.")
        print("Please set your Gemini API key in the .env file.")
        return
    
    print("Setting up fallback_gemini client to test multiple tools...")
    
    # Use the setup_client function to create the fallback_gemini client
    # Starting with gemini-2.0-flash to avoid rate limits
    client = setup_client("fallback_gemini", "gemini-2.0-flash")
    
    # Create a new conversation
    conversation_id = client.create_conversation()
    print(f"Created conversation with ID: {conversation_id}")
    
    # Test 1: classify_repository (repo_operations)
    test_repo_classification(client, conversation_id)
    
    # Test 2: classify_language (repo_operations)
    test_language_classification(client, conversation_id)
    
    # Test 3: classify_test_framework (repo_operations) 
    test_framework_classification(client, conversation_id)
    
    # Test 4: list_files (file_operations)
    test_list_files(client, conversation_id)
    
    # Test 5: review_file (general_operations)
    test_review_file(client, conversation_id)

def test_repo_classification(client, conversation_id):
    print("\n=== Testing classify_repository tool ===")
    
    prompt = """
    Based on the following repository characteristics, please classify it:
    - Python files with machine learning imports (scikit-learn, tensorflow)
    - Jupyter notebooks
    - Requirements.txt with data science packages
    - Data preprocessing scripts
    """
    
    try:
        response = client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            tools_required=True
        )
        
        # Check for tool calls
        found_tool_call = False
        if isinstance(response.get("content"), list):
            for item in response["content"]:
                if item.get("type") == "tool_call":
                    tool_call = item["tool_call"]
                    if tool_call["name"] == "classify_repository":
                        found_tool_call = True
                        print(f"✅ Success! Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                        break
        
        if not found_tool_call:
            print("❌ Failed: classify_repository tool call not found in response")
    
    except Exception as e:
        print(f"❌ Error testing classify_repository: {e}")

def test_language_classification(client, conversation_id):
    print("\n=== Testing classify_language tool ===")
    
    prompt = """
    Based on the following code characteristics, please classify the primary programming language:
    
    ```
    import pandas as pd
    import numpy as np
    from sklearn.model_selection import train_test_split
    
    # Load the data
    data = pd.read_csv('data.csv')
    
    # Split features and target
    X = data.drop('target', axis=1)
    y = data['target']
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    ```
    
    Please use the classify_language tool to determine the programming language.
    """
    
    try:
        response = client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            tools_required=True
        )
        
        # Check for tool calls
        found_tool_call = False
        if isinstance(response.get("content"), list):
            for item in response["content"]:
                if item.get("type") == "tool_call":
                    tool_call = item["tool_call"]
                    if tool_call["name"] == "classify_language":
                        found_tool_call = True
                        print(f"✅ Success! Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                        break
        
        if not found_tool_call:
            print("❌ Failed: classify_language tool call not found in response")
    
    except Exception as e:
        print(f"❌ Error testing classify_language: {e}")

def test_framework_classification(client, conversation_id):
    print("\n=== Testing classify_test_framework tool ===")
    
    prompt = """
    Based on the following test code, please identify the testing framework being used:
    
    ```
    import pytest
    from myapp import create_app
    
    @pytest.fixture
    def client():
        app = create_app()
        with app.test_client() as client:
            yield client
    
    def test_home_page(client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'Welcome' in response.data
    ```
    
    Please use the classify_test_framework tool to identify the testing framework.
    """
    
    try:
        response = client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            tools_required=True
        )
        
        # Check for tool calls
        found_tool_call = False
        if isinstance(response.get("content"), list):
            for item in response["content"]:
                if item.get("type") == "tool_call":
                    tool_call = item["tool_call"]
                    if tool_call["name"] == "classify_test_framework":
                        found_tool_call = True
                        print(f"✅ Success! Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                        break
        
        if not found_tool_call:
            print("❌ Failed: classify_test_framework tool call not found in response")
    
    except Exception as e:
        print(f"❌ Error testing classify_test_framework: {e}")

def test_list_files(client, conversation_id):
    print("\n=== Testing list_files tool ===")
    
    prompt = """
    I need to see the files in the current directory. 
    Please use the list_files tool to show me the files.
    The directory to check is "."
    """
    
    try:
        response = client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            tools_required=True
        )
        
        # Check for tool calls
        found_tool_call = False
        if isinstance(response.get("content"), list):
            for item in response["content"]:
                if item.get("type") == "tool_call":
                    tool_call = item["tool_call"]
                    if tool_call["name"] == "list_files":
                        found_tool_call = True
                        print(f"✅ Success! Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                        break
        
        if not found_tool_call:
            print("❌ Failed: list_files tool call not found in response")
    
    except Exception as e:
        print(f"❌ Error testing list_files: {e}")

def test_review_file(client, conversation_id):
    print("\n=== Testing review_file tool ===")
    
    prompt = """
    I need you to review a file for me. The file is called "test_multiple_tools.py".
    Please use the review_file tool to analyze it and provide feedback on the code quality, 
    potential issues, and suggestions for improvement.
    """
    
    try:
        response = client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            tools_required=True
        )
        
        # Check for tool calls
        found_tool_call = False
        if isinstance(response.get("content"), list):
            for item in response["content"]:
                if item.get("type") == "tool_call":
                    tool_call = item["tool_call"]
                    if tool_call["name"] == "review_file":
                        found_tool_call = True
                        print(f"✅ Success! Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                        break
        
        if not found_tool_call:
            print("❌ Failed: review_file tool call not found in response")
    
    except Exception as e:
        print(f"❌ Error testing review_file: {e}")

if __name__ == "__main__":
    main() 