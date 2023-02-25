from datetime import date, timedelta
import schedule
import threading
import os
import telebot
from register import Register
from time import sleep

class Bot:
    bot = None
    id_list = []  # user to send news to
    token = ""
    user = ""
    password = ""
    day = []
    oldDB = []
    register = None
	
    def __init__(self):
        # create bot
        self.token = os.environ['TOKEN']
        self.user = os.environ['Username']
        self.password = os.environ['Password']

        self.register = Register(self.user, self.password)
        self.bot = telebot.TeleBot(self.token)

        # load user to send automatic messages to
        with open('userFile.txt') as file:
            for line in file:
                line = line.strip()
                self.id_list.append(int(line))

        # update bot lessons database
        self.oldDB = self.register.requestGeop()
        self.day = self.register.requestGeop(date.today(), date.today()+timedelta(days=1))

        # scheduling newsletter and updates of lessons database
        schedule.every(30).minutes.do(self.checkDB)
        schedule.every().day.at("06:00").do(self.newsletter)
        threading.Thread(target=self.handle_messages).start()


    def start(self):
        while True:
            schedule.run_pending()
            sleep(1)

    def handle_messages(self):

        @self.bot.message_handler(commands=['help'])
        def handle_help(message):
            help_msg = \
            """
            /help\t\t\tVisualizza questa guida
            /day\t\t\tLezione più recente
            /registro, /reg\t\t\tLezione da oggi + 7gg
            /news\t\t\tNotifica alle 8 sulla lezione del giorno
            """
            self.bot.reply_to(message, help_msg)

        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.bot.reply_to(message, "Benvenuto")

        @self.bot.message_handler(commands=['day'])
        def handle_day(message):
            id = message.from_user.id
            self.bot_print(self.day, id)

        @self.bot.message_handler(commands=['register', 'reg'])
        def handle_registro(message):
            id = message.from_user.id
            self.bot_print(self.oldDB, id)

        @self.bot.message_handler(commands=['news'])
        def echo_news(message):
            id = message.from_user.id
            with open("userFile.txt", "a") as file:
                if id not in self.id_list:
                    self.id_list.append(id)
                    file.write(str(id) + "\n")
        self.bot.polling()

    def newsletter(self):
        for user in self.id_list:
            self.bot_print(self.day, user)

    def checkDB(self):
        newDB = self.register.requestGeop()
        self.oldDB = newDB
        self.day = self.register.requestGeop(date.today(), date.today()+timedelta(days=1))

    # id: user to send the message to
    def bot_print(self, lessons, id):

        lessons.sort(
            key=lambda l: (
                int(l["day"][0]), 
                int(l["day"][1]), 
                int(l["day"][2])
            )
        )

        for l in lessons:
            canPrintDay = True
            weekday, day, month, start, end = l["weekday"], l["day"], l["month"], l["start"], l["end"]
            teacher, subject, room = l["teacher"], l["subject"], l["room"]
            type_ = l["type"]
            previous_lesson_i = lessons.index(l) - 1

            if previous_lesson_i >= 0:
                previous_lesson = lessons[previous_lesson_i]
                if previous_lesson["day"] == day:
                    canPrintDay = False


            data = "-" * 26
            if canPrintDay:
                data = f"\n*{weekday[:3]} {day[2]} {month} {day[0]}* "

            orario = (f"-- *{start}-{end}*")
            docente = f"\n🧑‍🏫 | {teacher}"
            materia = f"\n📓 | {subject}" if not type_ == "esame" else  f"\n⚠️ | {subject}"
            stanza = f"\n🏢 | {room}"
            msg = data + orario + docente + materia + stanza            

            self.bot.send_message(id, msg, parse_mode='Markdown')
        return
