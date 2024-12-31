import asyncio
import calendar
import pickle
import time
import utils.ConfigReader as ConfigReader
import structlog
from alicebot import Plugin
from DuelFrontend import to_text
from authconfigs import gen_quote
from alicebot.adapter.mirai import MiraiMessageSegment
from alicebot.adapter.apscheduler import scheduler_decorator
from bs4 import BeautifulSoup
import urllib.request
from WordCloud import message_group_list
from plugins.FlowerCore.crawler import fetch_url_and_return_json, afetch_url_and_return_json

from plugins.FlowerCore.account import user
from plugins.FlowerCore.configs import STORAGE_PATH



contest_list = []

clist_contest = ConfigReader.read_contest_list()
clist_api_url = "https://clist.by/api/v4/json/contest/?resource={}&filtered=false&order_by=-start&limit=20&offset=0&username=Dynamic_Pigeon&api_key=6e1a0f877f1f55496ab039759eca803c3a2c34cf"
nowcoder_contest_url = 'https://ac.nowcoder.com/acm/contest/vip-index'

remind_times = ConfigReader.read_remind_times()

lock = asyncio.Lock()
contest_lock = asyncio.Lock()

def get_time(t):
    if t >= 24 * 3600:
        return time.strftime("%dday %Hh %Mm %Ss", time.gmtime(t))
    return time.strftime("%Hh %Mm %Ss", time.gmtime(t))


def get_day(t):
    return time.strftime("%Y-%m-%d(%A) %H:%M", time.gmtime(t))

def get_api_time(t):
    return time.strptime(t, '%Y-%m-%dT%H:%M:%S')


def as_utc_time(time_str, offset = 8):
    tm = time.strptime(time_str, "%Y-%m-%d %H:%M")
    return calendar.timegm(tm) - offset * 3600

def as_api_time(time_str, offset = 8):
    tm = as_utc_time(time_str, offset)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(tm))



def get_nowcoder_contest_info():
    proxy_support = urllib.request.ProxyHandler({'http': 'localhost:7890'})
    opener = urllib.request.build_opener(proxy_support)
    urllib.request.install_opener(opener)

    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'}  
    req = urllib.request.Request(url=nowcoder_contest_url, headers=headers)  
    page = urllib.request.urlopen(req)
    soup = BeautifulSoup(page, 'html.parser')

    info = soup.find('div', class_='platform-mod js-current')

    all_contest = info.find_all('div', class_='platform-item js-item')

    contest_info = []

    for contest in all_contest:
        main = contest.find('div', class_='platform-item-main')
        cont = main.find('div', class_='platform-item-cont')
        event = cont.find('h4').find('a').text
        href = 'https://ac.nowcoder.com' + cont.find('h4').find('a')['href']
        time = cont.find('ul').find('li', class_ = 'match-time-icon').text
        time = time.split()
        start_time = time[1] + ' ' + time[2]
        end_time = time[4] + ' ' + time[5]
        start = as_api_time(start_time)
        end = as_api_time(end_time)
        duration = as_utc_time(end_time) - as_utc_time(start_time)

        info = {
            'event': event,
            'href': href,
            'start': start,
            'end': end,
            'duration': duration
        }
        contest_info.append(info)

    return contest_info

async def get_contest():
    if contest_lock.locked():
        async with contest_lock:
            return
    async with contest_lock:
        global contest_list
        contest_list = []
        # clist 改了api，现在只能这样找
        for contest in clist_contest:
            url = clist_api_url.format(contest)
            json = await afetch_url_and_return_json(url)
            contest_list += json['objects']
        contest_list.sort(key = lambda x: x['start'])
        contest_list.reverse()


async def get_contest_list():
    if len(contest_list) == 0:
        await get_contest()
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



@scheduler_decorator(
    trigger="interval", trigger_args={"seconds": 1800}, override_rule=True
)
class UpdateContestList(Plugin):
    async def handle(self) -> None:
        await get_contest()
        structlog.stdlib.get_logger().debug('Contest 更新')

    async def rule(self) -> bool:
        return False



@scheduler_decorator(
    trigger="interval", trigger_args={"seconds": 60, 'start_date': '2024-07-10 14:00:10'}, override_rule=True
)
class Schedule(Plugin):
    async def handle(self) -> None:
        if len(contest_list) == 0:
            await get_contest()
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
        cur_time = calendar.timegm(get_api_time(result['start']))
        
        
        mess = MiraiMessageSegment.plain('喵喵喵，选手注意') + \
                    MiraiMessageSegment.plain('\n' + event) + \
                    MiraiMessageSegment.plain('还有 {} 分钟开始'.format((cur_time- now) // 60)) + \
                    MiraiMessageSegment.plain('\n请要参加的选手及时报名！')
        
        for sub_time in remind_times:
            sub_time *= 60
            if cur_time- sub_time - 60 <= now <= cur_time- sub_time:
                for id in message_group_list:
                    await self.bot.get_adapter("mirai").sendGroupMessage(
                        target=id, 
                        messageChain=mess
                    )
                return
        

    async def rule(self) -> bool:
        return False

                

class Contest(Plugin):
    async def handle(self):
        await self.event.reply('正在查询比赛列表')
        async with lock:
            statement = await get_contest_list()
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



