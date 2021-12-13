import sqlite3


class Handler:
    def __init__(self):
        self.__con = sqlite3.connect('store.db')
        self.__cur = self.__con.cursor()
        self.__cur.execute('CREATE TABLE IF NOT EXISTS accounts (number text, credit real, available real)')

    def select_all(self, sql, params):
        self.__cur.execute(sql, params)
        return self.__cur.fetchall()

    def select_one(self, sql, params):
        self.__cur.execute(sql, params)
        return self.__cur.fetchone()

    def insert(self, sql, params):
        self.__cur.execute(sql, params)
        self.commit()

    def update(self, sql, params):
        self.__cur.execute(sql, params)
        self.commit()

    def commit(self):
        self.__con.commit()

    def close(self):
        self.__con.close()
