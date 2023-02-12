from requests import Session, utils, ConnectionError
from getpass import getpass
from sys import argv
from datetime import date, time, timedelta, datetime
from time import sleep
from termcolor import colored
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import calendar, json, re
import schedule
import time
import threading
import sys, os
import colorama
import telebot

#gestione id-pass login e bot
SERVICE_ACCOUNT_FILE = 'client_secret_769971844746-2qn00ltihibfvtrje4htdd676852ghno.apps.googleusercontent.com'
CALENDAR_ID = 'cef82a8362167dbcf8f6b21d22db000c8118ed398e4affea76c56db582b4e07f@group.calendar.google.com'
CLIENT_ID = '769971844746-2qn00ltihibfvtrje4htdd676852ghno.apps.googleusercontent.com'
CLIENT_SECRET = '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'
SCOPES = ['https://www.googleapis.com/auth/calendar']
token = os.environ['TOKEN']
user = os.environ['Username']
password = os.environ['Password']
colorama.init()
bot = telebot.TeleBot(token)
id_list=[]

# "info" is a list of json
def extract_info(info):

  WEEKDAY = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Sunday"
  ]
  SYMBOLS = {"ok": "✔", "dash": "-", "now": "¤", "cross": "x"}

  lessons = [
  ]  # list of dictionaries. used to sort the lessons before displaying them

  for _lesson in info:
    lesson = {}
    lesson["id"] = int(_lesson["id"])
    lesson["subject"] = _lesson["tooltip"].split("Materia:")[1].split(
      "<br>")[0].strip().replace("Ã", "à")
    lesson["teacher"] = _lesson["tooltip"].split("Docente:")[1].split(
      "<br>")[0].strip()
    lesson["start"] = _lesson["start"].split("T")[1][:-3].strip()
    lesson["end"] = _lesson["end"].split("T")[1][:-3].strip()
    lesson["room"] = _lesson["tooltip"].split("Aula:")[1].split(
      "<br>")[0].strip()
    lesson["day"] = _lesson["start"].split("T")[0].split("-")
    lesson["month"] = calendar.month_abbr[int(lesson["day"][1])]
    weekday_num = calendar.weekday(int(lesson["day"][0]),
                                   int(lesson["day"][1]),
                                   int(lesson["day"][2]))
    lesson["weekday"] = WEEKDAY[weekday_num]
    lesson["type"] = _lesson["ClasseEvento"].lower()

    lesson_date_start = datetime(int(lesson["day"][0]), int(lesson["day"][1]),
                                 int(lesson["day"][2]),
                                 int(lesson["start"].split(":")[0]),
                                 int(lesson["start"].split(":")[1]))
    lesson_date_end = datetime(int(lesson["day"][0]), int(lesson["day"][1]),
                               int(lesson["day"][2]),
                               int(lesson["end"].split(":")[0]),
                               int(lesson["end"].split(":")[1]))
    lesson["isDone"] = lesson_date_end < datetime.today()

    lesson["color"] = "white"
    lesson["symbol"] = SYMBOLS["dash"]

    if lesson["isDone"] == True:
      lesson["color"] = "cyan"
      lesson["symbol"] = SYMBOLS["ok"]

    elif (datetime.today() < lesson_date_end
          and datetime.today() > lesson_date_start
          and datetime.today().date() == lesson_date_start.date()):
      lesson["color"] = "green"
      lesson["symbol"] = SYMBOLS["now"]

    elif "sospensione didattica" in lesson["teacher"].lower():
      lesson["symbol"] = SYMBOLS["cross"]

    if lesson["type"] == "esame":
      lesson["color"] = "magenta"

    lessons.append(lesson)

  return lessons


# stampa a terminale json "lessons"
def print_lessons(lessons):

  lessons.sort(
    key=lambda l: (int(l["day"][0]), int(l["day"][1]), int(l["day"][2])))

  for l in lessons:
    canPrintDay = True
    symbol, weekday, day, month, start, end, color = l["symbol"], l[
      "weekday"], l["day"], l["month"], l["start"], l["end"], l["color"]
    teacher, subject, room = l["teacher"], l["subject"], l["room"]
    type_ = l["type"]

    previous_lesson_i = lessons.index(l) - 1
    if previous_lesson_i >= 0:
      previous_lesson = lessons[previous_lesson_i]
      if previous_lesson["day"] == day:
        canPrintDay = False

    if "sospensione didattica" in teacher.lower():
      print(
        colored(
          f"\n{symbol} {weekday[:3]} {day[2]} {month} {day[0]}, {start}-{end}",
          "red",
          attrs=["bold"]))
      print(colored("-" * 37, "red"))
      print(colored("Sospensione didattica", "red"))
      continue

    if not canPrintDay:
      print(" " * 19, end="")
      print(colored(f"{start}-{end}", color, attrs=["bold"]))
      print(colored(f"\t\t{teacher}\rTeacher: ", color))
      print(colored(f"\t\t{subject}\rSubject: ", color))
      print(colored(f"\t\t{room}\rRoom: ", color))
      continue

    print(colored(
      f"\n{symbol} {weekday[:3]} {day[2]} {month} {day[0]}, {start}-{end}",
      color,
      attrs=["bold"]),
          end="")
    print(
      colored(f" [Esame]" if type_ == "esame" else "",
              "magenta",
              attrs=["bold"]))
    print(colored("-" * 37, color))
    print(colored(f"\t\t{teacher}\rTeacher: ", color))
    print(colored(f"\t\t{subject}\rSubject: ", color))
    print(colored(f"\t\t{room}\rRoom: ", color))


def get_file_content(file_name):
  username = ""

  exe_path = os.path.expanduser('~')
  file_name = f"{exe_path}/{file_name}"

  with open(file_name, "r") as f:
    username = f.readline()

  return username


def get_input_email():
  return user


def swap(obj1, obj2):
  return obj2, obj1


# check data e username
def check_argv():

  start_date = ""
  end_date = ""
  username = ""

  used_plus_notation = False  # for example: geop +5

  for arg in argv[1:]:

    if arg == 'today':
      arg = date.today().strftime("%d-%m-%Y")
    elif arg == 'yesterday':
      arg = date.today() + timedelta(days=-1)
      arg = arg.strftime("%d-%m-%Y")
    elif arg == 'tomorrow':
      arg = date.today() + timedelta(days=1)
      arg = arg.strftime("%d-%m-%Y")

    if re.match(
        "^(0?[1-9]|[12][0-9]|3[01])(\-|\/)(0?[1-9]|1[012])(\-\d{4}|\/\d{4})?$",
        arg):  # [d]d-[m]m-yyyy

      arg = arg.replace("/", "-")

      if start_date != "" and end_date != "":
        print(
          colored(
            "Error: Too much dates passed.\nOnly the first two will be taken into consideration",
            "red"))
        continue

      d = int(arg.split("-")[0])
      m = int(arg.split("-")[1])
      try:
        y = int(arg.split("-")[2])
      except:
        y = date.today().year

      if start_date == "":
        start_date = date(y, m, d)
        continue

      end_date = date(y, m, d)
      if end_date < start_date:
        start_date, end_date = swap(start_date, end_date)

      # the register doesn't count the last day provided when fetching the db
      end_date += timedelta(days=1)

    elif re.match(
        "^\d{4}(\-|\/)(0?[1-9]|1[012])(\-|\/)(0?[1-9]|[12][0-9]|3[01])$",
        arg):  # yyyy-[m]m-[d]d

      arg = arg.replace("/", "-")

      if start_date != "" and end_date != "":
        print(
          colored(
            "Error: Too much dates passed.\nOnly the first two will be taken into consideration",
            "red"))
        continue

      d = int(arg.split("-")[2])
      m = int(arg.split("-")[1])
      y = int(arg.split("-")[0])

      if start_date == "":
        start_date = date(y, m, d)
        continue

      end_date = date(y, m, d)
      if end_date < start_date:
        start_date, end_date = swap(start_date, end_date)

      # the register doesn't count the last day provided when fetching the db
      end_date += timedelta(days=1)

    elif re.match("^[\+|-][\d]+$", arg):
      if start_date != "" and end_date != "":
        print(
          colored(
            "Error: Too much dates passed.\nOnly the first two will be taken into consideration",
            "red"))
        continue

      used_plus_notation = True
      try:
        days = int(arg.split("+")[1])
      except:
        days = -int(arg.split("-")[1])

      if start_date == "":
        start_date = date.today() + timedelta(days)
      else:
        end_date = start_date + timedelta(
          days + 1
        )  # +1 because the register doesn't take count of the last day provided when fetching the db

    elif re.match(MAIL_REGEX, arg):
      username = arg
      write_to_file("email.txt", username)

    else:
      print(colored(f"Unrecognized option {arg}", "red"))

  if used_plus_notation and end_date == "":
    end_date = start_date + timedelta(
      1
    )  # the register doesn't count the last day provided when fetching the db
    start_date = date.today()
    if start_date > end_date:
      start_date, end_date = swap(start_date, end_date)

  return start_date, end_date, username


def write_to_file(file_name, text):

  exe_path = os.path.expanduser('~')
  file_name = f"{exe_path}/{file_name}"

  with open(file_name, "w") as f:
    f.write(text) if not "dict" in str(type(text)) else json.dump(
      text, f
    )  # write as json if the type is a dictionary (json is double quoted, dictionary not)


def get_cookies_of(session):
  cookies = json.loads(get_file_content("cookies.json"))
  utils.add_dict_to_cookiejar(session.cookies, cookies)


def is_cookie_valid_in(url, session):

  res = session.get(
    url
  )  # no need to try-catch. Exceptions are handled externally from this function

  if res.status_code == 200:
    if "Sintassi non corretta" in res.text:  # cookie not valid anymore, asking for user's password
      return False
    return True
  else:
    raise Exception(colored(str(res.status) + " " + res.reason, "red"))


def can_login(username, psw, session, url):
  login_url = "/geopcfp2/update/login.asp?1=1&ajax_target=DIVHidden&ajax_tipotarget=login"
  body = {'username': username, 'password': password}

  url += login_url
  res = session.post(url, data=body)

  if res.status_code == 200:
    if "Username e password non validi" in res.text:  # valid password, ready to save cookies
      return False
    return True
  else:
    print(colored(str(res.status) + " " + res.reason, "red"))
  return False


# checks if all dates are set and converts dates to strings
def correct_dates(start_date, end_date):

  if start_date == "":
    start_date = date.today()
  if end_date == "":
    end_date = start_date + timedelta(
      days=8
    )  # default is +7, but the register doesn't count the last day provided when fetching the db

  # if "date" in str(type(start_date)):
  #   start_date = f"{start_date.year}-{start_date.month}-{start_date.day}"
  # if "date" in str(type(end_date)):
  #   end_date = f"{end_date.year}-{end_date.month}-{end_date.day}"
  print(start_date)
  print(end_date)
  return start_date, end_date


def get_presence(session):
  presence_url = "https://itsar.registrodiclasse.it/geopcfp2/json/data_tables_ricerca_registri.asp"
  presence_body = f"columns%5B0%5D%5Bdata%5D=idRegistroAlunno&columns%5B0%5D%5Bname%5D=idRegistroAlunno&columns%5B1%5D%5Bdata%5D=Giorno&columns%5B1%5D%5Bname%5D=Giorno&columns%5B2%5D%5Bdata%5D=Data&columns%5B2%5D%5Bname%5D=Data&columns%5B3%5D%5Bdata%5D=DataOraInizio&columns%5B3%5D%5Bname%5D=DataOraInizio&columns%5B4%5D%5Bdata%5D=DataOraFine&columns%5B4%5D%5Bname%5D=DataOraFine&columns%5B5%5D%5Bdata%5D=MinutiPresenza&columns%5B5%5D%5Bname%5D=MinutiPresenza&columns%5B6%5D%5Bdata%5D=MinutiAssenza&columns%5B6%5D%5Bname%5D=MinutiAssenza&columns%5B7%5D%5Bdata%5D=CodiceMateria&columns%5B7%5D%5Bname%5D=CodiceMateria&columns%5B8%5D%5Bdata%5D=Materia&columns%5B8%5D%5Bname%5D=Materia&columns%5B9%5D%5Bdata%5D=CognomeDocente&columns%5B9%5D%5Bname%5D=CognomeDocente&columns%5B10%5D%5Bdata%5D=Docente&columns%5B10%5D%5Bname%5D=Docente&columns%5B11%5D%5Bdata%5D=DataGiustificazione&columns%5B11%5D%5Bname%5D=DataGiustificazione&columns%5B12%5D%5Bdata%5D=Note&columns%5B12%5D%5Bname%5D=Note&columns%5B13%5D%5Bdata%5D=idLezione&columns%5B13%5D%5Bname%5D=idLezione&columns%5B14%5D%5Bdata%5D=idAlunno&columns%5B14%5D%5Bname%5D=idAlunno&columns%5B15%5D%5Bdata%5D=DeveGiustificare&columns%5B15%5D%5Bname%5D=DeveGiustificare&order%5B0%5D%5Bcolumn%5D=2&order%5B0%5D%5Bdir%5D=desc&order%5B1%5D%5Bcolumn%5D=3&order%5B1%5D%5Bdir%5D=desc&start=0&length=10000&search%5Bregex%5D=false&NumeroColonne=15&idAnnoAccademicoFiltroRR=13&MateriePFFiltroRR=0&RisultatiPagina=10000&SuffissoCampo=FiltroRR&DataDaFiltroRR={start_date_filter}&DataAFiltroRR={end_date_filter}&NumeroPagina=1&OrderBy=DataOraInizio&ajax_target=DIVRisultati&ajax_tipotarget=elenco_ricerca_registri&z=1666466657560"
  res = session.post(presence_url, data=presence_body)

  # extract info
  presences = []  # list of presence
  attendance = {}  # single json
  res = res.json()


def requestGeop(start_date, end_date):
  username = user
  start_date, end_date = correct_dates(start_date, end_date)

  site = "https://itsar.registrodiclasse.it"
  lessons_url = f"/geopcfp2/json/fullcalendar_events_alunno.asp?Oggetto=idAlunno&idOggetto=2672&editable=false&z=1665853136739&start={start_date}&end={end_date}&_=1665853136261"
  canGetCookie = True

  try:
    file_username = get_file_content("email.txt")
    if re.match(MAIL_REGEX, file_username) == None:
      raise Exception()
  except:
    file_username = ""

  if username == "":
    try:
      username = get_file_content("email.txt")
      if re.match(MAIL_REGEX, username) == None:
        raise Exception()
    except:
      username = get_input_email()
      write_to_file("email.txt", username)

  if username != file_username:  # if the username passed is different from the one saved, there is no point checking the cookie's validity
    canGetCookie = False

  #* Getting cookie
  session = Session()
  try:
    if not canGetCookie:
      raise Exception()

    cookies = get_cookies_of(session)

    if not is_cookie_valid_in(site + lessons_url, session):
      raise Exception()

  except ConnectionError as e:
    print(colored("Failed to connect. Check your internet connection", "red"))

  except:
    while True:
      try:
        if can_login(username, password, session, site):
          break
      except ConnectionError as e:
        print(
          colored("Failed to connect. Check your internet connection", "red"))
        sys.exit(1)
      except:
        print(colored("Something went wrong", "red"))
        sys.exit(1)
      else:
        print(colored("Wrong password", "red"))
      sleep(1)

    cookies = session.cookies.get_dict()
    write_to_file("cookies.json", cookies)

  # LESSONS
  url = site + lessons_url
  try:
    res = session.get(url)
    lessons = extract_info(res.json())
    print(lessons)
    print_lessons(lessons) if len(lessons) > 0 else print(colored(f"No lessons found", "yellow", attrs=["underline"]))
  except ConnectionError as e:
    print(colored("Failed to connect. Check your internet connection", "red"))
  except Exception as e:
    print(e)
    sys.exit(1)
  return lessons


def bot_print(lessons, id):

  lessons.sort(
    key=lambda l: (int(l["day"][0]), int(l["day"][1]), int(l["day"][2])))
  for l in lessons:
    canPrintDay = True
    symbol, weekday, day, month, start, end, color = l["symbol"], l[
      "weekday"], l["day"], l["month"], l["start"], l["end"], l["color"]
    teacher, subject, room = l["teacher"], l["subject"], l["room"]
    type_ = l["type"]
    previous_lesson_i = lessons.index(l) - 1

    if previous_lesson_i >= 0:
      previous_lesson = lessons[previous_lesson_i]
      if previous_lesson["day"] == day:
        canPrintDay = False

    if not canPrintDay:
      # bot.reply_to(message,{teacher})
      orario = f"*{start}-{end}*"
      docente = f"\n{teacher}"
      materia = f"\n{subject}"
      stanza = f"\n{room}"
      stringa = orario + docente + materia + stanza
      bot.send_message(id, stringa, parse_mode='Markdown')
      continue

    data = f"\n{symbol} {weekday[:3]} {day[2]} {month} {day[0]} {symbol}"
    bot.send_message(id, data, parse_mode='Markdown')
    orario = f"*{start}-{end}*"
    docente = f"\n{teacher}"
    materia = f"\n{subject}"
    stanza = f"\n{room}"
    stringa2 = orario + docente + materia + stanza
    bot.send_message(id, stringa2, parse_mode='Markdown')


def bot_print_day(lessons, id):
  lessons.sort(
    key=lambda l: (int(l["day"][0]), int(l["day"][1]), int(l["day"][2])))
  for l in lessons:
    canPrintDay = True
    symbol, weekday, day, month, start, end, color = l["symbol"], l[
      "weekday"], l["day"], l["month"], l["start"], l["end"], l["color"]
    teacher, subject, room = l["teacher"], l["subject"], l["room"]
    type_ = l["type"]
    previous_lesson_i = lessons.index(l) - 1

    if previous_lesson_i >= 0:
      previous_lesson = lessons[previous_lesson_i]
      if previous_lesson["day"] == day:
        canPrintDay = False

    if not canPrintDay:
      # bot.reply_to(message,{teacher})
      orario = f"*{start}-{end}*"
      docente = f"\n{teacher}"
      materia = f"\n{subject}"
      stanza = f"\n{room}"
      stringa = orario + docente + materia + stanza
      bot.send_message(id, stringa, parse_mode='Markdown')
      continue

    data = f"\n{symbol} {weekday[:3]} {day[2]} {month} {day[0]} {symbol}"
    bot.send_message(id, data, parse_mode='Markdown')
    orario = f"*{start}-{end}*"
    docente = f"\n{teacher}"
    materia = f"\n{subject}"
    stanza = f"\n{room}"
    stringa2 = orario + docente + materia + stanza
    bot.send_message(id, stringa2, parse_mode='Markdown')


def newsletter():
    for utente in id_list:
        bot_print(day,utente)
  # print("OK NEWS FUNZIONA")
#   with open('userFile.txt','r') as file:
#     for utente in file:
#       utente = utente.strip()
#       bot_print(lessons,utente)


def checkDB(oldDB):
  newDB = requestGeop("", "")
  if newDB != oldDB:
    newsletter(newDB)
    oldDB = newDB


def handle_messages():
  
    @bot.message_handler(commands=['start', 'help'])
    def handle_start(message):
      bot.reply_to(message, "Benvenuto")
    
    @bot.message_handler(commands=['day'])
    def handle_day(message):
      id = message.from_user.id
      bot_print(day, id)

    @bot.message_handler(commands=['registro'])
    def handle_registro(message):
      id = message.from_user.id
      bot_print(oldDB, id)

    @bot.message_handler(commands=['news'])
    def echo_news(message):
      id = message.from_user.id
      with open("userFile.txt", "a") as file:
        if id not in id_list:
          id_list.append(id)
          file.write(str(id) + "\n")
        
    bot.polling()

def main():
    global oldDB
    global day
    oldDB = requestGeop("", "")
    day = requestGeop(date.today(), date.today()+timedelta(days=2))
    schedule.every(30).minutes.do(checkDB,oldDB)
    schedule.every().day.at("06:00").do(newsletter)
    threading.Thread(target=handle_messages).start()
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
  main()