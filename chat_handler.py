# chat_handler_v3_4.py
"""
ChatHandler v3.4
Changes:
- Structured markdown answer formatting
- Cleaner prompt construction
- Stable output for consistent educational tone
"""

from typing import Tuple, List, Dict, Optional
from vector_store import VectorStore
import time

class ChatHandler:
    def __init__(self, model, vector_store: VectorStore, auto_summarize_tokens: int = 250):
        self.model = model
        self.vector_store = vector_store
        self.conversation_history: List[Dict] = []
        self.auto_summarize_tokens = auto_summarize_tokens

    def _call_model(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
        try:
            if hasattr(self.model, "generate_content"):
                resp = self.model.generate_content(prompt)
                if hasattr(resp, "text"): return resp.text
                if isinstance(resp, dict) and "text" in resp: return resp["text"]
        except Exception:
            pass
        try:
            if hasattr(self.model, "generate_text"):
                return self.model.generate_text(prompt, max_tokens=max_tokens, temperature=temperature)
        except Exception:
            pass
        try:
            if callable(self.model):
                out = self.model(prompt)
                if isinstance(out, str): return out
                if isinstance(out, dict) and "text" in out: return out["text"]
        except Exception:
            pass
        raise RuntimeError("Model invocation failed. Ensure compatibility.")

    def _build_prompt(self, query: str, context: str, memory: Optional[str] = None) -> str:
        memory_txt = f"CONVERSATION HISTORY:\n{memory}\n\n" if memory else ""
        prompt = (
            f"{memory_txt}You are Smart Study Buddy — an accurate, concise study assistant.\n"
            "Use ONLY the provided context. If unavailable, state that clearly.\n\n"
            "CONTEXT:\n"
            f"{context}\n\n"
            "QUESTION:\n"
            f"{query}\n\n"
            "INSTRUCTIONS:\n"
            "1) Be concise and educational.\n"
            "2) Use only context content.\n"
            "3) Format answers clearly in Markdown:\n"
            "   - Use headings (###) for main ideas.\n"
            "   - Bullet points or numbered lists for clarity.\n"
            "   - Bold key terms.\n"
            "4) Include page numbers if relevant.\n\n"
            "### Structured Answer:\n"
        )
        return prompt

    def get_response(self, query: str, k: int = 3, memory: Optional[str] = None, max_context_chars: int = 3000) -> Tuple[str, List[Dict]]:
        start_tot = time.time()
        context, sources = self.vector_store.get_context_for_query(query, k=k, max_context_length=max_context_chars)
        if not context.strip():
            return ("I couldn’t find relevant information in the uploaded documents.", [])

        prompt = self._build_prompt(query, context, memory)
        start_gen = time.time()
        try:
            response_text = self._call_model(prompt)
            if not isinstance(response_text, str):
                response_text = str(response_text)
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")
        gen_time = time.time() - start_gen

        if len(response_text.split()) > self.auto_summarize_tokens:
            try:
                summary_prompt = f"Summarize in under 100 words:\n\n{response_text}"
                summary = self._call_model(summary_prompt, max_tokens=150)
                response_text = f"{summary}\n\n---\n**Full Answer:**\n\n{response_text}"
            except Exception:
                pass

        entry = {
            "query": query,
            "response": response_text,
            "sources": sources,
            "t_generation_s": round(gen_time, 3),
            "timestamp": time.time()
        }
        self.conversation_history.append(entry)

        return response_text, sources

    def get_conversation_summary(self) -> str:
        if not self.conversation_history:
            return "No conversation yet."
        out = []
        for i, h in enumerate(self.conversation_history[-6:], start=1):
            out.append(f"{i}. Q: {h['query']}\nA: {h['response'][:250]}...")
        return "\n\n".join(out)

    def clear_history(self):
        self.conversation_history = []
