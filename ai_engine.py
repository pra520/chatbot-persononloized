"""
AI Engine - OpenRouter Integration + Prompt Engineering
Handles all LLM communication with structured prompt templates
"""

import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class AIEngine:
    """
    Core AI reasoning engine.
    Constructs expert-level prompts and communicates with OpenRouter API.
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    # GPT-4o-mini: fast, cheap, very capable
    DEFAULT_MODEL   = "openai/gpt-4o-mini"

    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    def _build_system_prompt(self, bot_role: str, business_name: str, context: str) -> str:
        """
        Construct a high-quality, anti-hallucination system prompt.

        Structure:
        1. Role definition      → Establishes AI identity
        2. Behavior rules       → Controls tone and accuracy
        3. Knowledge context    → Injects user data
        4. Safety instructions  → Prevents hallucination
        """

        context_section = ""
        if context:
            context_section = f"""
## 📂 KNOWLEDGE BASE (Use ONLY this data to answer questions)
The following information has been provided by {business_name}. 
Base your answers EXCLUSIVELY on this data when relevant:

{context[:4000]}

---
"""

        system_prompt = f"""You are an expert {bot_role} for **{business_name}**.

## YOUR IDENTITY
- You are a professional, knowledgeable, and helpful AI assistant
- You represent {business_name} with the highest level of professionalism
- You speak clearly, concisely, and with expertise

## STRICT BEHAVIOR RULES
1. **Accuracy First**: NEVER make up facts, numbers, dates, or names
2. **Context Priority**: If knowledge base data is provided, use it as your PRIMARY source
3. **Honest Limitations**: If you don't know something, say "I don't have that information" — never guess
4. **Professional Tone**: Keep responses clear, helpful, and business-appropriate
5. **Concise Answers**: Provide focused answers — avoid unnecessary filler text
6. **No Speculation**: Do not speculate about topics outside your knowledge
7. **Structure**: Use bullet points and headers when the answer benefits from structure
{context_section}
## RESPONSE GUIDELINES
- If the user asks about uploaded documents, answer from the knowledge base only
- If no relevant data exists in the knowledge base, say so politely
- Always end with a helpful offer: "Is there anything else I can help you with?"
- Keep responses under 400 words unless complex detail is truly needed
"""
        return system_prompt.strip()

    def _format_history(self, history: List[Dict]) -> List[Dict]:
        """
        Convert internal history format to OpenRouter message format.
        Keeps last N turns to control token usage.
        """
        messages = []
        for turn in history:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        return messages

    def generate_response(
        self,
        user_message: str,
        context: str = "",
        history: List[Dict] = None,
        bot_role: str = "professional business assistant",
        business_name: str = "Our Company"
    ) -> str:
        """
        Main inference method.
        Builds prompt → Calls API → Returns clean response.
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured. Please check your .env file.")

        history = history or []

        # Build the full message chain
        system_prompt = self._build_system_prompt(bot_role, business_name, context)
        history_messages = self._format_history(history)

        messages = [
            {"role": "system", "content": system_prompt},
            *history_messages,
            {"role": "user", "content": user_message}
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://personabot.ai",
            "X-Title": "PersonaBot SaaS"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.4,       # Lower = more factual, less creative
            "top_p": 0.9,
            "frequency_penalty": 0.3  # Reduce repetition
        }

        try:
            response = requests.post(
                self.OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            # Log raw response for debugging
            logger.info(f"OpenRouter status: {response.status_code}")

            if response.status_code == 401:
                raise Exception(
                    "Invalid API key. Open backend/.env and make sure "
                    "OPENROUTER_API_KEY is set to your real key from openrouter.ai/keys"
                )
            if response.status_code == 429:
                raise Exception("Rate limit reached. Please wait a moment and try again.")
            if response.status_code == 402:
                raise Exception(
                    "Insufficient credits on OpenRouter. "
                    "Switch to a free model: set AI_MODEL=mistralai/mistral-7b-instruct:free in .env"
                )

            response.raise_for_status()
            result = response.json()

            # Some models return an error field instead of choices
            if "error" in result:
                err_msg = result["error"].get("message", str(result["error"]))
                raise Exception(f"OpenRouter model error: {err_msg}")

            if "choices" not in result or not result["choices"]:
                logger.error(f"Unexpected response: {result}")
                raise ValueError(f"Unexpected API response: {result}")

            content = result["choices"][0]["message"]["content"]
            return content.strip()

        except requests.exceptions.Timeout:
            raise Exception("AI service timeout (30s). Check your internet connection and try again.")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot reach OpenRouter API. Check your internet connection.")
        except Exception as e:
            logger.error(f"AI Engine error: {str(e)}")
            raise

    def test_connection(self) -> dict:
        """Quick connectivity + auth test — call this to validate the API key"""
        try:
            result = self.generate_response(
                user_message="Say 'API connection successful' and nothing else.",
                context="",
                history=[],
                bot_role="assistant",
                business_name="Test"
            )
            return {"ok": True, "response": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}
