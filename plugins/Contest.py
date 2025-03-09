import asyncio
import calendar
import pickle
import time
import utils.ConfigReader as ConfigReader
from alicebot import Plugin
from DuelFrontend import to_text
from authconfigs import gen_quote
from alicebot.adapter.mirai import MiraiMessageSegment
from alicebot.adapter.apscheduler import scheduler_decorator
from bs4 import BeautifulSoup
import urllib.request
from WordCloud import message_group_list
from plugins.FlowerCore.crawler import (
    fetch_json,
    fetch_json_async,
)

from plugins.FlowerCore.account import user
from plugins.FlowerCore.configs import STORAGE_PATH
from plugins.utils.ConfigReader import get_logger


contest_list = []

clist_contest = ConfigReader.read_contest_list()
clist_api_url = "https://clist.by/api/v4/json/contest/?resource={}&filtered=false&order_by=-start&limit=20&offset=0&username=Dynamic_Pigeon&api_key=6e1a0f877f1f55496ab039759eca803c3a2c34cf"

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
    return time.strptime(t, "%Y-%m-%dT%H:%M:%S")


async def get_contest():
    if contest_lock.locked():
        async with contest_lock:
            return
    async with contest_lock:
        con_list = []
        # clist 改了api，现在只能这样找
        for contest in clist_contest:
            url = clist_api_url.format(contest)
            json = await fetch_json_async(url)
            con_list += json["objects"]
        con_list.sort(key=lambda x: x["start"])
        con_list.reverse()

        global contest_list
        contest_list = con_list


async def get_contest_list():
    if len(contest_list) == 0:
        await get_contest()
    if len(contest_list) == 0:
        return "网络错误"
    now = calendar.timegm(time.gmtime())
    result = []
    for contest in contest_list:
        if calendar.timegm(get_api_time(contest["start"])) > now:
            result.append(contest)
    if len(result) == 0:
        return {"title": "比赛列表", "brief": "找不到比赛喵", "text": "找不到比赛喵"}
    result = result[::-1]
    msg = ""
    for contest in result:
        msg += contest["event"] + "\n"
        msg += "[duration {}]\n".format(get_time(contest["duration"]))
        msg += get_day(calendar.timegm(get_api_time(contest["start"])) + 8 * 3600)
        msg += "\n" + contest["href"] + "\n\n"
    return {
        "title": "比赛列表",
        "brief": "找到了 {} 场比赛".format(len(result)),
        "text": msg,
    }


def get_text(message_chain):
    s = ""
    with open(STORAGE_PATH, "rb") as file:
        duels, user_list, index = pickle.load(file)
    for x in message_chain:
        if x["type"] == "Plain":
            s += x["text"]
        elif x["type"] == "At":
            t = x["target"]
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
        get_logger().debug("Contest 更新")

    async def rule(self) -> bool:
        return False


@scheduler_decorator(
    trigger="interval",
    trigger_args={"seconds": 60, "start_date": "2024-07-10 14:00:10"},
    override_rule=True,
)
class Schedule(Plugin):
    async def handle(self) -> None:
        if len(contest_list) == 0:
            await get_contest()
        if len(contest_list) == 0:
            return
        now = calendar.timegm(time.gmtime())
        result = [
            contest
            for contest in contest_list
            if calendar.timegm(get_api_time(contest["start"])) > now
        ]

        if len(result) == 0:
            return

        cur_time = calendar.timegm(get_api_time(result[-1]["start"]))

        for sub_time in remind_times:
            sub_time *= 60
            if cur_time - sub_time <= now <= cur_time - sub_time + 60:
                await self.send_message(result, sub_time // 60)
                return

    async def send_message(self, res_event, time):
        event = ""
        for item in res_event[::-1]:
            if item["start"] == res_event[-1]["start"]:
                event += "{}\n{}\n".format(item["event"], item["href"])
            else:
                break

        mess = MiraiMessageSegment.plain(
            "喵喵喵，选手注意"
            f"\n{event}"
            f"还有 {time} 分钟开始"
            "\n请要参加的选手及时报名！"
        )
        for id in message_group_list:
            await self.bot.get_adapter("mirai").sendGroupMessage(
                target=id, messageChain=[mess]
            )

    async def rule(self) -> bool:
        return False


class Contest(Plugin):
    async def handle(self):
        await self.event.reply("正在查询比赛列表")
        async with lock:
            statement = await get_contest_list()
        if type(statement) == dict:
            msg = gen_quote(statement["title"], statement["brief"], [statement["text"]])
            await self.event.reply(msg)
        else:
            await self.event.reply(statement)

    async def rule(self) -> bool:
        try:
            message_chain = self.event.message.as_message_chain()
            text = to_text(message_chain)
            return text.startswith("/contests") or text.startswith("/contest")
        except:
            return False
