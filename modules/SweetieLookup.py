from datetime import datetime
import pytz
import urllib.request, urllib.parse, urllib.error
import requests
from requests.exceptions import Timeout
import logging
import difflib
import json
import random
import re
from xml.etree import ElementTree as ET
from utils import logerrors, botcmd
from random import randint
from modules.MessageResponse import MessageResponse

log = logging.getLogger(__name__)

class SweetieLookup(object):

    id_dic = {"": ""}

    def __init__(self, bot, crest):
        self.bot = bot
        self.bot.load_commands_from(self)
        self.crest = crest

    def get_sender_username(self, mess):
        return self.bot.get_sender_username(mess)

    def chat(self, message):
        self.bot.send_groupchat_message(message)

    def ross(self):
        return random.choice([
            "In painting, you have unlimited power. You have the ability to move mountains. You can bend rivers. But when I get home, the only thing I have power over is the garbage",
            "You need the dark in order to show the light.",
            "Look around. Look at what we have. Beauty is everywhere - you only have to look to see it.",
            "Just go out and talk to a tree. Make friends with it.",
            "There's nothing wrong with having a tree as a friend.",
            "Trees cover up a multitude of sins.",
            "They say everything looks better with odd numbers of things. But sometimes I put even numbers - just to upset the critics.",
            "I remember when my Dad told me as a kid, 'If you want to catch a rabbit, stand behind a tree and make a noise like a carrot. Then when the rabbit comes by you grab him.' Works pretty good until you try to figure out what kind of noise a carrot makes...",
            "The secret to doing anything is believing that you can do it. Anything that you believe you can do strong enough, you can do. Anything. As long as you believe.",
            "Water's like me. It's laaazy ... Boy, it always looks for the easiest way to do things",
            "We artists are a different breed of people. We're a happy bunch.",
            "We don't make mistakes. We just have happy accidents.",
            "Talent is a pursued interest. Anything that you're willing to practice, you can do.",
            "I guess I'm a little weird. I like to talk to trees and animals. That's okay though; I have more fun than most people.",
            "I can't think of anything more rewarding than being able to express yourself to others through painting. Exercising the imagination, experimenting with talents, being creative; these things, to me, are truly the windows to your soul.",
            "Lets build a happy little cloud. Lets build some happy little trees.",
            "Believe that you can do it, 'cause you can do it."
            ])

    @botcmd
    @logerrors
    def argue(self, message):
        '''Get angry'''
        return self.ross()

    @botcmd
    @logerrors
    def rant(self, message):
        '''Rage at the dying of the light'''
        return self.ross()

    def format_isk(self, value):
        if value == 0 or value == float("inf"):
            return 'unavailable'

        return '{0:,} isk'.format(float(value))

    def get_prices(self, href, region, station):
        endpoint = '/market/{}/orders/?type={}'.format(region, href)

        log.debug('asking for prices at '+endpoint)
        try:
            apiresult = self.crest.get(endpoint).json()
            buy = 0
            sell = float("inf")
            for item in apiresult['items']:
                if item['location']['id'] != station: continue
                price = item['price']
                is_buy_order = item['buy']
                if is_buy_order and price > buy: buy = price
                if not is_buy_order and price < sell: sell = price

            return 'buy: ' + self.format_isk(buy) + ', sell: ' + self.format_isk(sell)
        except Exception as e:
            log.exception('error parsing CREST data')
            if 'apiresult' in locals():
                return "CREST is unhappy: "+apiresult[:200]
            return "Error getting market data: "+str(e)

    def read_ids(self):
        self.chat('Downloading latest typeid list from CREST (this might take a minute)')
        result = {}
        types_url = 'https://crest-tq.eveonline.com/market/types/'
        while types_url:
            try:
                types_res = requests.get(types_url, timeout=10)
                types = json.loads(types_res.text)
                for type in types['items']:
                    href = type['type']['href']
                    name = type['type']['name'].upper()
                    result[name] = href
                if 'next' in types:
                    types_url = types['next']['href']
                else:
                    types_url = None
            except Timeout as t:
                raise
            except Exception as e:
                log.exception(e)
        log.info('found {} typeid results'.format(len(result)))
        return result

    def id_lookup(self, name):
        if name.lower() == 'plex' or name.lower() == '30 day':
            return 'https://crest-tq.eveonline.com/inventory/types/44992/', name
        test = name
        test = test.upper()
        reply = None
        i_id = None
        i_name = None
        if len(self.id_dic) <= 1:
            self.id_dic = self.read_ids()

        log.debug('looking for '+test+' in id_dic')
        if test in list(self.id_dic.keys()):
            log.debug('.. found')
            reply = self.id_dic[test]
            log.debug(' .. sending '+test+', '+str(reply))
            return reply, test
        else:
            maybe = difflib.get_close_matches(
                test, list(self.id_dic.keys()), 1)
            if len(maybe) > 0:
                log.debug("maybe meant " + str(maybe))
                if maybe[0] in list(self.id_dic.keys()):
                    i_id = self.id_dic[maybe[0]]
                    i_name = maybe[0]
        return i_id, i_name

    @botcmd
    @logerrors
    def jita(self, message):
        return self.get_prices_response(message, 10000002, 60003760)

    @botcmd
    @logerrors
    def amarr(self, message):
        return self.get_prices_response(message, 10000043, 60008494)

    def get_prices_response(self, message, regionid, systemid):
        '''[item name] Look up prices in jita'''
        href, name = self.id_lookup(message.args)
        if href is None:
            return 'Couldn\'t find any matches'
        reply = self.get_prices(href, regionid, systemid)
        reply = message.sender_nick + ': '+name.title() + ' - ' + reply
        return reply

    class Bunch:
        __init__ = lambda self, **kw: setattr(self, '__dict__', kw)
        __getattr__ = lambda self, name: None

    def dice_error(self, message, *args):
        return SweetieLookup.Bunch(error=message.format(*args))

    def parse_dice(self, dice_spec):
        # scrap whitespace
        dice_spec = re.sub(r'\s+', '', dice_spec, re.UNICODE)

        # search for the d
        split = dice_spec.split('d', 1)
        if len(split) != 2:
            return self.dice_error("Dice need to be specified in the form 2d20 [>x] [<x] [!] [=] [+n]")
        dice_count = split[0]
        dice_type = split[1]

        try:
            # assume we only want one die if dice count is missing
            dice = 1 if dice_count == '' else int(dice_count)
        except:
            return self.dice_error("Sorry, don't know how to roll '{}' dice", dice_count)

        try:
            split_modifiers = re.split(r'(\d+|=|>|<|!|%|\+)', dice_type)
            split_modifiers = list(filter(len, split_modifiers))

            current_modifier = None
            threshold = None
            lt_threshold = None
            show_sum = False
            explode = False
            bonus = 0
            # iterate over dice spec, remembering what the last modifier was 
            # in order to interpret the different numbers
            for modifier in split_modifiers:
                if modifier.isdigit():
                    modifier_value = int(modifier)

                    if current_modifier == '>':
                        threshold = modifier_value
                    elif current_modifier == '<':
                        lt_threshold = modifier_value
                    elif current_modifier == '+':
                        bonus = modifier_value
                    else: 
                        assert(current_modifier is None)
                        sides = int(modifier)
                    current_modifier = None

                elif modifier == '%':
                    sides = 100
                elif modifier == '>' or modifier == '<' or modifier == '+':
                    current_modifier = modifier
                elif modifier == '=':
                    show_sum = True
                elif modifier == '!':
                    explode = True
                else:
                    raise "unknown modifier"

            return SweetieLookup.Bunch(
                    dice=dice,
                    sides=sides,
                    bonus=bonus,
                    threshold=threshold,
                    lt_threshold=lt_threshold,
                    show_sum=show_sum,
                    explode=explode)
        except:
            return self.dice_error("Sorry, don't know how to roll '{}'", dice_type)
        return SweetieLookup.Bunch(dice=dice, sides=sides)

    @botcmd
    def roll(self, message):
        '''[eg 5d20] Roll some dice'''
        try:
            dice_spec = self.parse_dice(message.args)
            if dice_spec.error:
                return dice_spec.error
            dice = dice_spec.dice
            sides = dice_spec.sides
        except Exception as e:
            log.exception('bad dice')
            return "Error parsing input"
        if dice > 25:
            return "Too many variables in possibility space, abort!"
        if sides > 20000000:
            return "Sides of dice too small, can't see what face is upright!"
        if sides == 1:
            return "Oh look, they all came up ones. Are you suprised? I'm suprised."
        if sides < 1:
            return "How do you make a dice with less than two sides?"
        if dice < 1:
            return "You want me to roll...less than one dice?"

        if (dice_spec.threshold and dice_spec.lt_threshold and
                dice_spec.threshold > dice_spec.lt_threshold):
            return "Requirements unsatisfactory: thresholds conflict. Try again."

        rolls = self.get_rolls(dice, sides)
        rolls = list(map(lambda x: x + dice_spec.bonus, rolls))

        if dice_spec.explode:
            rolls = self.explode_dice(rolls, sides)

        log.debug("roll result: {}".format(rolls))
        roll_list = ', '.join(map(str, rolls))
        if dice_spec.threshold or dice_spec.lt_threshold:
            gt = dice_spec.threshold
            lt = dice_spec.lt_threshold

            if not lt:
                success_count = len(list(filter(lambda x: x >= gt, rolls)))
            elif not gt:
                success_count = len(list(filter(lambda x: x <= lt, rolls)))
            else:
                success_count = len(list(filter(lambda x: (x <= lt and x >= gt), rolls)))

            roll_list += " ({} successes)".format(success_count)
        if dice_spec.show_sum:
            dice_sum = sum(rolls)
            roll_list += " (sum {})".format(dice_sum)
        return roll_list

    class ExplodingDice:
        def __init__(self, initialValue):
            self.rolls = [int(initialValue)]
        def last_roll(self):
            return self.rolls[-1]
        def add_roll(self, roll):
            self.rolls.append(int(roll))
            return self
        def sum(self):
            return sum(self.rolls)

    def explode_dice(self, rolls, sides):
        sides = int(sides)
        rolls = list(map(SweetieLookup.ExplodingDice, rolls))
        should_explode = lambda r: r.last_roll() == sides
        add_roll = lambda r, n: r.add_roll(n)
        unexploded_rolls = list(rolls)
        while any(unexploded_rolls):
            unexploded_rolls = list(filter(should_explode, unexploded_rolls))
            rerolls = self.get_rolls(len(unexploded_rolls), sides)
            unexploded_rolls = list(map(add_roll, unexploded_rolls, rerolls))

        return list(map(lambda x: x.sum(), rolls))

    def get_rolls(self, dice=1, sides=6):
        try:
            return [randint(1, sides) for i in range(dice)]
        except:
            return []

    @botcmd
    def date(self, message):
        '''Returns the current datetime in a bunch of timezones'''
        now = datetime.now(pytz.utc)
        usptz = pytz.timezone('US/Pacific')
        usetz = pytz.timezone('US/Eastern')
        evetz = pytz.timezone('UTC')
        uktz = pytz.timezone('Europe/London')
        eutz = pytz.timezone('Europe/Brussels')
        nztz = pytz.timezone('Pacific/Auckland')

        format = '%Y-%m-%d %H:%M %Z'
        dates = [now.astimezone(tz) for tz in [usptz, usetz, evetz, uktz, eutz, nztz]]
        dates = [date.strftime(format) for date in dates]
        return ('\n' + '\n'.join(dates)).replace('UTC', 'EVE')

    @logerrors
    def random_reddit_link(self, subreddit, domain_filter=None):
        luna_data = self.get('http://www.reddit.com/r/{}/new.json?limit=100'
                .format(subreddit))
        if luna_data is None: raise Exception('failed to call reddit api')
        link_data = self.get_children_of_type(json.loads(luna_data), 't3')
        if domain_filter:
            link_data = list(filter(
                lambda x: x['data']['domain'] in domain_filter,
                link_data))
        log.info('choosing one of {} links'.format(len(link_data)))
        choice = random.choice(link_data)
        link = choice['data']['url']
        text = choice['data']['title']
        html = '<a href="{}">{}</a>'.format(link, text)
        plain = '{} [ {} ]'.format(text, link)
        return MessageResponse(plain, None, html=html)

    @botcmd
    @logerrors
    def ferret(self, message):
        '''Ferret!'''
        return self.random_reddit_link('ferret', ('imgur.com', 'i.imgur.com'))

    @botcmd
    @logerrors
    def woon(self, message):
        '''loona woona'''
        luna_data = self.get('http://www.reddit.com/r/princessluna/new.json?limit=100')
        if luna_data is None: raise Exception('failed to call reddit api')
        link_data = self.get_children_of_type(json.loads(luna_data), 't3')

        kyuu_data = self.get('http://www.reddit.com/user/kyuuketsuki.json?limit=100')
        if kyuu_data is None: raise Exception('failed to call reddit api')
        link_title_data = self.get_children_of_type(json.loads(kyuu_data), 't1')

        log.info('choosing one of {} links'.format(len(link_data)))
        log.info('choosing one of {} comments'.format(len(link_title_data)))
        link = random.choice(link_data)['data']['url']
        text = random.choice(link_title_data)['data']['body']
        text = re.split('\.|!|\?', text)[0]
        html = '<a href="{}">{}</a>'.format(link, text)
        plain = '{} [ {} ]'.format(text, link)
        return MessageResponse(plain, None, html=html)

    def get_children_of_type(self, reddit_data, kind):
        if type(reddit_data) is dict:
            return self.get_children_from_listing(reddit_data, kind)

        result = []
        for listing in reddit_data:
            for child in self.get_children_from_listing(listing, kind):
                result.append(child)
        return result

    def get_children_from_listing(self, listing_data, kind):
        result = []
        for child in listing_data['data']['children']:
            if child['kind'] == kind:
                result.append(child)
        return result

    def get(self, url, extra_headers={}):
        try:
            headers = {
                    'user-agent': 'sweetiebot',
                    'cache-control': 'no-cache'
            }
            headers.update(extra_headers)
            log.debug('requesting {} with headers {}'.format(url, str(headers)))
            res = requests.get(url, timeout=10, headers=headers)
            return res.text
        except Exception as e:
            log.warning("error fetching url "+url+" : "+str(e))
            return None

