import random
import aiohttp
from bs4 import BeautifulSoup
import urllib.request
from json import loads, dumps
from plugins.FlowerCore.configs import *
import plugins.utils.DBHelper as DBHelper


async def fetch_url_async(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()


async def fetch_json_async(url):
    """Fetch a URL and return the JSON response with async."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


def fetch_json(url):
    """Fetch a URL and return the JSON response."""
    proxy_support = urllib.request.ProxyHandler({"http": "localhost:7890"})
    opener = urllib.request.build_opener(proxy_support)
    urllib.request.install_opener(opener)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36"
    }
    req = urllib.request.Request(url=url, headers=headers)
    page = urllib.request.urlopen(req)
    soup = BeautifulSoup(page, "html.parser").text
    return loads(soup)


def link(problem):
    if problem == None:
        return "找不到题目"
    try:
        return f"https://codeforces.com/problemset/problem/{problem['contestId']}/{problem['index']}"
    except KeyError:
        return str(problem)


def get_recent_submission(CF_id):
    try:
        json = fetch_json(
            f"https://codeforces.com/api/user.status?handle={CF_id}&from=1&count=1"
        )
        print(json)
        if json["status"] == "FAILED":
            return None
        try:
            return json["result"][0]
        except IndexError:
            return None
    except:
        return None


def problem_name(problem, rating=False):
    try:
        if rating:
            return (
                str(problem["contestId"])
                + str(problem["index"])
                + "(*{:d})".format(problem["rating"])
            )
        return str(problem["contestId"]) + str(problem["index"])
    except KeyError:
        return str(problem)


problems = []


def fetch_problems() -> bool:
    global problems
    for cnt in range(10):
        try:
            problems = fetch_json("https://codeforces.com/api/problemset.problems")[
                "result"
            ]["problems"]
            return True
        except BaseException:
            pass
    return False


def daily_problem():
    res = DBHelper.get_problem(datetime.datetime.now())
    if len(res) != 0:
        text = res[0]
        return loads(text)

    if len(problems) == 0:
        fetch_problems()
    res = []
    for x in problems:
        try:
            if x["rating"] <= DAILY_UPPER_BOUND and "*special" not in x["tags"]:
                res.append(x)
        except KeyError:
            pass

    problem = random.choice(res)

    DBHelper.write_problem(dumps(problem), datetime.datetime.now())

    return problem


def problem_record(user):
    try:
        try:
            d = fetch_json("https://codeforces.com/api/user.status?handle=" + user)
        except:
            return set()
        JSON = d
        if JSON["status"] != "OK":
            return []
        res = {problem_name(x["problem"]) for x in JSON["result"]}
        return res
    except:
        return set()


def request_problem(tags, excluded_problems=None):
    if len(problems) == 0:
        fetch_problems()
    assert type(tags[0]) == int
    rating = tags[0]
    tags = tags[1:]
    result = []
    for x in problems:
        if ("tags" not in x) or ("rating" not in x) or ("contestId" not in x):
            continue
        if excluded_problems is not None and problem_name(x) in excluded_problems:
            continue
        flag = 1
        for y in tags:
            if y == "not-seen":
                continue
            if y[0] != "!":
                if y not in x["tags"] or (
                    y == "new" and "contestId" in x and x["contestId"] < NEW_THRESHOLD
                ):
                    flag = 0
            else:
                if y[1:] in x["tags"] or (
                    y[1:] == "new"
                    and "contestId" in x
                    and x["contestId"] >= NEW_THRESHOLD
                ):
                    flag = 0
        if not flag:
            continue
        if x["rating"] == rating:
            result.append(x)
    if not result:
        return None
    return random.choice(result)
