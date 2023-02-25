from requests import Session, ConnectionError
from datetime import date, timedelta
from termcolor import colored
import calendar
import sys
from utils import *

class Register:
    user = ""
    psw = ""

    def __init__(self, user, psw):
        self.user = user
        self.psw = psw

    # Request lessons to geop and return a db containing the lessons processed by the function "extract_info()"
    def requestGeop(self, start_date="", end_date=""):
        
        start_date, end_date = self.correct_dates(start_date, end_date)

        site = "https://itsar.registrodiclasse.it"
        lessons_url = f"/geopcfp2/json/fullcalendar_events_alunno.asp?Oggetto=idAlunno&idOggetto=2672&editable=false&z=1665853136739&start={start_date}&end={end_date}&_=1665853136261"

        #* Getting cookie
        session = Session()
        try:
            cookies = get_cookies_of(session)

            if not is_cookie_valid_in(site + lessons_url, session):
                raise Exception()

        except ConnectionError as e:
            print(colored("Failed to connect. Check your internet connection", "red"))

        except:
            while True:
                try:
                    if can_login(self.user, self.psw, session, site):
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

            cookies = session.cookies.get_dict()
            write_to_file("cookies.json", cookies)

        #* Get lessons from the register
        MAX_ATTEMPTS = 3
        oldDB = ""
        for i in range(MAX_ATTEMPTS):
            url = site + lessons_url
            try:
                res = session.get(url)
                oldDB = self.extract_info(res.json())
                break

            except ConnectionError as e:
                print(colored("Failed to connect. Check your internet connection", "red"))
                sys.exit(1)

            except Exception as e:
                print(colored(e, "red"))
                if(i == MAX_ATTEMPTS-1):
                    sys.exit(1)
                continue

        return oldDB

    # checks if all dates are set
    def correct_dates(self, start_date, end_date):

        if start_date == "":
            start_date = date.today()

        if end_date == "":
            end_date = start_date + timedelta(
				days=8
			)  # default is +7, but the register doesn't count the last day provided when fetching the db
        return start_date, end_date

    # take a json "info" and takes lessons info
    def extract_info(self, info):

        WEEKDAY = [
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
            "Sunday"
        ]

        lessons = [
        ]  # list of dictionaries. used to sort the lessons before displaying them

        for _lesson in info:
            lesson = {}
            lesson["id"] = int(_lesson["id"])
            lesson["subject"] = _lesson["tooltip"].split("Materia:")[1].split("<br>")[0].strip().replace("Ã", "à")
            lesson["teacher"] = _lesson["tooltip"].split("Docente:")[1].split("<br>")[0].strip()
            lesson["start"] = _lesson["start"].split("T")[1][:-3].strip()
            lesson["end"] = _lesson["end"].split("T")[1][:-3].strip()
            lesson["room"] = _lesson["tooltip"].split("Aula:")[1].split("<br>")[0].strip()
            lesson["day"] = _lesson["start"].split("T")[0].split("-")
            lesson["month"] = calendar.month_abbr[int(lesson["day"][1])]
            weekday_num = calendar.weekday(
                                        int(lesson["day"][0]),
                                        int(lesson["day"][1]),
                                        int(lesson["day"][2])
                                        )
            lesson["weekday"] = WEEKDAY[weekday_num]
            lesson["type"] = _lesson["ClasseEvento"].lower()

            lessons.append(lesson)

        return lessons
