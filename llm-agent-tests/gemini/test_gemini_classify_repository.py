import os
import unittest
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
# Make sure to import the specific exception if available, otherwise use string matching
from google.api_core.exceptions import ResourceExhausted 
from prometheus_swarm.tools.repo_operations.definitions import DEFINITIONS

load_dotenv()

class TestGeminiClassifyRepository(unittest.TestCase):
    def setUp(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            self.fail("GEMINI_API_KEY not found in .env file")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0.7, 
            google_api_key=self.api_key,
            max_retries=1 # Keep Langchain retries low to let our loop handle longer waits
        )
        self.tools = [DEFINITIONS["classify_repository"]]

    def test_classify_repository(self):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful assistant that can classify repositories."),
                ("user", "Use the classify_repository tool to classify this repository as a web application."),
            ]
        )
        chain = prompt_template | self.llm.bind_tools(tools=self.tools)
        
        max_custom_retries = 1 # Our custom retry attempts
        result = None
        for attempt in range(max_custom_retries + 1):
            try:
                result = chain.invoke({})
                break # Success
            except ResourceExhausted as e: # Catch the specific exception
                if attempt < max_custom_retries:
                    print(f"Rate limit reached (ResourceExhausted). Waiting 60 seconds before retrying... (Attempt {attempt + 1}/{max_custom_retries + 1})")
                    time.sleep(60)
                    continue # Make sure this is uncommented and active
                else:
                    print(f"Test failed after {max_custom_retries + 1} attempts due to ResourceExhausted: {e}")
                    self.fail(f"Test failed due to ResourceExhausted after retries: {e}")
            except Exception as e: # Catch other exceptions
                if "tool_code_execution_error" in str(e):
                    self.fail(f"Tool execution failed: {e}")
                else:
                    # For any other exception, fail immediately
                    self.fail(f"An unexpected error occurred: {e}") 
        
        if result is None: 
            # This case should ideally be covered by the loop's else or specific exception handling
            self.fail("No result obtained from LLM call after all retries.")

        tool_calls = result.additional_kwargs.get("tool_calls", [])
        self.assertGreater(len(tool_calls), 0, "No tool calls made by the LLM")

        tool_call = tool_calls[0]
        self.assertEqual(tool_call["name"], "classify_repository")
        self.assertIn("repo_type", tool_call["args"])
        self.assertEqual(tool_call["args"]["repo_type"], "web_application")

if __name__ == "__main__":
    unittest.main() 