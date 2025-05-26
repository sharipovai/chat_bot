import sqlite3
from datetime import datetime, timedelta
import config
import pandas as pd
import json

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    def create_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS user_information (user_id int PRIMARY KEY , user_name varchar(50), "
            "first_name varchar(50), registration_date varchar(50), model_name varchar(50))")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS chat_history (number INTEGER PRIMARY KEY AUTOINCREMENT, user_id int, "
            "role TEXT NOT NULL, content TEXT NOT NULL)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS statistics (number INTEGER PRIMARY KEY AUTOINCREMENT, date varchar(20), "
            "user_id varchar(5000), new_user int, unique_users int)")
        conn.commit()
        cur.close()
        conn.close()

    def write_statistics(self, parameter_name, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        today_date = (datetime.now()).strftime("%d.%m.%y")
        count = cur.execute(f"SELECT {parameter_name} FROM statistics WHERE date = '%s'"
                                         % today_date).fetchall()[0][0]
        count += 1
        cur.execute(f"UPDATE statistics SET {parameter_name}  = %d WHERE date = '%s'" % (count, today_date))
        conn.commit()
        user_id_str = str(cur.execute("SELECT user_id FROM statistics WHERE date = '%s'"
                                         % today_date).fetchall()[0][0])
        if str(user_id) not in user_id_str:
            user_id_str = str(user_id_str + "n" + str(user_id))
            cur.execute("UPDATE statistics SET user_id = ? WHERE date = ?", (user_id_str, today_date))
            conn.commit()
            unique_users = int(cur.execute("SELECT unique_users FROM statistics WHERE date = '%s'"
                                    % today_date).fetchall()[0][0])
            unique_users += 1
            cur.execute("UPDATE statistics SET unique_users = '%d' WHERE date = '%s'" % (unique_users, today_date))
            conn.commit()
        cur.close()
        conn.close()

    def get_date_str_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT date FROM statistics").fetchall()
        if len(result) > 0:
            result_list = [i[0] for i in result]
        else:
            result_list = []
        cur.close()
        conn.close()
        return result_list

    def write_new_date_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        today_date = (datetime.now()).strftime("%d.%m.%y")
        cur.execute("INSERT INTO statistics (date, user_id, new_user, unique_users) VALUES "
                    "('%s', '%d', '%d', '%d')" % (today_date, 0, 0, 0))
        conn.commit()
        cur.close()
        conn.close()

    def check_new_user(self, user_id):
        # for new user return 1
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM user_information WHERE user_id = '%d'" % user_id).fetchall()
        cur.close()
        conn.close()
        return not bool(len(result))

    def write_new_user(self, message):
        if not self.check_new_user(message.from_user.id):
            return
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        reg_date = datetime.now().strftime("%d.%m.%y")
        model_name = list(config.model_names.keys())[0]
        cur.execute('''
                        INSERT INTO user_information (
                            user_id, 
                            user_name, 
                            first_name, 
                            registration_date,
                            model_name
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, username, first_name, reg_date, model_name))
        conn.commit()
        cur.close()
        conn.close()

    def update_user_chat_history(self, user_id, role, content):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_user_chat_history(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT role, content FROM chat_history WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1]} for row in rows]

    def clear_chat_history(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute('''
            DELETE FROM chat_history
            WHERE user_id = ?
        ''', (user_id,))

        conn.commit()
        cur.close()
        conn.close()

    def get_user_model(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        model_name = cur.execute(f"SELECT model_name FROM user_information WHERE user_id = ?", (user_id, )).fetchall()[0][0]
        cur.close()
        conn.close()
        return model_name

    def update_user_model(self, user_id, model_name):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE user_information SET model_name = ? WHERE user_id = ?", (model_name, user_id))
        conn.commit()
        cur.close()
        conn.close()
