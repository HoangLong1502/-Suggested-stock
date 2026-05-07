import httpx

from app.core.config import settings


class OllamaProvider:
    def __init__(self) -> None:
        self.base_url = settings.ollama_url.rstrip('/')
        self.models = ['deepseek-r1:7b', 'llama3:8b', 'qwen2.5']

    async def complete(self, prompt: str, model: str | None = None) -> str:
        async with httpx.AsyncClient(timeout=20.0) as client:
            model_name = model or self.models[0]
            try:
                url = f'{self.base_url}/v1/completions'
                response = await client.post(
                    url,
                    json={
                        'model': model_name,
                        'prompt': prompt,
                        'max_tokens': 250,
                        'temperature': 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get('choices', [{}])[0].get('message', {}).get('content', '') or data.get('choices', [{}])[0].get('text', '')
            except Exception:
                if model_name != self.models[-1]:
                    return await self.complete(prompt, model=self.models[-1])
                return 'Unable to complete reasoning with local LLM.'


llm_provider = OllamaProvider()
