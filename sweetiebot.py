#!/usr/bin/env python
# coding: utf-8

import redis
import sys
import logging
from utils import randomstr
#from time import sleep
from modules import MUCJabberBot, ResponsesFile, SweetieAdmin, \
    SweetieChat, SweetieLookup, SweetieMQ, FakeRedis, SweetieRoulette, \
    RestartException, SweetieMarkov, PBLogHandler, SweetieDe, SweetiePings
import time
import os
import traceback

log = logging.getLogger(__name__)

class Sweetiebot(object):
    def __init__(self, nickname, bot, lookup, mq, admin, chat, roulette,
                 sweetiede, pings):
        self.nickname = nickname
        self.bot = bot
        self.bot.unknown_command_callback = self.unknown_command
        self.lookup = lookup
        self.mq = mq
        self.admin = admin
        self.chat = chat
        self.roulette = roulette
        self.sweetiede = SweetieDe
        self.pings = pings

#    def join_room(self, room, nick):
#        connection = self.bot.connect()
#        if connection is None:
#            sleep(5)
#            log.error('connection failed .. sleeping for 5')
#            raise RestartException()
#        self.bot.join_room(room, nick)
#        self.chatroom = room

    def unknown_command(self, message):
        return self.chat.random_chat(message)

    def disconnect(self):
        self.bot.disconnect()

def build_sweetiebot(config=None):
    if config is None: import config
    resource = config.nickname + randomstr()
    if config.fake_redis:
        redis_conn = FakeRedis()
    else:
        redis_conn = redis.Redis('localhost')

    jid = config.username + '/' + resource
    nick = config.nickname
    room = config.chatroom
    password = config.password

    bot = MUCJabberBot(jid, password, room, nick)
    lookup = SweetieLookup(bot)
    admin = SweetieAdmin(bot, config.chatroom, config.mods)
    mq = SweetieMQ(config)
    de = SweetieDe(bot, admin, mq)
    actions = ResponsesFile('data/Sweetiebot.actions')
    sass = ResponsesFile('data/Sweetiebot.sass')
    markov = SweetieMarkov(redis_conn, 'data/banned_keywords.txt',
                           'data/preferred_keywords.txt',
                           'data/swap_words.txt')
    chat = SweetieChat(bot, actions, sass, config.chatroom, markov)
    roulette = SweetieRoulette(bot, admin)
    pings = SweetiePings(bot, redis_conn)

    sweet = Sweetiebot(config.nickname, bot, lookup, mq, admin, chat, roulette,
                       de, pings)
    return sweet

def setup_logging(config):
    logging.getLogger().setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    streamhandler = logging.StreamHandler()
    streamhandler.setLevel(logging.DEBUG if config.debug else logging.INFO)
    streamhandler.setFormatter(formatter)
    logging.getLogger().addHandler(streamhandler)

    filehandler = logging.FileHandler('sweetiebot.log')
    filehandler.setLevel(logging.DEBUG)
    filehandler.setFormatter(formatter)
    logging.getLogger().addHandler(filehandler)

    errorhandler = PBLogHandler(config)
    errorhandler.setLevel(logging.ERROR)
    errorhandler.setFormatter(formatter)
    logging.getLogger().addHandler(errorhandler)

if __name__ == '__main__':
    import config
    setup_logging(config)
    if '--test' in sys.argv:
        config.fake_redis = True
        config.chatroom = config.test_chatroom
    else:
        config.fake_redis = False

    while True:
        try:
            sweet = build_sweetiebot(config)
            while True: time.sleep(1)
        except RestartException:
            continue
        except Exception:
            traceback.print_exc()
        finally:
            if sweet is not None: sweet.disconnect()
        break

