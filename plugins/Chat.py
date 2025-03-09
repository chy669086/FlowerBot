import asyncio
import json
from alicebot import Plugin
from openai import AsyncOpenAI
import pypandoc
from DuelFrontend import to_text
from authconfigs import MAINPATH, self_QQ
import imgkit

with open("plugins/data/openai-config.json", "r") as f:
    config = json.load(f)
    api_key = config["api_key"]
    base_url = config["base_url"]
    model = config["model"]
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)


path_wk = "/usr/bin/wkhtmltoimage"
md_file = MAINPATH + "plugins/data/chat.md"
image_file = MAINPATH + "plugins/data/chat.png"

# 用于创建图像，防止冲突
write_lock = asyncio.Lock()
# 用于实现群聊之间的锁，防止一个群聊在回答之前多次问问题
locks = {}
# 存储群聊信息
chat_messages = {}



def html_to_image(html_content, image_file):
    # 将HTML转换为图片
    options = {
        "format": "png",
        "encoding": "UTF-8",
        "quiet": "",
        "disable-smart-width": "",
    }
    config = imgkit.config(wkhtmltoimage=path_wk)
    imgkit.from_string(html_content, image_file, options=options, config=config)


def markdown_to_image(mess: str):
    # 将Markdown文件转换为HTML
    extra_args = ["--from=markdown+tex_math_dollars"]
    html_content = pypandoc.convert_text(
        mess,
        "html",
        format="markdown+tex_math_dollars",
        extra_args=extra_args,
    )

    html_to_image(html_content, image_file)


async def chat(text: str, group_id: int):
    if group_id not in chat_messages:
        chat_messages[group_id] = []
    messages = chat_messages[group_id]
    if len(messages) > 20:
        messages = messages[4:]

    messages.append({"role": "user", "content": text})
    try:
        completion = await client.chat.completions.create(
            model=model, messages=messages
        )
    except BaseException as e:
        messages.pop()
        raise e
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
            "summary": "查看Chat",
        },
        "nodeList": [
            {
                "senderId": int(self_QQ),
                "time": 0,
                "senderName": "flower",
                "messageChain": [{"type": "Image", "path": image_file}],
            },
            {
                "senderId": int(self_QQ),
                "time": 0,
                "senderName": "flower",
                "messageChain": [{"type": "Plain", "text": msg}],
            },
        ],
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
            except BaseException as e:
                await self.event.reply(str(e))
                return
            response = (
                response.replace("\\(", "$")
                .replace("\\)", "$")
                .replace("\\[", "$$")
                .replace("\\]", "$$")
            )
            async with write_lock:
                markdown_to_image(response)
                msg = get_mes(response, image_file)
                await self.event.reply(msg)

    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith("/chat") and self.event.type == "GroupMessage"
        except:
            return False

