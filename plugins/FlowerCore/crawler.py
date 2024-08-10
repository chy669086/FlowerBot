import random
import time
import requests
from bs4 import BeautifulSoup
import urllib.request
from json import loads
from plugins.FlowerCore.configs import *


def fetch_url_and_return_json(url):
    proxy_support = urllib.request.ProxyHandler({'http': 'localhost:7890'})
    opener = urllib.request.build_opener(proxy_support)
    urllib.request.install_opener(opener)

    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'}  
    req = urllib.request.Request(url=url, headers=headers)  
    page = urllib.request.urlopen(req)
    soup = BeautifulSoup(page, 'html.parser').text
    return loads(soup)


def link(problem):
    if problem == None:
        return "找不到题目"
    try:
        return "https://codeforces.com/problemset/problem/" + str(problem['contestId']) + '/' + str(
            problem['index'])
    except KeyError:
        return str(problem)


def get_recent_submission(CF_id):
    try:
        json = fetch_url_and_return_json('https://codeforces.com/api/user.status?handle={:s}&from=1&count=1'.format(CF_id))
        # json = requests.get('https://codeforces.com/api/user.status?handle={:s}&from=1&count=1'.format(CF_id)).json()
        print(json)
        if json['status'] == 'FAILED':
            return None
        try:
            return json['result'][0]
        except IndexError:
            return None
    except :
        return None


def problem_name(problem, rating=False):
    try:
        if rating:
            return str(problem['contestId']) + str(problem['index']) + '(*{:d})'.format(problem['rating'])
        return str(problem['contestId']) + str(problem['index'])
    except KeyError:
        return str(problem)


problems = []


def fetch_problems() -> bool:
    global problems
    for cnt in range(10):
        try:
            problems = fetch_url_and_return_json('https://codeforces.com/api/problemset.problems')['result']['problems']
            return True
        except BaseException:
            pass
    return False


def daily_problem():
    t = time.localtime(time.time())
    if len(problems) == 0 :
        fetch_problems()
    res = []
    for x in problems:
        try:
            if x['rating'] <= DAILY_UPPER_BOUND and '*special' not in x['tags']:
                res.append(x)
        except KeyError:
            pass
    seed = (t.tm_year * 1000 + t.tm_mon * 100000 * t.tm_mday) % len(res)
    return res[seed]


def problem_record(user):
    try:
        try:
            d = fetch_url_and_return_json('https://codeforces.com/api/user.status?handle=' + user)
        except :
            return set()
        JSON = d
        if JSON['status'] != 'OK':
            return []
        res = {problem_name(x["problem"]) for x in JSON['result']}
        return res
    except:
        return set()


def request_problem(tags, excluded_problems=None):
    if excluded_problems is None:
        excluded_problems = set()
    if len(problems) == 0 :
        fetch_problems()
    assert (type(tags[0]) == int)
    rating = tags[0]
    tags = tags[1:]
    result = []
    for x in problems:
        if (not 'tags' in x) or (not 'rating' in x) or (not 'contestId' in x):
            continue
        if excluded_problems is not None:
            if problem_name(x) in excluded_problems:
                continue
        flag = 1
        for y in tags:
            if y == 'not-seen':
                continue
            if y[0] != '!':
                if y == 'new':
                    if 'contestId' in x and x['contestId'] < NEW_THRESHOLD:
                        flag = 0
                    continue
                if not y in x['tags']:
                    flag = 0
            else:
                if y == '!new':
                    if 'contestId' in x and x['contestId'] >= NEW_THRESHOLD:
                        flag = 0
                    continue
                if y[1:] in x['tags']:
                    flag = 0
        if not flag:
            continue
        if x['rating'] == rating:
            result.append(x)
    if not result:
        return None
    return random.choice(result)
