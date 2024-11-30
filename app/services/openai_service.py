from typing import Dict, List
from openai import OpenAI
from flask import current_app
import re
import tiktoken

class OpenAIService:
    def __init__(self):
        self.model = "gpt-4"
        self.max_tokens = 8192  # GPT-4's context limit
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self._load_guardrails()
    
    def _load_guardrails(self):
        """Load predefined guardrails for content filtering."""
        self.guardrails = {
            'irrelevant_patterns': [
                r'i don\'t know',
                r'cannot answer',
                r'no information',
                r'not mentioned',
                r'not specified'
            ],
            'inappropriate_patterns': [
                r'confidential',
                r'private',
                r'classified',
            ]
        }
    
    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text."""
        return len(self.encoding.encode(text))
    
    def _trim_context(self, context_parts: List[Dict], question: str, max_tokens: int) -> str:
        """
        Trim context to fit within token limit while keeping most relevant parts.
        """
        # Calculate tokens for question and system message
        system_message = "You are a precise document assistant that provides well-sourced answers."
        base_tokens = self._count_tokens(system_message + question) + 200  # Buffer for formatting
        
        available_tokens = max_tokens - base_tokens
        current_tokens = 0
        selected_parts = []
        
        # Sort context parts by relevance score
        sorted_parts = sorted(context_parts, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        for part in sorted_parts:
            part_text = f"""Content from {part['source']['document']} (ID: {part['source']['paragraph_id']}):
{part['content']}\n\n"""
            part_tokens = self._count_tokens(part_text)
            
            if current_tokens + part_tokens <= available_tokens:
                selected_parts.append(part_text)
                current_tokens += part_tokens
            else:
                break
        
        return "\n".join(selected_parts)

    def _check_response_validity(self, response: str) -> bool:
        """Check if response passes guardrail checks."""
        for pattern in self.guardrails['irrelevant_patterns']:
            if re.search(pattern, response.lower()):
                return False
        
        for pattern in self.guardrails['inappropriate_patterns']:
            if re.search(pattern, response.lower()):
                return False
        
        return True
    
    def generate_answer(self, question: str, relevant_sections: List[Dict]) -> Dict:
        """Generate an answer using OpenAI API with context management."""
        client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
        
        if not relevant_sections:
            return {
                'status': 'no_relevant_content',
                'message': 'No relevant information found in the documents.'
            }
        
        # Trim context to fit within token limits
        context = self._trim_context(relevant_sections, question, self.max_tokens)
        
        prompt = f"""
Based on the following context, answer the question concisely and precisely.
Include specific source references using the provided paragraph IDs.
If you cannot answer the question based on the context, state that clearly.

Context:
{context}

Question: {question}

Requirements:
1. Be concise and precise
2. Reference specific sources using paragraph IDs
3. Only include information from the provided context
4. If the question cannot be fully answered from the context, state that clearly
"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise document assistant that provides well-sourced answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            
            if not self._check_response_validity(answer):
                return {
                    'status': 'invalid_response',
                    'message': 'The system could not generate a valid response.'
                }
            
            # Only include sources that were actually used in the trimmed context
            used_sources = [
                {
                    'document': section['source']['document'],
                    'paragraph_id': section['source']['paragraph_id'],
                    'char_start': section['source']['char_start'],
                    'char_end': section['source']['char_end']
                }
                for section in relevant_sections
                if section['content'] in context
            ]
            
            return {
                'status': 'success',
                'answer': answer,
                'sources': used_sources
            }
            
        except Exception as e:
            current_app.logger.error(f"OpenAI API error: {str(e)}")
            return {
                'status': 'error',
                'message': 'An error occurred while generating the answer.'
            }