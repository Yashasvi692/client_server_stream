import httpx
from .base import StreamPlugin


class LLMDemoPlugin(StreamPlugin):
    name = "llm_demo"

    async def stream(self, prompt: str):
        print("CALLING HF SERVICE:", prompt)

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                "https://unirritable-onomatopoetically-donna.ngrok-free.dev/generate",
                headers={"ngrok-skip-browser-warning": "true"},
                json={"prompt": prompt},
            ) as response:

                async for chunk in response.aiter_text():
                    if chunk.strip():
                        print("TOKEN:", chunk)
                        yield chunk
