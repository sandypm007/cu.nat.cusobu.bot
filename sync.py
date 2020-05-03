#!/usr/bin/env python3

import logging
import os
from logging.handlers import RotatingFileHandler

import git
from dotenv import load_dotenv
from telegram.ext import CommandHandler
from telegram.ext import Updater

LAST_COMMIT_FILE = 'last_commit'
DIRECTORY = os.path.dirname(os.path.realpath(__file__)) + '/'

env_path = DIRECTORY + '.env'
load_dotenv(dotenv_path=env_path)

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
        send_message(context, update.effective_chat.id, 'Already up to date!!')
    else:
        logger.debug('Will need to update {0} -> {1}'.format(remote_commit, last_commit))
        logger.debug('Started Telegram Client')
        send_message(context, update.effective_chat.id, 'Attempt to sync project!')

        send_message(context, update.effective_chat.id, 'Starting sync, please leave server without work until further notice.')
        send_message(context, update.effective_chat.id, 'Running db update')
        os.system('cd {folder} && php bin/console doctrine:schema:update --force'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Cleaning production cache')
        os.system('cd {folder} && rm -rf var/cache/prod/*'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Cleaning development cache')
        os.system('cd {folder} && rm -rf var/cache/dev/*'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Installing assets as symbolic links')
        os.system('cd {folder} && php bin/console assets:install --symlink'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Restoring permissions')
        os.system('cd {folder} && chmod -R 777 var/cache/'.format(folder=local_repo))
        send_message(context, update.effective_chat.id, 'Done!! Go click the system!! ;)')

        with open(LAST_COMMIT_FILE, 'w') as file:
            file.write(remote_commit)


def send_message(context, chat_id, text):
    context.bot.send_message(chat_id=chat_id, text=text)


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a OnData bot. I'm here to help!")


def init(token):
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    start_handler = CommandHandler('sync', sync)
    dispatcher.add_handler(start_handler)
    updater.start_polling()


if __name__ == "__main__":
    try:
        local_repo = os.getenv("REPO")
        if not os.path.exists(local_repo):
            print("Folder should exists")
        init(os.getenv("TOKEN"))
    except Exception as ex:
        logger.debug(ex)
