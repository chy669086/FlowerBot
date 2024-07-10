import asyncio
import jieba
import numpy as np
from pytz import utc

from PIL import Image
from matplotlib import pyplot as plt
from wordcloud import WordCloud
from alicebot import Plugin
from authconfigs import MAINPATH
from alicebot.adapter.mirai import MiraiMessageSegment
from alicebot.adapter.apscheduler import scheduler_decorator


word_file_path = MAINPATH + 'plugins/storage/wordCloud/dailyWord_{}.txt'
image_path = MAINPATH + 'plugins/storage/wordCloud/bear.jpg'
image_save_path = MAINPATH +  'plugins/storage/wordCloud/wordCloud.jpg'
stop_words_path = MAINPATH + 'plugins/storage/wordCloud/hit_stopwords.txt'
message_group_list = [930035838]

lock = asyncio.Lock()


def add_to_file(path: str, words: list, group_id: int):
    with open(path.format(group_id), 'a', encoding='utf-8') as file:
        file.write('\n'.join(words))
        file.write('\n')


def clear_file(path: str, group_id: int):
    with open(path.format(group_id), 'w', encoding='utf-8') as file:
        file.write('')


def participle(words: str) -> list:
    ls = jieba.lcut(words)
    return ls


def remove_stop_words(data: list) -> list:
    with open(stop_words_path, 'r', encoding='utf-8') as file:
        stop_words = set([line.strip() for line in file.readlines()])
    
    value = []
    for word in data:
        if word not in stop_words:
            value.append(word)

    return value


def make_word_cloud(word_file_path: str, image_path: str, save_path: str) :
    with open(word_file_path, 'r', encoding='utf-8') as file:
        data = file.read()

    data = participle(data)
    data = remove_stop_words(data)
    string = ' '.join(data)

    img = Image.open(image_path)
    img_array = np.array(img)

    wc = WordCloud(
        font_path = MAINPATH +  'plugins/storage/wordCloud/SourceHanSerifSC-Medium.otf',
        background_color='white',
        width=1000,
        height=800,
        mask=img_array
    )
    wc.generate_from_text(string) # 绘制图片

    plt.imshow(wc)
    plt.axis('off')#隐藏坐标轴
    wc.to_file(save_path)  #保存图片


def get_message(message_chain) -> list:
    ls = []
    for x in message_chain:
        if x['type'] == 'Plain':
            ls.append(x['text'])
    
    return ls


@scheduler_decorator(
    trigger="cron", trigger_args={"hour": '21', "timezone": 'Asia/Shanghai'}, override_rule=True
)
class MakeWordCloud(Plugin):
    async def handle(self) -> None:
        async with lock:
            for id in message_group_list:
                make_word_cloud(word_file_path.format(id), image_path, image_save_path)
                mess = MiraiMessageSegment.plain('今日词云') + MiraiMessageSegment.image(path=image_save_path)
                await self.bot.get_adapter("mirai").sendGroupMessage(
                    target=id, 
                    messageChain=mess
                )
                clear_file(word_file_path, id)

    async def rule(self) -> bool:
        return False



class GetMessage(Plugin):
    async def handle(self):
        async with lock:
            id = self.event.sender.group.id
            message_chain = self.event.message.as_message_chain()
            message = get_message(message_chain)
            if len(message) > 0:
                add_to_file(word_file_path, message, id)

    async def rule(self) -> bool:
        return self.event.adapter.name == 'mirai' and self.event.type == 'GroupMessage' and self.event.sender.group.id in message_group_list