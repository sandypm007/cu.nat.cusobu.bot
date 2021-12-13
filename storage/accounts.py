from storage.handler import Handler


class Accounts:
    def __init__(self):
        self.__handler = Handler()

    def all(self):
        return self.__handler.select_all("select * from accounts", params={})

    def by_number(self, number):
        return self.__handler.select_one("select * from accounts where number=:number", {"number": number})

    def insert(self, number, credit, available):
        return self.__handler.insert("insert into accounts values (?, ?, ?)", (number, credit, available))

    def update(self, number, credit, available):
        return self.__handler.update("update accounts set credit = ?, available = ? where number = ?", (credit, available, number))
