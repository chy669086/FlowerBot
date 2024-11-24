import sqlite3
import datetime

from authconfigs import MAINPATH

conn = sqlite3.connect(f'{MAINPATH}/plugins/storage/wordCloud/group_message.db')

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS group_message 
    (group_id INTEGER, message TEXT, time TEXT)
''')

conn.commit()

# time is a datetime object
def insert(group_id: int, message: str, time: datetime.datetime = datetime.datetime.now()):
    cursor.execute('''
    INSERT INTO group_message (group_id, message, time)
    VALUES (?, ?, ?)
    ''', (group_id, message, time))
    conn.commit()

# start_time and end_time are datetime objects
def select_from_time_range(group_id: int, start_time: datetime.datetime, end_time: datetime.datetime):
    cursor.execute('''
    SELECT message FROM group_message
    WHERE group_id = ? AND time >= ? AND time <= ?
    ''', (group_id, start_time, end_time))
    mes = cursor.fetchall()
    return [x[0] for x in mes]

def select_all(group_id: int):
    cursor.execute('''
    SELECT message FROM group_message
    WHERE group_id = ?
    ''', (group_id,))
    mes = cursor.fetchall()
    return [x[0] for x in mes]

# time is a datetime object
def delete_before_time(group_id: int, time: datetime.datetime):
    cursor.execute('''
    DELETE FROM group_message
    WHERE group_id = ? AND time < ?
    ''', (group_id, time))
    conn.commit()