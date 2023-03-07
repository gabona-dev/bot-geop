from datetime import date, timedelta
import schedule
import threading
import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from register import Register
from time import sleep
from db import DB

class Bot:
    bot = None
    id_list = []  # user to send news to
    token = ""
    user = ""
    password = ""
    day = []
    oldDB = []
    register = None
    COURSES = {}
    db = None
	
    def __init__(self):
        # create bot
        self.token = os.environ['TOKEN']

        self.register = Register(self.user, self.password)
        self.bot = telebot.TeleBot(self.token)

        self.db = DB()

        # load user to send automatic messages to
        with open('userFile.txt') as file:
            for line in file:
                line = line.strip()
                self.id_list.append(int(line))

        # scheduling newsletter and updates of lessons
        schedule.every(30).minutes.do(self.updateDB)
        schedule.every().day.at("06:00").do(self.newsletter)
        threading.Thread(target=self.handle_messages).start()


    def start(self):
        while True:
            schedule.run_pending()
            sleep(1)

    # Ottenere l'indirizzo email dell'utente
    def get_email(self, message, course):
        email = message.text
        self.bot.send_message(message.chat.id, 'Password:')
        self.bot.register_next_step_handler(message, self.get_password, email, course)

    # Ottenere la password dell'utente
    def get_password(self, message, email, course):
        psw = message.text

        self.register.set_credential(email, psw)
        self.updateDB()     # updates oldDB variable

        if (self.oldDB == self.register.CONNECTION_ERROR) or (self.oldDB == self.register.ERROR):
            self.bot.send_message(message.chat.id, "Errore nella configurazione nell'account. Per riprovare esegui il comando /start\n In caso di errore persistente contattta gli admin")
            return

        if(self.oldDB == self.register.WRONG_PSW):
            self.bot.send_message(message.chat.id, "Account non configurato: credenziali errate.\nPer riprovare esegui il comando /start")
            return

        self.save_user_info(message.chat.id, email, psw, course)
        self.bot.send_message(message.chat.id, 'Account configurato con successo!')


    # Funzione per salvare le informazioni dell'utente nel database
    def save_user_info(self, user_id, email, psw, course):
        self.db.connect()

        # if user does not already exists in the db then insert it
        if self.user_already_exists_in('users_login', user_id):
            self.db.query(
                'UPDATE users_login SET course=? WHERE id=?;',
                [course, user_id]
            )
        else:
            self.db.query(
                'INSERT INTO users_login VALUES (?,?,?,?);', 
                (user_id, email, psw, course)
            )

        # if user does not exists in the "user_newsletter" table then insert it
        if not self.user_already_exists_in('users_newsletter', user_id):
            self.db.query('INSERT INTO users_newsletter VALUES (?, ?, ?);', [{user_id}, course, False])
        
        self.db.close()
        return
        
           
    # Tastiera inline per la configurazione dell'account
    def create_courses_keyboard(self):

        keyboard = InlineKeyboardMarkup(row_width=2)
         
        with open("courses.txt", "r") as file:
            lines = file.readlines()
            #! The number of courses must be even 
            for i in range(0, len(lines)-1, 2):   # i add 2 buttons in one call, otherwise every button is displayed in a single row
                keyboard.add(InlineKeyboardButton(f'{lines[i]}', callback_data=f'{lines[i]}'), InlineKeyboardButton(f'{lines[i+1]}', callback_data=f'{lines[i+1]}'))
            
        return keyboard


    def handle_messages(self):

        @self.bot.message_handler(commands=['help'])
        def handle_help(message):
            help_msg = \
            "/help Visualizza questa guida\n" + \
            "/day  Lezione più recente\n" + \
            "/reg  Lezione da oggi + 7gg\n" + \
            "/news Notifica alle 7 sulla lezione del giorno"
            
            self.bot.reply_to(message, help_msg)

        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            self.bot.reply_to(message, "Benvenuto! Per configurare il tuo account, scegli il tuo corso:", reply_markup=self.create_courses_keyboard())


        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):

            self.db.connect()
            res = self.db.query("SELECT * FROM users_login WHERE course=?", [call.data,])

            if res != None:
                self.db.query("INSERT INTO users_newsletter VALUES (?, ?, ?)", [call.message.chat.id, call.data, False])
                self.bot.send_message(call.message.chat.id, "Account configurato!")
                self.db.close()
                return
            
            self.db.close()
            self.bot.send_message(call.message.chat.id, 'Nessun account configurato per questo corso, fornisci le seguenti informazioni:\n\nEmail:')
            self.bot.register_next_step_handler(call.message, self.get_email, call.data)


        @self.bot.message_handler(commands=['day'])
        def handle_day(message):
            id = message.from_user.id
            self.bot_print(self.day, id)

        @self.bot.message_handler(commands=['register', 'reg'])
        def handle_registro(message):
            id = message.from_user.id
            self.bot_print(self.oldDB, id)

        @self.bot.message_handler(commands=['news'])
        def echo_news(message, course):
            id = message.from_user.id
            self.db.connect()
            res = self.db.query("SELECT id FROM users_newsletter WHERE id=?", [id])

            if res == None:
                self.db.query("INSERT INTO users_newsletter VALUES (?, ?, ?)", [id, course, False])

            self.db.close()
            
        self.bot.polling()


    def newsletter(self):
        self.db.connect()
        self.id_list = self.db.query("SELECT id FROM users_newsletter")
        self.db.close()

        for user in self.id_list:
            self.bot_print(self.day, user)

    # Funzione per verificare se le informazioni dell'utente sono già state fornite
    def user_already_exists_in(self, table, user_id):
        res = self.db.query(f"SELECT * FROM {table} WHERE id=?", [user_id,])
        return res != None


    def updateDB(self):
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