import os
import json
from termcolor import colored

MAIL_REGEX = "^[\w\-\.]+@itsrizzoli.it$"

def get_file_content(file_name):
    username = ""

    exe_path = os.path.expanduser('~')
    file_name = f"{exe_path}/{file_name}"

    with open(file_name, "r") as f:
        username = f.readline()

    return username

# def get_input_email():
#     return user

def swap(obj1, obj2):
    return obj2, obj1


def write_to_file(file_name, text):

    exe_path = os.path.expanduser('~')
    file_name = f"{exe_path}/{file_name}"

    with open(file_name, "w") as f:
        f.write(text) if not "dict" in str(type(text)) else json.dump(text, f)  # write as json if the type is a dictionary (json is double quoted, dictionary not)


# def get_cookies_of(session):
#     cookies = json.loads(get_file_content("cookies.json"))
#     utils.add_dict_to_cookiejar(session.cookies, cookies)


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
