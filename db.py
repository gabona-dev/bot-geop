import sqlite3

class DB:

    """
        The database contains:
        - id
        - email
        - psw
        - course
        of the user that log into the register
        and a table of users to send automatic messages to
    """
    def __init__(self, db_name="database.db"):
        self.db_name = db_name
        self.conn = None
        self.cur = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cur = self.conn.cursor()

        self.cur.execute("CREATE TABLE IF NOT EXISTS users_login(id, email, psw, course, section)")     # section contains year and section ->1A, 2A...
        self.cur.execute("CREATE TABLE IF NOT EXISTS users_newsletter(id, course, section, can_send_news)")
    
    def query(self, query, values=[]):
        res = self.cur.execute(query, values)

        if "SELECT" in query.upper():
            return res.fetchone()      # result of the query

        elif "INSERT" in query.upper() or "UPDATE" in query.upper():
            self.conn.commit()

        return None

    def close(self):
        self.conn.close()
