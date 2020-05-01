import logging
import os
from logging.handlers import RotatingFileHandler

import fire
import git
from telethon import TelegramClient

logger = logging.getLogger('com.cusobucuba.local.sync')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh = RotatingFileHandler('logs/sync.log', mode='a', maxBytes=5 * 1024 * 1024, backupCount=1, encoding=None, delay=0)
fh.setFormatter(formatter)
logger.addHandler(fh)

LAST_COMMIT_FILE = 'last_commit'


class LeaveMissing(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def run_update(local_repo):
    if not os.path.exists(local_repo):
        print("Both folders should exists")

    logger.debug('Started sync')
    r = git.Repo.init(local_repo)
    last_commit = None
    if os.path.isfile(LAST_COMMIT_FILE):
        with open(LAST_COMMIT_FILE, 'r') as file:
            last_commit = file.readline().strip()

    logger.debug('Started Telegram Client')
    client = TelegramClient('COVID', 1346594, 'ba0c3974d7210cfda36f23460a93935b')
    client.start()

    remote_commit = str(r.head.commit)
    if remote_commit == last_commit:
        print('Already up to date')
    else:
        print('Will need to update', remote_commit, last_commit)

        client.loop.run_until_complete(send_message(client, 'Server >>> Starting sync, please leave server without work until further notice.'))
        os.system('cd {folder} && git pull origin master'.format(folder=local_repo))
        client.loop.run_until_complete(send_message(client, 'Server >>> Running db update'))
        os.system('cd {folder} && php bin/console doctrine:schema:update --force'.format(folder=local_repo))
        client.loop.run_until_complete(send_message(client, 'Server >>> Cleaning production cache'))
        os.system('cd {folder} && rm -rf var/cache/prod/*'.format(folder=local_repo))
        client.loop.run_until_complete(send_message(client, 'Server >>> Cleaning development cache'))
        os.system('cd {folder} && rm -rf var/cache/dev/*'.format(folder=local_repo))
        client.loop.run_until_complete(send_message(client, 'Server >>> Installing assets as symbolic links'))
        os.system('cd {folder} && php bin/console assets:install --symlink'.format(folder=local_repo))
        client.loop.run_until_complete(send_message(client, 'Server >>> Restoring permissions'))
        os.system('cd {folder} && chmod -R 777 var/cache/'.format(folder=local_repo))
        client.loop.run_until_complete(send_message(client, 'Server >>> Done!! Go click the system!! ;)'))

        with open(LAST_COMMIT_FILE, 'w') as file:
            file.write(remote_commit)

        client.loop.stop()
    client.disconnect()


async def send_message(client, message):
    entity = await client.get_input_entity('https://t.me/joinchat/KwCBW0yTMRVjbeU6jytUYg')
    await client.send_message(entity=entity, message=message)


if __name__ == "__main__":
    fire.Fire(run_update)
