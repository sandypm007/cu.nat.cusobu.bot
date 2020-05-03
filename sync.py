#!/usr/bin/env python3

import logging
import os
from logging.handlers import RotatingFileHandler

import fire
import git
from telegram.ext import CommandHandler
from telegram.ext import Updater

LAST_COMMIT_FILE = 'last_commit'
DIRECTORY = os.path.dirname(os.path.realpath(__file__)) + '/'

logger = logging.getLogger('com.cusobucuba.local.sync')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh = RotatingFileHandler(DIRECTORY + 'logs/sync.log', mode='a', maxBytes=5 * 1024 * 1024, backupCount=1, encoding=None, delay=0)
fh.setFormatter(formatter)
logger.addHandler(fh)
local_repo = False


def sync(update, context):
    logger.debug('Started sync')
    os.system('cd {folder} && git pull origin master'.format(folder=local_repo))
    r = git.Repo.init(local_repo)
    last_commit = None
    if os.path.isfile(LAST_COMMIT_FILE):
        with open(LAST_COMMIT_FILE, 'r') as file:
            last_commit = file.readline().strip()

    remote_commit = str(r.head.commit)
    if remote_commit == last_commit:
        logger.debug('Already up to date')
    else:
        logger.debug('Will need to update {0} -> {1}'.format(remote_commit, last_commit))
        logger.debug('Started Telegram Client')
        send_message(context, update.effective_chat.id, 'Server >>> Attempt to sync project!')

        send_message(context, update.effective_chat.id, 'Server >>> Starting sync, please leave server without work until further notice.')
        send_message(context, update.effective_chat.id, 'Server >>> Running db update')
        os.system('cd {folder} && php bin/console doctrine:schema:update --force'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Server >>> Cleaning production cache')
        os.system('cd {folder} && rm -rf var/cache/prod/*'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Server >>> Cleaning development cache')
        os.system('cd {folder} && rm -rf var/cache/dev/*'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Server >>> Installing assets as symbolic links')
        os.system('cd {folder} && php bin/console assets:install --symlink'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Server >>> Restoring permissions')
        os.system('cd {folder} && chmod -R 777 var/cache/'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Server >>> Done!! Go click the system!! ;)')

        with open(LAST_COMMIT_FILE, 'w') as file:
            file.write(remote_commit)


def send_message(context, chat_id, text):
    context.bot.send_message(chat_id=chat_id, text=text)


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a OnData bot. I'm here to help!")


def init(local):
    global local_repo
    if not os.path.exists(local):
        print("Folder should exists")
    local_repo = local
    updater = Updater(token='1158809155:AAGI91jBYs4G5vlzlRQgDSUIAKL0hQrdnYk', use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    start_handler = CommandHandler('sync', sync)
    dispatcher.add_handler(start_handler)
    updater.start_polling()


if __name__ == "__main__":
    try:
        fire.Fire(init)
    except Exception as ex:
        logger.error("Unhandled exception {0}".format(ex))
