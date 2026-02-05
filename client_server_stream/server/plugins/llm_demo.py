import asyncio
from .base import StreamPlugin


class LLMDemoPlugin(StreamPlugin):
    name = "llm_demo"

    async def stream(self, prompt: str):
        print("LLM STREAM CALLED WITH:", prompt)
        response = f"Simulated LLM response to: {prompt}"

        # simulate token streaming
        for word in response.split():
            print("LLM CHUNK:", word)
            await asyncio.sleep(0.3)
            yield word + " "
