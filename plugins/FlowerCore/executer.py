import datetime

from plugins.FlowerCore import crawler
import pickle
import traceback
import difflib
from plugins.FlowerCore.account import duel, bind, user
from functools import cmp_to_key
from plugins.FlowerCore.configs import *


def match(s, t):
    return difflib.SequenceMatcher(None, s, t).ratio()


def log(s):
    print(s)


def timestr(t):
    s = str(t)
    if not "." in s:
        return s
    return s[: s.find(".")]


def find_tag(t):
    tar = None
    for y in AVAILABLE_TAGS:
        if tar is None or match(t, tar) < match(t, y):
            tar = y
    if match(tar, t) > DIFF_THRESHOLD:
        return tar


def parse_tags(tags):
    log(str(tags))
    try:
        rating = int(tags[0])
        if rating < 800 or rating > 3500 or rating % 100 != 0:
            return "rating 应该是 800~3500 的整百数"
    except:
        return "rating 应该是 800~3500 的整百数"
    for x in tags[1:]:
        y = str(x)
        if y[0] == "!":
            y = y[1:]
        if not y in AVAILABLE_TAGS:
            msg = "{:s} 看起来不是一个合法的 tag 哦".format(y)
            t1 = find_tag(y)
            if t1:
                msg += "\n你是否在寻找 {:s}".format(t1.replace(" ", "_"))
            return msg
    return 0


class Flower:
    duels = []
    binding = []
    user_list = dict()
    index = 0

    @classmethod
    def syncto(cls):
        with open(STORAGE_PATH, "wb") as file:
            pickle.dump([cls.duels, cls.user_list, cls.index], file)

    @classmethod
    def syncfrom(cls):
        try:
            with open(STORAGE_PATH, "rb") as file:
                cls.duels, cls.user_list, cls.index = pickle.load(file)
        except FileNotFoundError:
            cls.syncto()

    @classmethod
    def init(cls):
        duel.init()
        cls.syncfrom()

    @classmethod
    def bind(cls, sender, *args):
        try:
            CF_id = args[0][0]
        except:
            return "参数非法。"
        if sender.bind is not None:
            return "你正在绑定一个账号，请先输入 /bind finish 结束绑定"
        if CF_id in [x.CF_id for x in cls.binding]:
            return "有人正在绑定这个账号"
        new_bind = bind.CFBindAction(sender, CF_id)
        cls.binding.append(new_bind)
        sender.bind = new_bind
        return (
            "你正在绑定 CF 账号：{:s}，请在 {:d} 秒内向 https://codeforces.com/contest/1/problem/A "
            "提交一个 CE，之后输入 /bind finish 完成绑定。".format(
                CF_id, BIND_TIME_LIMIT
            )
        )

    @classmethod
    def finish_bind(cls, sender, *args):
        if sender.bind is None:
            return "你好像没有在绑定账号啊"
        result = sender.bind.check()
        if sender.bind in cls.binding:
            cls.binding.remove(sender.bind)
        sender.bind = None
        if result != 1:
            return {
                -1: "未在规定时间内提交",
                -2: "没有发现符合要求的提交",
                -3: "网络错误，请稍后再试",
            }[result]
        cls.user_list[sender.qq] = sender
        return "绑定账号 {:s} 成功".format(sender.CF_id)

    @classmethod
    def challenge(cls, sender, *args):
        if len(args) < 1:
            return "参数非法。"
        try:
            args = args[0]
            if int(args[0]) == SELF_QQ:
                return "抱歉，我不是很擅长战斗。"
            try:
                target = cls.user_list[int(args[0])]
            except KeyError:
                return "你或者对手没有绑定账号"
        except:
            return "参数非法。"
        tags = [x.replace("_", " ") for x in args[1:] if x]
        res = parse_tags(tags)
        if res != 0:
            return res
        tags[0] = int(tags[0])
        if target == sender:
            return "你知道吗，人无法逃离自己的影子。"
        if sender.CF_id is None or target.CF_id is None:
            return "你或者对手没有绑定账号"
        if (sender.duel is not None) or (target.duel is not None):
            return "你们已经在决斗了，或者已经被邀请进行决斗。"
        cls.index += 1
        new_duel = duel.Duel(sender, target, tags, cls.index)
        cls.duels.append(new_duel)
        return "{:s} 挑战了 {:s}, 应战请输入 /duel accept，拒绝请输入 /duel decline".format(
            sender.name(), target.name()
        )

    @classmethod
    def accept(cls, sender, *args):
        if (
            (sender.duel is None)
            or (sender.duel.status != "pending")
            or (sender == sender.duel.user1)
        ):
            return "你好像没有接收到邀请啊"
        result = sender.duel.begin()
        if result == -1:
            cls.duels.remove(sender.duel)
            sender.duel.discard()
            return "抱歉，我没找到符合条件的题目。"
        rival = sender.duel.rival(sender)
        return """你接受了 {:s} 的挑战。题目链接：{:s}，
通过后输入 /duel judge 进行结算。""".format(
            rival.name(), crawler.link(sender.duel.problem)
        )

    @classmethod
    def decline(cls, sender, *args):
        if (
            (sender.duel is None)
            or (sender.duel.status != "pending")
            or (sender.duel.user1 == sender)
        ):
            return "你好像没有接收到邀请啊"
        rival = sender.duel.rival(sender)
        cls.duels.remove(sender.duel)
        sender.duel.discard()
        return "你拒绝了 {:s} 的挑战".format(rival.name())

    @classmethod
    def cancel(cls, sender, *args):
        if (
            (sender.duel is None)
            or (sender.duel.status != "pending")
            or (sender.duel.user2 == sender)
        ):
            return "你好像没有发起挑战啊"
        rival = sender.duel.rival(sender)
        cls.duels.remove(sender.duel)
        sender.duel.discard()
        return "你取消了对 {:s} 的挑战".format(rival.name())

    @classmethod
    def judge(cls, sender, *args):
        if (sender.duel is None) or (sender.duel.status != "active"):
            return "你好像没有在决斗啊"
        duet = sender.duel
        result = duet.judge()
        if type(result) == int:
            return {
                -1: "似乎遇到了网络错误，请稍后再试吧",
                -2: "评测机正在评测，请稍后再试吧",
                -3: "未检测到通过的提交",
            }[result]
        assert duet.status == "finished"
        winner = duet.result["winner"]
        loser = duet.rival(winner)
        old = duet.result["old"]
        new = duet.result["new"]
        cls.duels.remove(duet)
        return """决斗结束，{:s} 取得了胜利。
        Rating 变化：{:s} {:d} + {:d} = {:d}
         {:s} {:d} + {:d} = {:d}
         用时：{:s}""".format(
            winner.name(),
            winner.name(),
            old[0],
            new[0] - old[0],
            new[0],
            loser.name(),
            old[1],
            new[1] - old[1],
            new[1],
            timestr(duet.duration()),
        )

    @classmethod
    def change(cls, sender, *args):
        if (sender.duel is None) or (sender.duel.status != "active"):
            return "你好像没有在决斗啊"
        result = sender.duel.change(sender)
        rival = sender.duel.rival(sender)
        if result == 0:
            return "{:s} 发起了换题请求，{:s} 请输入 /duel change 以同意请求".format(
                sender.name(), rival.name()
            )
        else:
            return "题目链接：{:s}".format(crawler.link(sender.duel.problem))

    @classmethod
    def give_up(cls, sender, *args):
        if (sender.duel is None) or (sender.duel.status != "active"):
            return "你好像没有在决斗啊"
        sender.duel.give_up(sender)
        return "{:s} 投降了。".format(sender.name())

    @classmethod
    def ranklist(cls, sender, *args):
        rank = []
        for u in cls.user_list:
            usr = cls.user_list[u]
            if usr.CF_id is None:
                continue
            rank.append([usr, usr.display_rating()])
        rank.sort(key=cmp_to_key(lambda x, y: y[1] - x[1]))
        cnt = 0
        msg = ""
        for x in rank:
            msg += x[0].name() + ": " + str(x[1]) + "\n"
            cnt += 1
            if cnt > DISPLAY_LIMIT:
                msg += "仅显示前 {:d} 位...".format(DISPLAY_LIMIT)
                break
        return {"title": "排行榜", "brief": "决斗 Rating 排行榜", "text": msg}

    @classmethod
    def ongoing(cls, sender, *args):
        msg = "正在进行的决斗：\n"
        for d in cls.duels:
            assert d.status != "finished"
            if d.status == "pending":
                msg += "{:s} 正在挑战 {:s}\n".format(d.user1.name(), d.user2.name())
            elif d.status == "active":
                msg += "{:s} vs {:s}, on {:s}, lasted for {:s}\n".format(
                    d.user1.name(),
                    d.user2.name(),
                    crawler.problem_name(d.problem),
                    timestr(datetime.datetime.now() - d.begin_time),
                )
        return {"title": "进行中的决斗", "brief": "正在进行的决斗有：", "text": msg}

    @classmethod
    def problem(cls, sender, *args):
        try:
            tags = [x.replace("_", " ") for x in args[0] if x]
            res = parse_tags(tags)
            if res != 0:
                return res

        except:
            return "参数非法。"
        try:
            tags[0] = int(tags[0])
        except:
            return "Rating 应该是 800 ~ 3500 的整百数"
        excluded_problems = None
        if "not-seen" in tags and sender.CF_id is not None:
            excluded_problems = crawler.problem_record(sender.CF_id)
            log("excluded {:d} problems".format(len(excluded_problems)))
        return "题目链接：{:s}".format(
            crawler.link(duel.crawler.request_problem(tags, excluded_problems))
        )

    @classmethod
    def history(cls, sender, *args):
        try:
            args = args[0]
            try:
                target = target2 = cls.user_list[int(args[0])]
                if len(args) > 1:
                    target2 = cls.user_list[int(args[1])]
            except:
                if args[0] == "recent":
                    target = "recent"
                else:
                    return "参数非法。"
        except:
            target = target2 = sender
        if target != "recent":
            msg = "用户 {:s} Rating = {:d}\n\n".format(
                target.name(), target.display_rating()
            )
            c1 = 0
            c2 = 0
            for d in target.duel_history:

                part = {d.user1, d.user2}
                if not ((target in part) and (target2 in part)):
                    continue
                try:
                    begin = timestr(d.begin_time)
                    end = timestr(d.finish_time)
                    duration = timestr(d.finish_time - d.begin_time)
                    timestamp = "From {:s} to {:s}, lasted for {:s}\n".format(
                        begin, end, duration
                    )
                except TypeError:
                    timestamp = ""
                try:
                    problem = "on {:s}\n".format(
                        crawler.problem_name(d.problem, rating=True)
                    )
                except TypeError:
                    problem = ""
                if d.status == "finished":
                    line = "🟩 {:s} 胜 {:s}\n".format(
                        target.name(), d.rival(target).name()
                    )
                    if target != d.result["winner"]:
                        c2 += 1
                        line = "🟥 {:s} 负 {:s}\n".format(
                            target.name(), d.rival(target).name()
                        )
                    else:
                        c1 += 1
                    line = "#{:d}: ".format(d.index) + line
                else:
                    line = "{:s} 投降了\n".format(d.result["loser"].name())
                msg += line + problem + timestamp + "\n"
            msg += "\n比分为 {:d} : {:d}".format(c1, c2)
            return {
                "title": "决斗历史",
                "brief": "用户 {:s} 的决斗历史：".format(target.name()),
                "text": msg,
            }

        else:
            msg = "最近的 {:d} 场单挑:\n\n".format(DISPLAY_LIMIT)
            lis = []
            for u in cls.user_list:
                for d in cls.user_list[u].duel_history:
                    if d.index < cls.index - DISPLAY_LIMIT:
                        continue
                    try:
                        begin = timestr(d.begin_time)
                        end = timestr(d.finish_time)
                        duration = timestr(d.finish_time - d.begin_time)
                        timestamp = "From {:s} to {:s}, lasted for {:s}\n".format(
                            begin, end, duration
                        )
                    except TypeError:
                        timestamp = ""
                    try:
                        problem = "on {:s}\n".format(
                            crawler.problem_name(d.problem, rating=True)
                        )
                    except TypeError:
                        problem = ""
                    if d.status == "finished":
                        line = "{:s} 胜 {:s}\n".format(
                            d.result["winner"].name(),
                            d.rival(d.result["winner"]).name(),
                        )
                        line = "#{:d}: ".format(d.index) + line
                    else:
                        line = "{:s} 投降了\n".format(d.result["loser"].name())
                    lis.append(line + problem + timestamp)
            lis = list(set(lis))
            lis.sort()
            for x in lis:
                msg += x + "\n"
            return {"title": "决斗历史", "brief": "最近的的决斗历史：", "text": msg}

    @classmethod
    def statics(cls, sender, *args):
        s = ""
        begin = FLOWER_BIRTHDAY
        end = datetime.datetime.now()
        days = (end - begin).days
        c1, c2 = 0, 0
        for x in cls.user_list:
            usr = cls.user_list[x]
            if usr.CF_id is None:
                continue
            c2 += len(usr.duel_history)
            c1 += 1
        s += "我已经工作了 {:d} 天\n".format(days)
        s += "维护了 {:d} 场单挑\n".format(c2 // 2)
        s += "一共有 {:d} 名选手注册了账号\n".format(c1)
        s += "谢谢你与我同行。"
        return s

    @classmethod
    def daily_problem(cls, sender, *args):
        return "题目链接:{:s}".format(crawler.link(duel.crawler.daily_problem()))

    @classmethod
    def daily_finish(cls, sender, *args):
        day = (lambda x: [x.year, x.month, x.day])(datetime.datetime.now())
        if day in sender.daily_passed:
            return "你已经通过了今天的每日挑战"
        if sender.CF_id == None:
            return "请先绑定账号"
        submission = crawler.get_recent_submission(sender.CF_id)
        if submission is None:
            return "网络错误，请稍后再试"
        v1, p1 = submission["verdict"], submission["problem"]
        if p1 == duel.crawler.daily_problem() and v1 == "OK":
            point = p1["rating"]
            sender.daily_passed.append(day)
            sender.daily_score += point
            return "你通过了今天的每日挑战，" "获得了 {:d} 点积分。".format(
                point
            ) + "\n你当前的积分为 {:d}。".format(sender.daily_score)
        else:
            return "未检测到通过的提交"

    @classmethod
    def daily_ranklist(cls, sender, *args):
        rank = []
        for u in cls.user_list:
            usr = cls.user_list[u]
            if usr.CF_id is None:
                continue
            rank.append([usr, usr.daily_score])
        rank.sort(key=cmp_to_key(lambda x, y: y[1] - x[1]))
        cnt = 0
        msg = ""
        for x in rank:
            msg += x[0].name() + ": " + str(x[1]) + "\n"
            cnt += 1
            if cnt > DISPLAY_LIMIT:
                msg += "仅显示前 {:d} 位...".format(DISPLAY_LIMIT)
                break
        return {"title": "排行榜", "brief": "每日挑战积分排行榜", "text": msg}


command_tree = {
    "duel": {
        "challenge": Flower.challenge,
        "daily": {
            "problem": Flower.daily_problem,
            "ranklist": Flower.daily_ranklist,
            "finish": Flower.daily_finish,
        },
        "accept": Flower.accept,
        "decline": Flower.decline,
        "cancel": Flower.cancel,
        "change": Flower.change,
        "giveup": Flower.give_up,
        "judge": Flower.judge,
        "ranklist": Flower.ranklist,
        "ongoing": Flower.ongoing,
        "history": Flower.history,
        "statics": Flower.statics,
        "problem": Flower.problem,
    },
    "bind": {"begin": Flower.bind, "finish": Flower.finish_bind},
}


def interpret(command):
    command = command.strip()
    if not command[0].startswith("/"):
        return None
    command = command[1:]
    args = [x for x in command.split(" ") if x]
    cur = command_tree
    u = 0
    res = []
    flag = True
    while type(cur) == dict and u < len(args):
        cmd = args[u]
        des = None
        for opt in cur:
            if (not des) or (match(opt, cmd) > match(des, cmd)):
                des = opt
        if (des == cmd) or (u > 0 and match(des, cmd) > DIFF_THRESHOLD):
            flag &= des == cmd
            cur = cur[des]
            res.append(des)
            u += 1
        else:
            return None
    if type(cur) != dict:
        return [cur, [*res, *["[{:s}]".format(x) for x in args[u:]]], args[u:], flag]
    else:
        return None


def execute_command(command, sender):
    if not sender in Flower.user_list:
        Flower.user_list[sender] = user.User(sender)
    sender = Flower.user_list[sender]
    fun, cmd, args, flag = command
    try:
        Flower.syncto()
        statement = fun(sender, args)
        return statement
    except:
        return """While handling the command above, an unexpected exception occured. See the details about 
                the exception below:
                --------------------
                {:s}
                ---------------------
                If you believe this is a glitch, please contact the developer.""".format(
            traceback.format_exc()
        )


def exec_command(command, sender):
    res = interpret(command)
    if res is None:
        return None
    execute_command(res, sender)
