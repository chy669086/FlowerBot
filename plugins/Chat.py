import asyncio
import json
from alicebot import Plugin
from openai import AsyncOpenAI
from DuelFrontend import to_text
from authconfigs import MAINPATH, self_QQ
import imgkit
import pypandoc

with open('plugins/data/openai-config.json', 'r') as f:
    config = json.load(f)
    api_key = config['api_key']
    base_url = config['base_url']
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )


path_wk = r'/usr/bin/wkhtmltoimage'
md_file = MAINPATH + 'plugins/data/chat.md'
html_file = MAINPATH + 'plugins/data/chat.html'
image_file = MAINPATH + 'plugins/data/chat.png'

write_lock = asyncio.Lock()

def html_to_image(html_file, image_file):
    # 将HTML转换为图片
    options = {
        'format': 'png',
        'encoding': 'UTF-8',
        'quiet': '',
        'disable-smart-width': ''
    }
    config = imgkit.config(wkhtmltoimage=path_wk)
    imgkit.from_file(html_file, image_file, options=options, config=config)


def markdown_to_image(mess: str):
    # 将Markdown文件转换为HTML
    extra_args = ['--from=markdown+tex_math_dollars']
    html_content = pypandoc.convert_text(mess, 'html', format='markdown+tex_math_dollars', outputfile=html_file, extra_args=extra_args)

    html_to_image(html_file, image_file)


locks = {}

chat_messages = {}

async def chat(text: str, group_id: int):
    if group_id not in chat_messages:
        chat_messages[group_id] = []
    messages = chat_messages[group_id]
    messages.append({"role": "user", "content": text})
    while True:
        try:
            completion = await client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            break
        except:
            if len(messages) == 1:
                messages = []
                raise Exception("牛魔的输入太长了")
            if len(messages) > 4:
                messages = messages[4:]
            else:
                messages = messages[2:]
    message = completion.choices[0].message.content
    messages.append({"role": "assistant", "content": message})
    return message

def get_mes(msg, image_file):
    return {
        "type": "Forward",
        "display": {
            "title": "Chat",
            "brief": "Chat",
            "source": "Chat",
            "preview": ["Chat"],
            "summary": "查看Chat"
        },
        "nodeList": [
            {
                "senderId": int(self_QQ),
                "time": 0,
                "senderName": "flower",
                "messageChain": [  { "type":"Image", "path": image_file }],
            },
            {
                "senderId": int(self_QQ),
                "time": 0,
                "senderName": "flower",
                "messageChain": [{"type": "Plain", "text": msg}],
            }
        ]
    }

class Chat(Plugin):
    async def handle(self) -> None:
        if self.event.sender.group.id not in locks:
            locks[self.event.sender.group.id] = asyncio.Lock()
        lock = locks[self.event.sender.group.id]
        if lock.locked():
            await self.event.reply("请等待上一次对话结束")
            return
        async with lock:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            if len(text) < 6:
                return

            text = text[6:]
            
            try:
                response = await chat(text, self.event.sender.group.id)
            except:
                self.event.reply("牛魔的输入太长了")
            response = response.replace('\\(', '$').replace('\\)', '$').replace('\\[', '$$').replace('\\]', '$$')
            async with write_lock:
                markdown_to_image(response)
                msg = get_mes(response, image_file)
                await self.event.reply(msg)


    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith('/chat') and self.event.type == 'GroupMessage'
        except:
            return False