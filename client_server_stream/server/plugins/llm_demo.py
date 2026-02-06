import asyncio
from .base import StreamPlugin
import asyncio
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread
import torch


class LLMDemoPlugin(StreamPlugin):
    name = "llm_demo"

    def __init__(self):
        print("Loading HF model...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            device_map="auto",
            torch_dtype=torch.float32
        )

    async def stream(self, prompt: str):
        print("HF STREAM:", prompt)

        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True
        )

        inputs = self.tokenizer(prompt, return_tensors="pt")

        thread = Thread(
            target=self.model.generate,
            kwargs=dict(
                **inputs,
                streamer=streamer,
                max_new_tokens=100
            )
        )
        thread.start()

        for token in streamer:
            await asyncio.sleep(0)
            yield token
