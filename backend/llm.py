"""
LLM factory — HuggingFace Inference API with Mistral-7B-Instruct.
Uses ChatHuggingFace which properly routes through the conversational API.
"""

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_openai import ChatOpenAI

from config import HUGGINGFACE_API_KEY, LLM_MODEL, MAX_NEW_TOKENS, TEMPERATURE


def get_llm(
    api_key: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_new_tokens: int | None = None,
):
    """
    Auto-detect provider:
    - hf_ → HuggingFace (existing logic)
    - sk- → OpenAI (new logic)
    """

    api_key = api_key or HUGGINGFACE_API_KEY

    # 🔥 NEW: OpenAI support (added on top)
    if api_key and api_key.startswith("sk-"):
        return ChatOpenAI(
            api_key=api_key,
            model="gpt-4o-mini",
            temperature=temperature or TEMPERATURE,
        )

    endpoint = HuggingFaceEndpoint(
        repo_id=model or LLM_MODEL,  
        huggingfacehub_api_token=api_key,
        task="conversational",
        max_new_tokens=max_new_tokens or MAX_NEW_TOKENS,
        temperature=temperature or TEMPERATURE,
        do_sample=True,
        repetition_penalty=1.1,
    )

    return ChatHuggingFace(
        llm=endpoint,
        huggingfacehub_api_token=api_key,
    )