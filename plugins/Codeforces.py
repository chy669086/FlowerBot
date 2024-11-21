import asyncio
import time
from alicebot import Plugin
from DuelFrontend import to_text
from authconfigs import MAINPATH
import matplotlib.pyplot as plt
from datetime import datetime
from alicebot.adapter.mirai import MiraiMessageSegment
import matplotlib.dates as mdates
from plugins.FlowerCore.crawler import fetch_url_and_return_json, afetch_url_and_return_json

from plugins.FlowerCore.configs import DIFF_THRESHOLD
from plugins.FlowerCore.executer import match
from plugins.Contest import get_text


command_list = ['info', 'analyze']

IMG_PATH = 'plugins//storage//output.png'

def get_command(text):
    if text[1] in command_list:
        return [text, False]
    s = command_list[0]
    for command in command_list[1:]:
        if match(s, text[1]) < match(text[1], command):
            s = command
    if match(s, text[1]) > DIFF_THRESHOLD:
        # print(s)
        text[1] = s
        return [text, True]

    return [text, False]

async def get_user_contest(CF_id):
    json = await afetch_url_and_return_json("https://codeforces.com/api/user.rating?handle={}".format(CF_id))
    if json["status"] != "OK":
        return json['comment']
    con = json['result']
    if len(con) == 0:
        return "没有参赛记录"
    x = []
    y = []
    max_rating = 0
    for contest in con:
        y.append(contest['newRating'])
        max_rating = max(max_rating, contest['newRating'])
        s = time.strftime("%y/%m/%d", time.gmtime(contest['ratingUpdateTimeSeconds'] + 3600 * 8))
        x.append(s)

    plt.clf()
    plt.figure(dpi=300, figsize=(10, 5))

    plt.xlabel('Time')
    plt.ylabel('Rating')
    plt.title("{}'s Rating change".format(CF_id))

    date = [datetime.strptime(s, "%y/%m/%d") for s in x]
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%y-%m-%d"))
    plt.plot(date, y, 'o-', color='#4169E1', alpha=0.8, linewidth=1, label='rating', markersize=2)
    plt.legend()
    plt.tick_params(axis='x', rotation=30)
    plt.savefig(IMG_PATH)
    msg = MiraiMessageSegment.plain("max:{}\nnow:{}".format(max_rating, con[-1]['newRating'])) + \
          MiraiMessageSegment.image(path=MAINPATH+IMG_PATH)
    return msg


async def analyze(CF_id):
    try:
        json = await afetch_url_and_return_json("https://codeforces.com/api/user.status?handle={}".format(CF_id))
    except BaseException:
        return '网络错误或其他错误'
    if json["status"] != "OK":
        return json['comment']
    status = json['result']
    if len(status) == 0:
        return '没有提交记录'
    AC_status = []
    vis = set()
    for x in status:
        if 'problem' not in x.keys() or 'problemsetName' in x['problem'] or 'verdict' not in x.keys():
            continue
        if x['verdict'] == 'OK' and (str(x['problem']['contestId']) + x['problem']['index']) not in vis:
            AC_status.append(x['problem'])
            vis.add(str(x['problem']['contestId']) + x['problem']['index'])
    plt.clf()
    color = ['gray'] * 4 + ['g'] * 2 + ['c'] * 2 + ['b'] * 3 + ['purple'] * 2 + ['orange'] * 3 + ['red'] * 12
    y = [0] * 28
    for t in AC_status:
        if 'rating' in t:
            y[t['rating'] // 100 - 8] += 1
    x = [i for i in range(800, 3600, 100)]
    bar_width = 96
    plt.figure(dpi=300, figsize=(10, 5))
    plt.xlim(750, 3550)
    for i in range(len(y)):
        plt.bar(x[i], y[i], bar_width, color=color[i], edgecolor=color[i], antialiased=True)
    # plt.show()
    plt.title("{} solved {} problems in total".format(CF_id, len(AC_status)))
    plt.xlabel('Rating')
    plt.ylabel('Frequency')
    plt.savefig(IMG_PATH)
    msg = MiraiMessageSegment.image(path=MAINPATH+IMG_PATH)
    return msg

img_lock = asyncio.Lock()


class CodeForces(Plugin):
    async def handle(self):
        message_chain = self.event.message.as_message_chain()
        text = get_text(message_chain)
        text = text.split()
        text, flag = get_command(text)
        if flag:
            await self.event.reply("本条指令被解析为：" + ' '.join(text))
        if len(text) < 2:
            return
        if text[1] == 'info':
            async with img_lock:
                if len(text) < 3:
                    await self.event.reply('你是否没有at到他或者他没有绑定账号')
                    return
                await self.event.reply('正在查询用户参赛记录')
                try:
                    statement = await get_user_contest(text[2])
                except:
                    statement = '网络错误或其他错误'
                await self.event.reply(statement)
        elif text[1] == 'analyze':
            async with img_lock:
                if len(text) < 3:
                    await self.event.reply('你是否没有at到他或者他没有绑定账号')
                    return
                await self.event.reply('正在查询用户做题记录')
                try:
                    statement = await analyze(text[2])
                except:
                    statement = '网络错误或其他错误'
                await self.event.reply(statement)
        else:
            return
            

    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith('/cf')
        except:
            return False