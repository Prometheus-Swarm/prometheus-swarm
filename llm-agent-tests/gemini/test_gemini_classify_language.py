import os
import unittest
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from google.api_core.exceptions import ResourceExhausted
from prometheus_swarm.tools.repo_operations.definitions import DEFINITIONS

load_dotenv()

class TestGeminiClassifyLanguage(unittest.TestCase):
    def setUp(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            self.fail("GEMINI_API_KEY not found in .env file")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0.7, 
            google_api_key=self.api_key,
            max_retries=1 
        )
        self.tools = [DEFINITIONS["classify_language"]]

    def test_classify_language(self):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful assistant that can classify repository languages."),
                ("user", "Classify the language of this repository as Python."),
            ]
        )
        chain = prompt_template | self.llm.bind_tools(tools=self.tools)
        
        max_custom_retries = 1
        result = None
        for attempt in range(max_custom_retries + 1):
            try:
                result = chain.invoke({})
                break 
            except ResourceExhausted as e: 
                if attempt < max_custom_retries:
                    print(f"Rate limit reached (ResourceExhausted). Waiting 60 seconds before retrying... (Attempt {attempt + 1}/{max_custom_retries + 1})")
                    time.sleep(60)
                    continue 
                else:
                    print(f"Test failed after {max_custom_retries + 1} attempts due to ResourceExhausted: {e}")
                    self.fail(f"Test failed due to ResourceExhausted after retries: {e}")
            except Exception as e: 
                if "tool_code_execution_error" in str(e):
                    self.fail(f"Tool execution failed: {e}")
                # elif "ResourceExhausted" in str(e): # This was from before, now handled by specific catch
                #     self.skipTest(f"Skipping test due to API rate limits: {e}")
                else:
                    self.fail(f"An unexpected error occurred: {e}") 
        
        if result is None: 
            self.fail("No result obtained from LLM call after all retries.")

        tool_calls = result.additional_kwargs.get("tool_calls", [])
        self.assertGreater(len(tool_calls), 0, "No tool calls made by the LLM")

        tool_call = tool_calls[0]
        self.assertEqual(tool_call["name"], "classify_language")
        self.assertIn("language", tool_call["args"])
        self.assertEqual(tool_call["args"]["language"], "python")

if __name__ == "__main__":
    unittest.main() 