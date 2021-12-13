#!/usr/bin/env python3

import logging
import os
import sched
import subprocess
import time
from logging.handlers import RotatingFileHandler

import git
from dotenv import load_dotenv
from telegram.ext import CommandHandler
from telegram.ext import Updater

from bandec.bandec import Bandec

DIRECTORY = os.path.dirname(os.path.realpath(__file__)) + '/'
LAST_COMMIT_FILE = DIRECTORY + 'last_commit'

env_path = DIRECTORY + '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger('com.cusobucuba.local.sync')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh = RotatingFileHandler(DIRECTORY + 'logs/sync.log', mode='a', maxBytes=5 * 1024 * 1024, backupCount=1, encoding=None, delay=0)
fh.setFormatter(formatter)
logger.addHandler(fh)
local_repo = False

s = sched.scheduler(time.time, time.sleep)
scheduled_event = None

last_context = None
last_chat_id = None


def sync(update, context):
    logger.debug('Started sync')
    send_message(context, update.effective_chat.id, 'On it {name}, please wait.'.format(name=str(update.message.from_user.first_name)))
    run_command('cd {folder} && git pull origin master'.format(folder=local_repo))
    r = git.Repo.init(local_repo)
    last_commit = None
    if os.path.isfile(LAST_COMMIT_FILE):
        with open(LAST_COMMIT_FILE, 'r') as file:
            last_commit = file.readline().strip()

    remote_commit = str(r.head.commit)
    if remote_commit == last_commit:
        logger.debug('Already up to date')
        send_message(context, update.effective_chat.id, 'Already up to date!!')
    else:
        logger.debug('Will need to update {0} -> {1}'.format(remote_commit, last_commit))
        send_message(context, update.effective_chat.id, 'Starting sync, please leave server without work until further notice.')
        sync_db(update, context)
        send_message(context, update.effective_chat.id, 'Loading fixtures')
        run_command('php {folder}/bin/console doctrine:fixtures:load --append'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Installing assets as symbolic links')
        run_command('php {folder}/bin/console assets:install --symlink'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Cleaning production cache')
        run_command('rm -rf {folder}/var/cache/prod/*'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Cleaning development cache')
        run_command('rm -rf {folder}/var/cache/dev/*'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Restoring permissions')
        run_command('chmod -R 777 {folder}/var/cache/'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Done!! Go click the system!! 🎉🎉🎉')

        with open(LAST_COMMIT_FILE, 'w') as file:
            file.write(remote_commit)


def sync_db(update, context):
    logger.debug('Started sync db')
    send_message(context, update.effective_chat.id, 'Running db update')
    response = run_command('php {folder}/bin/console doctrine:schema:update --force'.format(folder=local_repo))
    send_message(context, update.effective_chat.id, response)


def run_command(command):
    return subprocess.run(command, shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8')


def send_message(context, chat_id, text):
    global last_chat_id
    global last_context
    logger.debug("Sending message to chat id: {chat}".format(chat=str(chat_id)))
    logger.debug(text)
    last_context = context
    last_chat_id = chat_id
    context.bot.send_message(chat_id=chat_id, text=text)


def reset(update, context):
    os.remove(LAST_COMMIT_FILE)
    send_message(context, chat_id=update.effective_chat.id, text="Ok, {name}, removed last commit log!".format(name=str(update.message.from_user.first_name)))


def hello(update, context):
    send_message(context, chat_id=update.effective_chat.id, text="Hello {name}, i'm a CUSOBU's bot. I'm here to help!".format(name=str(update.message.from_user.first_name)))


def money_check(update, context):
    send_message(context, chat_id=update.effective_chat.id, text="Ok, please let me check!")
    accounts = Bandec(logger).accounts()
    for entry in accounts:
        send_message(context, chat_id=update.effective_chat.id, text="Account {number}: {available} - {credit}".format(number=str(entry[0]), available=str(entry[2]), credit=str(entry[1])))


def check_accounts():
    global last_chat_id
    global last_context
    if last_context and last_chat_id:
        logger.debug('checking bank accounts')
        notifications = Bandec(logger).run_check()
        for entry in notifications:
            send_message(last_context, chat_id=last_chat_id, text=entry.message())
    else:
        logger.debug('Unable to check accounts without context')
    add_schedule()
    pass


def add_schedule():
    global scheduled_event
    logger.debug('Scheduled account check in 3600 seconds')
    scheduled_event = s.enter(3600, 1, check_accounts)  # , kwargs={'a': 'configuration'})
    s.run()


def init(token):
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('hello', hello))
    dispatcher.add_handler(CommandHandler('sync', sync))
    dispatcher.add_handler(CommandHandler('syncdb', sync_db))
    dispatcher.add_handler(CommandHandler('reset', reset))
    dispatcher.add_handler(CommandHandler('money', money_check))
    logger.debug('Started Telegram Bot')
    updater.start_polling()
    add_schedule()


if __name__ == "__main__":
    try:
        local_repo = os.getenv("REPO")
        if not os.path.exists(local_repo):
            print("Folder should exists")
        init(os.getenv("TOKEN"))
    except Exception as ex:
        logger.error(ex)
