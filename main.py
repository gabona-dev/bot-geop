from termcolor import colored
from bot import Bot
from utils import *


def main():

    # bot request
    bot = Bot()
    print(colored("[+] Bot started", "green"))
    bot.start()
    


if __name__ == '__main__':
    main()
