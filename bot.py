from datetime import date, timedelta
import schedule
import threading
import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
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
    db = None
    __course = ""
    __section = ""
	
    def __init__(self):
        # create bot
        self.token = os.environ['TOKEN']

        self.register = Register(self.user, self.password)
        self.bot = telebot.TeleBot(self.token)

        self.db = DB()

        # scheduling newsletter and updates of lessons
        schedule.every(30).minutes.do(self.updateDB)
        schedule.every().day.at("07:00").do(self.newsletter)
        threading.Thread(target=self.handle_messages).start()


    def start(self):
        while True:
            schedule.run_pending()
            sleep(1)

    # Ottenere l'indirizzo email dell'utente
    def get_email(self, message):
        email = message.text
        self.bot.send_message(message.chat.id, 'Password:')
        self.bot.register_next_step_handler(message, self.get_password, email)

    # Ottenere la password dell'utente
    def get_password(self, message, email):
        psw = message.text

        self.register.set_credential(email, psw)
        self.updateDB()     # updates oldDB variable

        if (self.oldDB == self.register.CONNECTION_ERROR) or (self.oldDB == self.register.ERROR):
            self.bot.send_message(message.chat.id, "Errore nella configurazione nell'account. Per riprovare esegui il comando /start\n In caso di errore persistente contattta gli admin")
            return

        if(self.oldDB == self.register.WRONG_PSW):
            self.bot.send_message(message.chat.id, "Account non configurato: credenziali errate.\nPer riprovare esegui il comando /start")
            return

        self.save_user_info(message.chat.id, email, psw)
        self.bot.send_message(message.chat.id, 'Account configurato con successo!')


    # Funzione per salvare le informazioni dell'utente nel database
    def save_user_info(self, user_id, email="", psw="", login_credentials=True):
        self.db.connect()

        if login_credentials:
            # if user does not already exists in the db then insert it
            if self.user_already_exists_in('users_login', user_id):
                self.db.query(
                    'UPDATE users_login SET course=?, section=? WHERE id=?;',
                    [self.__course, self.__section, user_id]
                )
            else:
                self.db.query(
                    'INSERT INTO users_login VALUES (?, ?, ?, ?, ?);', 
                    (user_id, email, psw, self.__course, self.__section)
                )

        # if user does not exists in the "user_newsletter" table then insert it
        if not self.user_already_exists_in('users_newsletter', user_id):
            self.db.query('INSERT INTO users_newsletter VALUES (?, ?, ?, ?);', [user_id, self.__course, self.__section, False])
        
        self.db.close()
        return
    
    
    def get_courses(self):
        lines = []
        with open("courses.txt", "r") as file:
            lines = file.readlines()

            for i in range(len(lines)):
                lines[i] = lines[i].replace('\n', '')
        
        return lines
 
           
    # Tastiera inline per la configurazione dell'account
    def create_courses_keyboard(self):

        keyboard = InlineKeyboardMarkup(row_width=2)
         
        courses = self.get_courses()

        #! The number of courses must be even 
        for i in range(0, len(courses)-1, 2):   # i add 2 buttons in one call, otherwise every button is displayed in a single row
            keyboard.add(
                InlineKeyboardButton(f'{courses[i]}', callback_data=f'{courses[i]}'),
                InlineKeyboardButton(f'{courses[i+1]}', callback_data=f'{courses[i+1]}')
            )        
        return keyboard
    
    def create_section_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=2)

        for sec in ["A","B"]:
            keyboard.add(
                InlineKeyboardButton("1° anno, sez. "+sec, callback_data="1"+sec), 
                InlineKeyboardButton("2° anno, sez. "+sec, callback_data="2"+sec)
            )
        return keyboard
                


    def handle_messages(self):

        @self.bot.message_handler(commands=['help'])
        def handle_help(message):
            help_msg = \
            "/start configura il tuo account" + \
            "/help Visualizza questa guida\n" + \
            "/day  Lezione più recente\n" + \
            "/week  Lezione da oggi + 7gg\n" + \
            "/news Notifica alle 7 sulla lezione del giorno"
            
            self.bot.reply_to(message, help_msg)

        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            self.bot.reply_to(message, "Benvenuto! Per configurare il tuo account, scegli il tuo corso:", reply_markup=self.create_courses_keyboard())


        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):

            if call.data == "1A" or  call.data == "1B" or call.data == "2A" or call.data == "2B":

                self.set_section(call.data)
                
                user_id = call.message.chat.id

                if self.there_is_a_user_configured_for(self.__course):

                    self.save_user_info(user_id, login_credentials=False)
                    self.bot.send_message(user_id, "Account configurato!")
                    self.db.close()
                    return
            
                self.bot.send_message(user_id, 'Nessun account configurato per questo corso, fornisci le seguenti informazioni:\n\nEmail:')
                self.bot.register_next_step_handler(call.message, self.get_email)
                    

            else:
                self.set_course(call.data)
                self.bot.send_message(call.message.chat.id, "Seleziona anno e sezione", reply_markup=self.create_section_keyboard())

            return


        @self.bot.message_handler(commands=['day'])
        def handle_day(message):
            user_id = message.from_user.id
            
            self.db.connect()

            res = self.db.query("SELECT course, section FROM users_newsletter WHERE id=?", [user_id])
            if res == None:
                self.send_configuration_message()
                self.db.close()
                return      
                  
            user_course, user_section = res[0], res[1]

            res = self.db.query("SELECT email, psw FROM users_login WHERE course=? AND section=?", [user_course, user_section])
            if res == None:
                self.send_configuration_message()
                self.db.close()
                return
            
            self.register.set_credential(res[0], res[1])
            self.updateDB(just_today=True)

            self.db.close()

            self.bot_print(self.day, user_id)

        @self.bot.message_handler(commands=['week'])
        def handle_week(message):
            user_id = message.from_user.id
            
            self.db.connect()

            res = self.db.query("SELECT course, section FROM users_newsletter WHERE id=?", [user_id])
            if res == None:
                self.send_configuration_message()
                self.db.close()
                return
                  
            user_course, user_section = res[0], res[1]

            res = self.db.query("SELECT email, psw FROM users_login WHERE course=? AND section=?", [user_course, user_section])
            if res == None:
                self.send_configuration_message()
                self.db.close()
                return
            
            self.register.set_credential(res[0], res[1])
            self.updateDB()

            self.db.close()

            self.bot_print(self.oldDB, user_id)

        @self.bot.message_handler(commands=['news'])
        def echo_news(message):
            id = message.from_user.id
            self.db.connect()
            
            # no need to check if the user is not present, because it is automatically inserted into the db during the config stage
            self.db.query("UPDATE users_newsletter SET can_send_news = 1 WHERE id = ?;", [id])

            self.db.close()

        try:    
            self.bot.polling()
        except Exception as e:
            print(e)
            print("Exception occured, restarting the function")
            sleep(5)
            threading.Thread(target=self.handle_messages).start()
            return


    def newsletter(self):

        courses = self.get_courses()
        self.db.connect()

        # per ogni corso, primo e secondo anno, sezioni A e B
        for course in courses:
            for year in {1, 2}:
                for section in {"A", "B"}:
                    login_user = self.db.query("SELECT email, psw FROM users_login WHERE course=? and section=? and year=?;", [course, section, year])
                    if login_user == None: continue
                    users = self.db.query("SELECT id FROM users_newsletter WHERE course=? and can_send_news=1 and section=? and year=?;", [course, section, year])

                    self.user, self.password = login_user[0], login_user[1]
                    self.updateDB(just_today=True)
                    self.register.set_credential(self.user, self.password)

                    for id in users:
                        self.bot_print(self.day, int(id))
            print(f"Sent news to {course} course")
            
        self.db.close()

        return

    # Funzione per verificare se le informazioni dell'utente sono già state fornite
    def user_already_exists_in(self, table, user_id):
        res = self.db.query(f"SELECT * FROM {table} WHERE id=?;", [user_id,])
        return res != None


    def updateDB(self, just_today=False):
        if not just_today:
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


    def set_course(self, course):
        self.__course = course

    def set_section(self, section):
        self.__section = section


    def there_is_a_user_configured_for(self, course):
        self.db.connect()
        res = self.db.query("SELECT * FROM users_login WHERE course=?;", [course,])

        # if there isn't an account configured for that course, ask for the credentials
        if res == None:
            self.db.close()
            return False
        
        self.db.close()
        return True
        