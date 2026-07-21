from ollama import chat

class GraniteClient:
    """
    Wrapper for the LLM.
    Currently uses Ollama locally.
    """

    def __init__(self, model: str = "llama3.2"):
        self.model = model

    def generate(self, prompt: str) -> str:
        response = chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response["message"]["content"]