import sqlite3
import datetime

from plugins.authconfigs import MAINPATH

conn = sqlite3.connect(f'{MAINPATH}/plugins/data/data.db')

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS group_message 
    (group_id INTEGER, message TEXT, time TEXT)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS dayliy_problem
    (problem TEXT, time TEXT)''')

cursor.close()

conn.commit()

def write_problem(problem: str, time: datetime.datetime = datetime.datetime.now()):
    time_str = time.today().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO dayliy_problem (problem, time)
    VALUES (?, ?)
    ''', (problem, time_str))
    cursor.close()
    conn.commit()

def get_problem(time: datetime.datetime = datetime.datetime.now()):
    time_str = time.today().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT problem FROM dayliy_problem
    WHERE time = ?
    ''', (time_str,))
    problem = [x[0] for x in cursor.fetchall()]
    cursor.close()
    return problem


def wirte_reconn_log():
    with open(f'{MAINPATH}/plugins/storage/wordCloud/reconn.log', 'a') as file:
        file.write(f'{datetime.datetime.now()}: reconn\n')

def reconn():
    global conn
    conn = sqlite3.connect(f'{MAINPATH}/plugins/data/data.db')

def close():
    conn.close()

def check_connection():
    try:
        conn.execute('SELECT 1')
    except sqlite3.ProgrammingError:
        reconn()

# time is a datetime object
def insert(group_id: int, message: str, time: datetime.datetime = datetime.datetime.now()):
    check_connection()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO group_message (group_id, message, time)
    VALUES (?, ?, ?)
    ''', (group_id, message, time))

    cursor.close()
    conn.commit()

# start_time and end_time are datetime objects
def select_from_time_range(group_id: int, start_time: datetime.datetime, end_time: datetime.datetime):
    check_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT message FROM group_message
    WHERE group_id = ? AND time >= ? AND time <= ?
    ''', (group_id, start_time, end_time))
    mes = cursor.fetchall()

    cursor.close()
    return [x[0] for x in mes]

def select_all(group_id: int):
    check_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT message FROM group_message
    WHERE group_id = ?
    ''', (group_id,))
    mes = cursor.fetchall()

    cursor.close()
    return [x[0] for x in mes]

# time is a datetime object
def delete_before_time(group_id: int, time: datetime.datetime):
    check_connection()
    cursor = conn.cursor()

    cursor.execute('''
    DELETE FROM group_message
    WHERE group_id = ? AND time < ?
    ''', (group_id, time))

    cursor.close()
    conn.commit()