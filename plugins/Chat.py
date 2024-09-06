import asyncio
import json
from alicebot import Plugin
from openai import AsyncOpenAI
from alicebot.adapter.mirai import MiraiMessageSegment
from DuelFrontend import to_text
from authconfigs import gen_quote

with open('plugins/data/openai-config.json', 'r') as f:
    config = json.load(f)
    api_key = config['api_key']
    base_url = config['base_url']
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )

locks = {}

async def chat(messages: list):
    completion = await client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    message = completion.choices[0].message.content
    return message


class Chat(Plugin):
    async def handle(self) -> None:
        if self.event.sender.group.id not in locks:
            locks[self.event.sender.group.id] = asyncio.Lock()
        lock = locks[self.event.sender.group.id]
        if lock.locked():
            await self.event.reply("每次回答后要等待5s")
            return
        async with lock:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            text = text[6:]
            messages = [{"role": "system", "content": text}]
            response = await chat(messages)
            if len(response) > 150:
                response = gen_quote("Chat", "Chat", [response])
            await self.event.reply(response)
            await asyncio.sleep(5)


    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith('/chat') and self.event.type == 'GroupMessage'
        except:
            return False