import calendar
import pickle
import time
import requests
from alicebot import Plugin
from DuelFrontend import to_text, lock
from authconfigs import gen_quote, MAINPATH
import matplotlib.pyplot as plt
from datetime import datetime
from alicebot.adapter.mirai import MiraiMessageSegment
from alicebot.adapter.apscheduler import scheduler_decorator
import matplotlib.dates as mdates

from plugins.FlowerCore.account import user
from plugins.FlowerCore.configs import STORAGE_PATH, DIFF_THRESHOLD
from plugins.FlowerCore.executer import Flower, match


IMG_PATH = 'plugins//storage//output.png'

message_group_list = [930035838]

contest_list = {}

clist_api_url = "https://clist.by/api/v4/json/contest/?resource=codeforces.com%2Catcoder.jp&filtered=false&order_by=-start&limit=40&offset=0&username=Dynamic_Pigeon&api_key=6e1a0f877f1f55496ab039759eca803c3a2c34cf"


def get_time(t):
    if t >= 24 * 3600:
        return time.strftime("%dday %Hh %Mm %Ss", time.gmtime(t))
    return time.strftime("%Hh %Mm %Ss", time.gmtime(t))


def get_day(t):
    return time.strftime("%Y-%m-%d(%a) %H:%M", time.gmtime(t))

def get_api_time(t):
    return time.strptime(t, '%Y-%m-%dT%X')


def get_contest():
    resp = requests.get(clist_api_url)
    
    if resp.status_code != 200:
        return
    
    json = resp.json()
    global contest_list
    contest_list = json['objects']


def get_contest_list():
    if len(contest_list) == 0:
        get_contest()
    if len(contest_list) == 0:
        return "网络错误"
    now = calendar.timegm(time.gmtime())
    result = []
    for contest in contest_list:
        if calendar.timegm(get_api_time(contest['start'])) > now:
            result.append(contest)
    if len(result) == 0:
        return {'title': '比赛列表', 'brief': '找不到比赛喵', 'text': "找不到比赛喵"}
    result = result[::-1]
    msg = ''
    for contest in result:
        msg += contest['event'] + "\n"
        msg += '[duration {}]\n'.format(get_time(contest['duration']))
        msg += get_day(calendar.timegm(get_api_time(contest['start'])) + 8 * 3600)
        msg += "\n" + contest['href'] + "\n\n"
    return {'title': '比赛列表', 'brief': '找到了 {} 场比赛'.format(len(result)), 'text': msg}


def get_user_contest(CF_id):
    json = requests.get("https://codeforces.com/api/user.rating?handle={}".format(CF_id)).json()
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


def analyze(CF_id):
    try:
        json = requests.get("https://codeforces.com/api/user.status?handle={}".format(CF_id)).json()
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
        if 'problemsetName' in x['problem'] or 'verdict' not in x.keys():
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


def get_text(message_chain):
    s = ''
    with open(STORAGE_PATH, 'rb') as file:
        duels, user_list, index = pickle.load(file)
    for x in message_chain:
        if x['type'] == 'Plain':
            s += x['text']
        elif x['type'] == 'At':
            t = (x['target'])
            if not t in user_list:
                user_list[t] = user.User(t)
            sender = user_list[t]
            if sender.CF_id == None:
                return s
            s += sender.CF_id
    return s



command_list = ['info', 'analyze']


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



@scheduler_decorator(
    trigger="interval", trigger_args={"seconds": 1800}, override_rule=True
)
class UpdateContestList(Plugin):
    async def handle(self) -> None:
        get_contest()
        print("contest 重新加载")

    async def rule(self) -> bool:
        return False



@scheduler_decorator(
    trigger="interval", trigger_args={"seconds": 60}, override_rule=True
)
class Schedule(Plugin):
    async def handle(self) -> None:
        if len(contest_list) == 0:
            get_contest()
        if len(contest_list) == 0:
            return
        now = calendar.timegm(time.gmtime())
        result = []
        for contest in contest_list:
            if calendar.timegm(get_api_time(contest['start'])) > now:
                result.append(contest)
        if len(result) == 0:
            return
        event = ''
        for item in result[::-1]:
            if item['start'] == result[-1]['start']:
                event += '{}\n{}\n'.format(item['event'], item['href'])
            else:
                break

        result = result[-1]
        cur_time = calendar.timegm(get_api_time(contest['start']))
        if cur_time- 3600 > now:
            return
        
        if cur_time- 3600 <= now <= cur_time- 3600 + 60:
            for id in message_group_list:
                await self.bot.get_adapter("mirai").sendGroupMessage(
                    target=id, 
                    messageChain=MiraiMessageSegment.plain('喵喵喵，选手注意') + MiraiMessageSegment.at_all() + 
                                MiraiMessageSegment.plain('\n' + event) + 
                                MiraiMessageSegment.plain(' 还有 {} 分钟开始'.format((cur_time- now) // 60) + 
                                MiraiMessageSegment.plain('\n请及时报名！'))
                    )
            return
        
        if cur_time- 600 <= now <= cur_time- 600 + 60:
            for id in message_group_list:
                await self.bot.get_adapter("mirai").sendGroupMessage(
                    target=id, 
                    messageChain=MiraiMessageSegment.plain('喵喵喵，选手注意') + MiraiMessageSegment.at_all() + 
                                MiraiMessageSegment.plain('\n' + event) + 
                                MiraiMessageSegment.plain(' 还有 {} 分钟开始'.format((cur_time- now) // 60) + 
                                MiraiMessageSegment.plain('\n请及时报名！'))
                    )
            return
        

    async def rule(self) -> bool:
        return False

                

class Contest(Plugin):
    async def handle(self):
        async with lock:
            await self.event.reply('正在查询比赛列表')
            statement = get_contest_list()
            if type(statement) == dict:
                msg = gen_quote(statement['title'], statement['brief'], [statement['text']])
                await self.event.reply(msg)
            else:
                await self.event.reply(statement)

    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith('/contests') or text.startswith('/contest')
        except:
            return False



class CodeForces(Plugin):
    async def handle(self):
        async with lock:
            message_chain = self.event.message.as_message_chain()
            text = get_text(message_chain)
            text = text.split()
            text, flag = get_command(text)
            if flag:
                await self.event.reply("本条指令被解析为：" + ' '.join(text))
            # print(text)
            if len(text) < 2:
                return
            if text[1] == 'info':
                if len(text) < 3:
                    await self.event.reply('你是否没有at到他或者他没有绑定账号')
                    return
                await self.event.reply('正在查询用户参赛记录')
                statement = get_user_contest(text[2])
                # print(statement)
                await self.event.reply(statement)
                return
            elif text[1] == 'analyze':
                if len(text) < 3:
                    await self.event.reply('你是否没有at到他或者他没有绑定账号')
                    return
                await self.event.reply('正在查询用户做题记录')
                statement = analyze(text[2])
                await self.event.reply(statement)
                return
            else:
                return
            

    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith('/cf')
        except:
            return False
