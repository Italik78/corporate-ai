import httpx

class LLMClient:
    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/models")
            if response.status_code != 200:
                return False
            return any(item.get("id") == self.model for item in response.json().get("data", []))
        except Exception:
            return False

    async def chat(self, messages: list[dict], temperature: float = 0.0, max_tokens: int = 1024) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            )
            response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
