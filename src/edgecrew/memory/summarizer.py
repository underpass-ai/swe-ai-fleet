

class Summarizer:
    def summarize(self, texts: list[str], max_tokens: int = 512) -> str:
        # TODO: call a small local LLM; placeholder returns head of text.
        return (texts[0] if texts else "")[:max_tokens]
