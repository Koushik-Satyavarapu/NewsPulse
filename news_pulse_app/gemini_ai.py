import os
from dotenv import load_dotenv

# Try to import google generative ai; if missing, functions will raise helpful error.

# Compatibility wrapper: prefer the new Google GenAI SDK ('google-genai') but allow legacy imports.
try:
    # New SDK: `pip install google-genai`
    from google import genai as new_genai  # modern import
except Exception:
    new_genai = None

# legacy import (older packages)
try:
    import google.generativeai as legacy_genai
except Exception:
    legacy_genai = None

# Choose the SDK object name 'genai_client' for convenience:
genai = new_genai or legacy_genai

load_dotenv()

# Use GEMINI_API_KEY in .env
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # updated default model

if genai and API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception:
        pass  # Ignore configure differences

def _extract_text_from_response(resp):
    """Attempt to extract generated text from several possible response shapes."""
    if not resp:
        return ""
    if hasattr(resp, 'text'):
        try:
            return resp.text if isinstance(resp.text, str) else str(resp.text)
        except Exception:
            pass
    try:
        if isinstance(resp, dict):
            if "candidates" in resp and resp["candidates"]:
                c = resp["candidates"][0]
                return c.get("content") or c.get("text") or str(c)
            if "output" in resp:
                out = resp.get("output")
                if isinstance(out, list) and out:
                    return out[0].get("content") or str(out[0])
                if isinstance(out, str):
                    return out
            return str(resp)
    except Exception:
        pass
    return str(resp)

def summarize_text(text, max_tokens=300):
    """Summarize given text using Gemini. Returns a string summary or an error message."""
    if not text or not text.strip():
        return ""
    if genai is None:
        return "Gemini client (google.generativeai) not installed. Install with: pip install google-generativeai"
    if not API_KEY:
        return "Missing GEMINI_API_KEY environment variable."

    prompt = f"Summarize the following news article in a concise paragraph (max {max_tokens} tokens):\n\n{text}"
    try:
        try:
            model = genai.GenerativeModel(MODEL)
            resp = model.generate_content(prompt)
            return _extract_text_from_response(resp)
        except Exception:
            pass
        try:
            resp = genai.generate_content(model=MODEL, contents=prompt)
            return _extract_text_from_response(resp)
        except Exception as e:
            return f"Error during summarization: {str(e)}"
    except Exception as e:
        return f"Error during summarization: {str(e)}"

def generate_questions(text, num_questions=5):
    """Generate study/discussion questions from text using Gemini."""
    if not text or not text.strip():
        return ""
    if genai is None:
        return "Gemini client (google.generativeai) not installed. Install with: pip install google-generativeai"
    if not API_KEY:
        return "Missing GEMINI_API_KEY environment variable."

    prompt = f"Generate {num_questions} clear, concise, thought-provoking study questions based on the following article:\n\n{text}\n\nReturn each question on a separate line."
    try:
        try:
            model = genai.GenerativeModel(MODEL)
            resp = model.generate_content(prompt)
            return _extract_text_from_response(resp)
        except Exception:
            pass
        try:
            resp = genai.generate_content(model=MODEL, contents=prompt)
            return _extract_text_from_response(resp)
        except Exception as e:
            return f"Error during question generation: {str(e)}"
    except Exception as e:
        return f"Error during question generation: {str(e)}"

def ask_question(article_text: str, question: str, max_output_tokens: int = 400) -> str:
    """Answer a user question given the article text using Gemini/GenAI."""
    if not article_text:
        return ""
    if not genai:
        return "Gemini client not installed. Please pip install google-genai and set GEMINI_API_KEY in your .env."

    prompt = f"""You are a helpful assistant. Use the article below as the source. 
Answer the user's question succinctly and clearly. If you do not know, say you don't know.

Article:
{article_text}

User question:
{question}

Answer:"""

    # Try new SDK usage first
    try:
        if new_genai:
            client = new_genai.Client(api_key=API_KEY)
            resp = client.models.generate_content(model=MODEL, contents=prompt)
            try:
                client.close()
            except Exception:
                pass
            return _extract_text_from_response(resp).strip()
    except Exception:
        pass

    # Try legacy SDK
    try:
        if legacy_genai:
            legacy_genai.configure(api_key=API_KEY)
            model_obj = legacy_genai.GenerativeModel(MODEL)
            resp = model_obj.generate_content(prompt)
            return _extract_text_from_response(resp).strip()
    except Exception as e:
        return f"Gemini call failed: {e}"

    return "Gemini call failed: unsupported SDK or configuration."
