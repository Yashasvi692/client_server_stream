import asyncio
from .base import BasePlugin


class LLMDemoPlugin(BasePlugin):
    name = "llm_demo"

    async def stream(self, prompt: str):
        response = f"Simulated LLM response to: {prompt}"

        # simulate token streaming
        for word in response.split():
            await asyncio.sleep(0.3)
            yield word + " "
