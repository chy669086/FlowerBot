import asyncio
import datetime
import jieba
import numpy as np
import utils.ConfigReader as ConfigReader
import utils.DBHelper as WordDBHelper

from PIL import Image
from matplotlib import pyplot as plt
from wordcloud import WordCloud
from alicebot import Plugin
from authconfigs import MAINPATH
from alicebot.adapter.mirai import MiraiMessageSegment
from alicebot.adapter.apscheduler import scheduler_decorator


image_path = MAINPATH + "plugins/storage/wordCloud/bear.jpg"
image_save_path = MAINPATH + "plugins/storage/wordCloud/wordCloud.jpg"
stop_words_path = MAINPATH + "plugins/storage/wordCloud/hit_stopwords.txt"
new_words_path = MAINPATH + "plugins/storage/wordCloud/jieba_new_word.txt"
message_group_list_path = MAINPATH + "plugins/storage/message_group_list.txt"

message_group_list = ConfigReader.read_message_group_list()

lock = asyncio.Lock()

jieba.load_userdict(new_words_path)


def add_message(words: list, group_id: int):
    WordDBHelper.insert(group_id, " ".join(words), datetime.datetime.now())


def clear_message(group_id: int):
    WordDBHelper.delete_before_time(
        group_id, datetime.datetime.now() - datetime.timedelta(days=7)
    )


def participle(words: str) -> list:
    ls = jieba.lcut(words)
    return ls


def remove_stop_words(data: list) -> list:
    with open(stop_words_path, "r", encoding="utf-8") as file:
        stop_words = set([line.strip() for line in file.readlines()])

    value = [word for word in data if word not in stop_words]

    return value


def make_word_cloud(group_id: int, image_path: str, save_path: str):
    start_time = datetime.datetime.now() - datetime.timedelta(days=1, minutes=10)
    end_time = datetime.datetime.now()

    data = " ".join(WordDBHelper.select_from_time_range(group_id, start_time, end_time))

    data = participle(data)
    data = remove_stop_words(data)
    string = " ".join(data)

    img = Image.open(image_path)
    img_array = np.array(img)

    wc = WordCloud(
        font_path=MAINPATH + "plugins/storage/wordCloud/SourceHanSerifSC-Medium.otf",
        background_color="white",
        width=1000,
        height=800,
        mask=img_array,
    )
    # 绘制图片
    wc.generate_from_text(string)

    plt.imshow(wc)
    # 隐藏坐标轴
    plt.axis("off")
    # 保存图片
    wc.to_file(save_path)


def get_message(message_chain) -> list:
    ls = [x["text"] for x in message_chain if x["type"] == "Plain"]

    return ls


@scheduler_decorator(
    trigger="cron",
    trigger_args={"hour": "21", "timezone": "Asia/Shanghai"},
    override_rule=True,
)
class MakeWordCloud(Plugin):
    async def handle(self) -> None:
        for id in message_group_list:
            async with lock:
                make_word_cloud(id, image_path, image_save_path)
                clear_message(id)

                mess = MiraiMessageSegment.plain(
                    "今日词云"
                ) + MiraiMessageSegment.image(path=image_save_path)

                await self.bot.get_adapter("mirai").sendGroupMessage(
                    target=id, messageChain=mess
                )

    async def rule(self) -> bool:
        return False


class GetMessage(Plugin):
    async def handle(self):
        async with lock:
            id = self.event.sender.group.id
            message_chain = self.event.message.as_message_chain()
            message = get_message(message_chain)
            if len(message) > 0:
                add_message(message, id)

    async def rule(self) -> bool:
        return (
            self.event.adapter.name == "mirai"
            and self.event.type == "GroupMessage"
            and self.event.sender.group.id in message_group_list
        )
