from cmu_graphics import *
import threading
import speech_recognition as sr
from thefuzz import process
import sys
import os
import time
from datetime import datetime
import tests
import math
import copy
import random

"""
Required Libraries:
- cmu_graphics
- threading
- speech_recognition
- openai
- thefuzz

Shortcode input format (4 chars, typed directly into the UI):
  <who><value><suit><y|n>
  who:   1-6  (player number shown on circle)
  value: A 2-9 T J Q K X(joker)
  suit:  H D C S  (or R/B for red/black joker)
  y/n:   Y = got it, N = didn't get it

  Example:  2JHY  →  ask player 2 for Jack of Hearts, got it
"""

# ── Shortcode helpers (module level) ────────────────────────────────────────

_VALUE_MAP = {
    'a': 'ace',   '2': 'two',   '3': 'three', '4': 'four',
    '5': 'five',  '6': 'six',   '7': 'seven', '8': 'eight',
    '9': 'nine',  't': 'ten',   'j': 'jack',  'q': 'queen',
    'k': 'king',  'x': 'joker'
}
_SUIT_MAP = {
    'h': 'hearts', 'd': 'diamonds', 'c': 'clubs', 's': 'spades',
    'r': 'red',    'b': 'black'
}

def getScale(app):
    # Fixed base dimensions for a wider 1400x800 layout
    # We'll use 800x600 as the "original" area for the table/input
    # and the extra width for the hand.
    return app.width / 1400, app.height / 800

def s(app, x, y):
    sx, sy = getScale(app)
    return x * sx, y * sy

def drawRectS(app, x, y, w, h, **kwargs):
    nx, ny = s(app, x, y)
    sx, sy = getScale(app)
    drawRect(nx, ny, w * sx, h * sy, **kwargs)


def drawCircleS(app, x, y, r, **kwargs):
    nx, ny = s(app, x, y)
    sx, sy = getScale(app)
    # Use min scale for circles to keep them circular
    avg_s = min(sx, sy)
    drawCircle(nx, ny, r * avg_s, **kwargs)


def drawOvalS(app, x, y, w, h, **kwargs):
    nx, ny = s(app, x, y)
    sx, sy = getScale(app)
    drawOval(nx, ny, w * sx, h * sy, **kwargs)


def drawLabelS(app, text, x, y, size=12, **kwargs):
    nx, ny = s(app, x, y)
    sx, sy = getScale(app)
    scale = min(sx, sy)
    drawLabel(text, nx, ny, size=size * scale, **kwargs)

def parse_shortcode(code, app):
    # Support 3-char codes for bots, 4-char for humans/declares
    if len(code) < 3:
        return None, "Shortcode too short"

    # NORMAL ASK (Target is first char)
    if code[0].isdigit():
        target_idx = int(code[0]) - 1
        if 0 <= target_idx < len(app.gameState.players):
            target = app.gameState.players[target_idx]

            # Bot: 3 chars allowed (automatic resolution)
            if target.isBot and len(code) == 3:
                val_char = code[1].lower()
                suit_char = code[2].lower()
                val = _VALUE_MAP.get(val_char)
                suit = _SUIT_MAP.get(suit_char)
                if not val or not suit: return None, "Invalid card"

                card = Card(val, suit)
                got_it = (card in target.hand)
                return Ask(app.gameState.playerWithTurn, target, card, got_it), None

    if len(code) != 4:
        return None, "Need 4 chars (3 for bots)"

    # DECLARE MODE
    if code[0].lower() == 'd':
        set_code = code[1:3].lower()
        result   = code[3].lower()

        set_map = {
            'lh': 'Low Hearts',
            'ld': 'Low Diamonds',
            'lc': 'Low Clubs',
            'ls': 'Low Spades',
            'hh': 'High Hearts',
            'hd': 'High Diamonds',
            'hc': 'High Clubs',
            'hs': 'High Spades',
            'ej': 'Eights and Jokers'
        }

        if set_code not in set_map:
            return None, "Invalid set code"

        if result not in ('y', 'n'):
            return None, "Must end in Y or N"

        return ("DECLARE", set_map[set_code], result == 'y'), None

    # ── ORIGINAL ASK LOGIC BELOW (unchanged) ──

    target_char = code[0]
    value_char  = code[1].lower()
    suit_char   = code[2].lower()
    got_char    = code[3].lower()

    try:
        target_idx = int(target_char) - 1
        if not (0 <= target_idx < len(app.gameState.players)):
            raise ValueError
        target = app.gameState.players[target_idx]
    except (ValueError, IndexError):
        return None, f"Player must be 1–{len(app.gameState.players)}"

    value = _VALUE_MAP.get(value_char)
    if not value:
        return None, f"Unknown value '{value_char.upper()}'"

    suit = _SUIT_MAP.get(suit_char)
    if not suit:
        return None, f"Unknown suit '{suit_char.upper()}'"

    if got_char not in ('y', 'n'):
        return None, "4th char must be Y or N"

    asker = app.gameState.playerWithTurn
    card  = Card(value, suit)
    return Ask(asker, target, card, got_char == 'y'), None


def _submit_shortcode(app):
    parsed, error = parse_shortcode(app.inputBuffer, app)
    app.inputBuffer = ''

    if error:
        app.illegalAskMessage = error
        return

    # DECLARE HANDLING
    if isinstance(parsed, tuple) and parsed[0] == "DECLARE":
        _, set_name, success = parsed

        current_team = app.gameState.playerWithTurn.team
        other_team   = 1 - current_team

        if set_name in app.gameState.completedSets:
            app.illegalAskMessage = "Set already declared"
            return

        if success:
            app.gameState.resolve_set(set_name, current_team, source="manual")
        else:
            app.gameState.resolve_set(set_name, other_team, source="manual")

        return

    # NORMAL ASK
    ask = parsed
    reason = Analyzer.isIllegalAsk(app.gameState, ask)

    if reason:
        app.illegalAskMessage = reason
    else:
        app.illegalAskMessage = None
        app.gameState.record_move(ask)
        print(f"  ✓  {ask}")


# ── Classes ──────────────────────────────────────────────────────────────────

class GameLogger:
    def __init__(self, enabled=True):
        self.enabled   = enabled
        self.directory = "games"
        if self.enabled:
            if not os.path.exists(self.directory):
                os.makedirs(self.directory)
            self.filename = self._get_filename()
        else:
            self.filename = None

    def _get_filename(self):
        date_str = datetime.now().strftime("%Y-%m-%d")
        game_num = 1
        while True:
            fname = os.path.join(self.directory, f"{date_str}_game_{game_num}.txt")
            if not os.path.exists(fname):
                return fname
            game_num += 1

    def log_move(self, move_str):
        if self.enabled and self.filename:
            with open(self.filename, "a") as f:
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{timestamp}] {move_str}\n")


class Card:
    def __init__(self, value, suit):
        digit_to_word = {
            '1': 'ace', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
            '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten'
        }
        self.value = digit_to_word.get(str(value), str(value))
        self.suit  = suit
        if self.value == 'joker' or self.value == 'eight':
            self.set = 'Eights and Jokers'
        elif self.value in ['two', 'three', 'four', 'five', 'six', 'seven']:
            self.set = f'Low {self.suit.capitalize()}'
        elif self.value in ['nine', 'ten', 'jack', 'queen', 'king', 'ace']:
            self.set = f'High {self.suit.capitalize()}'

    def __repr__(self):
        if self.value == 'joker':
            return f"{self.suit.capitalize()} Joker"
        return f"{self.value.capitalize()} of {self.suit.capitalize()}"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if not isinstance(other, Card): return False
        return self.value == other.value and self.suit == other.suit

    def __hash__(self):
        return hash((self.value, self.suit))

    @staticmethod
    def getAllCards():
        res = []
        for suit in ['hearts', 'diamonds', 'clubs', 'spades']:
            for val in ['ace', 'two', 'three', 'four', 'five', 'six', 'seven',
                        'eight', 'nine', 'ten', 'jack', 'queen', 'king']:
                res.append(Card(val, suit))
        res.append(Card('joker', 'black'))
        res.append(Card('joker', 'red'))
        return res


class Player:
    def __init__(self, name, team, isBot=False):
        self.name     = name
        self.handSize = 9
        self.team     = team
        self.isBot    = isBot
        self.hand     = set()

    def __repr__(self):
        return f"{self.name}{' (Bot)' if self.isBot else ''}"


class Team:
    def __init__(self, players):
        self.players   = players
        self.setsTaken = 0


class Ask:
    def __init__(self, asker, asked, card, gotCard=None):
        self.asker   = asker
        self.asked   = asked
        self.card    = card
        self.gotCard = gotCard

    def __repr__(self):
        asker_name = self.asker.name if isinstance(self.asker, Player) else str(self.asker)
        asked_name = self.asked.name if isinstance(self.asked, Player) else str(self.asked)
        res = "got it" if self.gotCard is True else ("didn't get it" if self.gotCard is False else "waiting...")
        return f"{asker_name.capitalize()} asked {asked_name.capitalize()} for {self.card} and {res}"


class LiteratureGame:
    def resolve_set(self, set_name, team_idx, source="auto"):
        if set_name in self.completedSets:
            return

        self.completedSets.add(set_name)
        self.teams[team_idx].setsTaken += 1

        print(f"[{source.upper()}] Team {team_idx} took {set_name}")

        # Clear info for that set
        for c in self.publicInfo[set_name]:
            self.publicInfo[set_name][c] = set()

        if self.teams[team_idx].setsTaken > 4:
            self.winner = self.teams[team_idx]

    def __init__(self, player_names, bot_cards=None, do_log=True, shuffle=False):
        # player_names is a list of 6 names in seating order.
        # Teams are alternating: Team 0: index 0, 2, 4; Team 1: index 1, 3, 5
        self.players = []
        for i, name in enumerate(player_names):
            isBot = (name.lower() == 'bot')
            p = Player(name, i % 2, isBot=isBot)
            self.players.append(p)

        self.teams = [
            Team([self.players[0], self.players[2], self.players[4]]),
            Team([self.players[1], self.players[3], self.players[5]])
        ]

        self.playerWithTurn = self.players[0]
        self.publicInfo     = dict()
        self.completedSets = set()

        for card in Card.getAllCards():
            if card.value in ['eight', 'joker']:
                group = 'Eights and Jokers'
            elif card.value in ['two', 'three', 'four', 'five', 'six', 'seven']:
                group = f'Low {card.suit.capitalize()}'
            else:
                group = f'High {card.suit.capitalize()}'

            if group not in self.publicInfo:
                self.publicInfo[group] = {}
            self.publicInfo[group][card] = set(self.players)

        if shuffle:
            all_cards = Card.getAllCards()
            random.shuffle(all_cards)
            for i, card in enumerate(all_cards):
                player = self.players[i % 6]
                player.hand.add(card)
                self.publicInfo[card.set][card] = {player}
        elif bot_cards:
            for p_idx, cards in bot_cards.items():
                if p_idx < len(self.players):
                    p = self.players[p_idx]
                    for c_str in cards:
                        c_str = c_str.strip().lower()
                        if not c_str: continue

                        val, suit = None, None
                        if c_str.startswith('10'):
                            val = 'ten'
                            if len(c_str) > 2: suit = _SUIT_MAP.get(c_str[2])
                        elif len(c_str) >= 2:
                            val = _VALUE_MAP.get(c_str[0])
                            suit = _SUIT_MAP.get(c_str[1])

                        if val and suit:
                            card = Card(val, suit)
                            p.hand.add(card)
                            self.publicInfo[card.set][card] = {p}

        self.logger = GameLogger(enabled=do_log)
        self.asks   = []
        self.winner = None

    def _apply_move(self, ask_object):
        """
        Mutate game state for one ask. Does NOT log or append to self.asks.
        Used by both record_move() and the analysis simulation.
        """
        gotCard  = ask_object.gotCard
        card     = ask_object.card
        asker    = ask_object.asker
        asked    = ask_object.asked
        card_set = card.set

        self.publicInfo[card_set][card] -= {asker}

        if gotCard:
            self.publicInfo[card_set][card] = {asker}
            self.playerWithTurn = asker
            if card in asked.hand:
                asked.hand.remove(card)
            asker.hand.add(card)
        else:
            self.publicInfo[card_set][card] -= {asked}
            self.playerWithTurn = asked

        playersInSet = set()
        for possible_players in self.publicInfo[card_set].values():
            playersInSet |= possible_players

        for i in range(len(self.teams)):
            team       = self.teams[i]
            other_team = self.teams[1 - i]

            numInSet = sum(1 for p in team.players if p in playersInSet)

            if numInSet == 0:
                self.resolve_set(card_set, 1 - i, source="auto")
                break

    def record_move(self, ask_object):
        if ask_object is None:
            return
        self.asks.append(ask_object)
        self.logger.log_move(str(ask_object))
        self._apply_move(ask_object)


class Analyzer:
    @staticmethod
    def isIllegalAsk(gameState, ask):
        info     = gameState.publicInfo
        asker    = ask.asker
        asked    = ask.asked
        card     = ask.card
        card_set = ask.card.set

        if asker == asked:
            return "You can't ask yourself"

        if asker.team == asked.team:
            return "You can't ask a teammate"

        if (asker.hand and card in asker.hand) or info[card_set][card] == {asker}:
            return f"You already have {card}"

        playersInSet = set()
        for possible_players in info[card_set].values():
            playersInSet |= possible_players

        # If the asker is a bot, we assume its known hand is its complete hand.
        if asker.isBot and asker.hand:
            asker_has_set = any(c.set == card_set for c in asker.hand)
            if not asker_has_set:
                return f"You have no cards in {card_set}"

        # For everyone (especially humans), we only block the ask if the
        # Observer has proven they don't have any cards in the set.
        if asker not in playersInSet:
            return f"You have no cards in {card_set}"

        return None

    @staticmethod
    def getAllLegalAsks(gameState, player):
        potentialPlayers = [p for p in gameState.players
                            if p.team != player.team]

        if not player.hand:
            return []

        possibleSets     = set(card.set for card in player.hand)
        potentialCards   = {c for c in Card.getAllCards()
                            if c.set in possibleSets and c not in player.hand}

        legal = []
        for card in potentialCards:
            for toAsk in potentialPlayers:
                ask = Ask(player, toAsk, card)
                if not Analyzer.isIllegalAsk(gameState, ask):
                    legal.append(ask)
        return legal

    @staticmethod
    def evaluatePosition(gameState, team_idx):
        team0 = gameState.teams[0]
        team1 = gameState.teams[1]

        if team0.setsTaken > 4:
            raw = math.inf
        elif team1.setsTaken > 4:
            raw = -math.inf
        else:
            raw = (team0.setsTaken - team1.setsTaken) * 100.0
            t0p = set(team0.players)
            t1p = set(team1.players)

            for card_info in gameState.publicInfo.values():
                t0_certain  = 0
                t1_certain  = 0
                active_count = 0

                for card, possible in card_info.items():
                    if not possible:
                        continue
                    active_count += 1
                    if len(possible) == 1:
                        holder = next(iter(possible))
                        if holder in t0p:
                            t0_certain += 1
                            raw += 5
                        else:
                            t1_certain += 1
                            raw -= 5
                    else:
                        t0c   = len(possible & t0p)
                        t1c   = len(possible & t1p)
                        total = t0c + t1c
                        if total > 0:
                            raw += (t0c - t1c) / total * 2

                if active_count > 0:
                    if t0_certain == active_count:
                        raw += 30
                    elif t1_certain == active_count:
                        raw -= 30

        return raw if team_idx == 0 else -raw

    @staticmethod
    def _label_move(got_card, delta, possible_size, asked_in_possible):
        if not got_card:
            if not asked_in_possible:
                return "Blunder",    'darkRed'
            if possible_size <= 2:
                return "Blunder",    'darkRed'
            if delta < -8:
                return "Mistake",    'crimson'
            if delta < -3:
                return "Inaccuracy", 'orangeRed'
            return "Risky",          'goldenrod'
        else:
            if delta >= 30:
                return "Brilliant!", 'darkGreen'
            if delta >= 12:
                return "Excellent",  'green'
            if delta >= 4:
                return "Good",       'limeGreen'
            return "Okay",           'olive'

    @staticmethod
    def analyzeReplay(moves, initial_game):
        sim = LiteratureGame(
            [p.name for p in initial_game.teams[0].players],
            [p.name for p in initial_game.teams[1].players],
            do_log=False
        )
        name_to_player = {p.name: p for p in sim.players}

        def translate(ask, ntp):
            return Ask(ntp[ask.asker.name], ntp[ask.asked.name],
                       ask.card, ask.gotCard)

        labels = []
        for ask in moves:
            team_idx         = ask.asker.team
            sim_ask          = translate(ask, name_to_player)
            possible_size    = len(sim.publicInfo[ask.card.set][ask.card])
            asked_in_possible = sim_ask.asked in sim.publicInfo[ask.card.set][ask.card]
            eval_before      = Analyzer.evaluatePosition(sim, team_idx)

            snap     = copy.deepcopy(sim)
            snap_ntp = {p.name: p for p in snap.players}
            snap._apply_move(translate(ask, snap_ntp))
            eval_after = Analyzer.evaluatePosition(snap, team_idx)

            delta = eval_after - eval_before
            labels.append(Analyzer._label_move(
                ask.gotCard, delta, possible_size, asked_in_possible))
            sim._apply_move(sim_ask)

        return labels


class Listener:
    def __init__(self, gameState):
        self.recognizer     = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0
        self.player_objects = gameState.players
        self.player_names   = [p.name for p in gameState.players]
        self.card_values    = ["joker","ace","2","3","4","5","6","7","8","9","10",
                               "two","three","four","five","six","seven","eight",
                               "nine","ten","jack","queen","king"]
        self.card_suits     = ["hearts","diamonds","clubs","spades","red","black"]

    def listen(self, current_asker):
        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                text  = self.recognizer.recognize_openai(
                    audio,
                    model="gpt-4o-mini-transcribe",
                    prompt=f"Card game: literature. Keywords: "
                           f"{self.card_values + self.card_suits + self.player_names}"
                ).lower()
                print(f"Heard: '{text}'")
                return self.parseText(text, current_asker)
            except Exception:
                return None

    def parseText(self, text, current_asker):
        found_suit   = None
        found_value  = None
        found_player = None
        thresh       = 70

        s_match, s_score = process.extractOne(text, self.card_suits)
        if s_score >= thresh: found_suit = s_match

        v_match, v_score = process.extractOne(text, self.card_values)
        if v_score >= thresh: found_value = v_match

        p_match, p_score = process.extractOne(text, self.player_names)
        if p_score >= thresh:
            for p in self.player_objects:
                if p.name == p_match:
                    found_player = p
                    break

        if found_suit and found_value and found_player:
            got_card = any(w in text for w in ['yes', 'got', 'here', 'have'])
            return Ask(current_asker, found_player, Card(found_value, found_suit), got_card)
        return None

    def background_listener(self, app):
        while app.isListening and app.gameState.winner is None:
            if not app.useMic:
                time.sleep(0.1)
                continue
            result_ask = self.listen(app.gameState.playerWithTurn)
            if result_ask:
                reason = Analyzer.isIllegalAsk(app.gameState, result_ask)
                if reason:
                    app.illegalAskMessage = reason
                else:
                    app.illegalAskMessage = None
                    app.gameState.record_move(result_ask)
                    print(f"  ✓  Recorded: {result_ask}")


class TestManager:
    @staticmethod
    def seed_card(game, player_idx, val, suit):
        player = game.players[player_idx]
        card   = Card(val, suit)
        game.publicInfo[card.set][card] = {player}

    @staticmethod
    def run_test_move(app, asker_idx, asked_idx, val, suit, got):
        asker = app.gameState.players[asker_idx]
        asked = app.gameState.players[asked_idx]
        card  = Card(val, suit)
        move  = Ask(asker, asked, card, got)
        if not Analyzer.isIllegalAsk(app.gameState, move):
            app.gameState.record_move(move)
            print(f"Test Move: {move}")

    @staticmethod
    def run_automated_test(app, test_key):
        all_tests = tests.get_test_cases()
        if test_key in all_tests:
            print(f"--- Running Test: {test_key} ---")
            for action in all_tests[test_key]:
                if action[0] == 'seed':
                    TestManager.seed_card(app.gameState, action[1], action[2], action[3])
                elif action[0] == 'move':
                    TestManager.run_test_move(app, action[1], action[2], action[3],
                                              action[4], action[5])
        else:
            print(f"Test '{test_key}' not found. Available: {list(all_tests.keys())}")


class LogParser:
    @staticmethod
    def parse_log(filename, game_players):
        moves          = []
        name_to_player = {p.name.lower(): p for p in game_players}
        if not os.path.exists(filename):
            return moves

        with open(filename, 'r') as f:
            for line in f:
                if ' asked ' not in line or ' for ' not in line:
                    continue
                try:
                    parts      = line.split(']', 1)[1].strip().split(' asked ')
                    asker_name = parts[0].lower()
                    rest       = parts[1].split(' for ')
                    asked_name = rest[0].lower()
                    card_and_res = rest[1].split(' and ')
                    card_str   = card_and_res[0]
                    got        = "got it" in card_and_res[1]

                    if " Joker" in card_str:
                        suit = card_str.replace(" Joker", "").lower()
                        card = Card("joker", suit)
                    else:
                        cp    = card_str.split(' of ')
                        card  = Card(cp[0].lower(), cp[1].lower())

                    asker = name_to_player.get(asker_name)
                    asked = name_to_player.get(asked_name)
                    if asker and asked:
                        moves.append(Ask(asker, asked, card, got))
                except Exception as e:
                    print(f"Error parsing line: {line}\n{e}")
        return moves


class TerminalInputHandler:
    def start(self, app):
        thread = threading.Thread(target=self._loop, args=(app,), daemon=True)
        thread.start()

    def _loop(self, app):
        try:
            tty = open('/dev/tty', 'r')
            print("Terminal input ready. Format: <asker> <target> <value> <suit> [got]")
        except Exception as e:
            print(f"Terminal input unavailable: {e}")
            return

        while True:
            try:
                sys.stdout.write('> ')
                sys.stdout.flush()
                line = tty.readline()
                if not line:
                    break
                line = line.strip().lower()
            except Exception as e:
                print(f"Terminal read error: {e}")
                break
            if line:
                self._handle(app, line)

    def _handle(self, app, line):
        name_to_player = {p.name.lower(): p for p in app.gameState.players}
        parts          = line.split()

        if len(parts) < 4:
            print("  ✗  Too few words. Format: <asker> <target> <value> <suit> [got]")
            return

        asker  = name_to_player.get(parts[0])
        target = name_to_player.get(parts[1])
        if not asker:
            print(f"  ✗  Unknown player '{parts[0]}'")
            return
        if not target:
            print(f"  ✗  Unknown player '{parts[1]}'")
            return

        try:
            card = Card(parts[2], parts[3])
        except Exception:
            print(f"  ✗  Could not parse card '{parts[2]} {parts[3]}'")
            return

        got    = len(parts) >= 5 and parts[4] == 'got'
        ask    = Ask(asker, target, card, got)
        reason = Analyzer.isIllegalAsk(app.gameState, ask)
        if reason:
            print(f"  ✗  Illegal: {reason}")
            app.illegalAskMessage = reason
        else:
            app.illegalAskMessage = None
            app.gameState.record_move(ask)
            print(f"  ✓  {ask}")


# ── Drawing helpers ──────────────────────────────────────────────────────────

# Players sit alternating teams clockwise from the bottom seat.
# Since command line input is now seating order, we display them sequentially.
_SEAT_ORDER  = [0, 1, 2, 3, 4, 5]
_TEAM_COLORS = ['dodgerBlue', 'tomato']

# Table geometry (pixels) - moved to the left
_TABLE_CX = 300   # center x
_TABLE_CY = 280   # center y
_PLAYER_R = 120    # center → player circle center
_CIRCLE_R = 30    # player circle radius


def _player_pos(app, seat_idx):
    cx, cy = _TABLE_CX, _TABLE_CY
    radius = _PLAYER_R

    angle = math.radians(90 - seat_idx * 60)

    x = cx + radius * math.cos(angle)
    y = cy + radius * math.sin(angle)

    return s(app, x, y)


def _draw_player_table(app):
    drawOvalS(app, _TABLE_CX, _TABLE_CY, 240, 160,
              fill='darkGreen', border='saddleBrown', borderWidth=3)

    drawLabelS(app, f"T1: {app.gameState.teams[0].setsTaken}",
               _TABLE_CX - 40, _TABLE_CY, size=18, bold=True, fill='lightCyan')

    drawLabelS(app, f"T2: {app.gameState.teams[1].setsTaken}",
               _TABLE_CX + 40, _TABLE_CY, size=18, bold=True, fill='lightCoral')

    for seat, pidx in enumerate(_SEAT_ORDER):
        player = app.gameState.players[pidx]
        px, py = _player_pos(app, seat)

        is_turn = (player == app.gameState.playerWithTurn)
        color = _TEAM_COLORS[player.team]

        if is_turn:
            # px, py are already scaled by s(app, x, y)
            # drawCircleS also scales, so we need to pass unscaled logical coords
            logical_px = px / (app.width/1400)
            logical_py = py / (app.height/800)
            drawCircleS(app, logical_px, logical_py,
                        _CIRCLE_R + 6, fill='gold', opacity=70)

        drawCircleS(app, px / (app.width/1400), py / (app.height/800),
                    _CIRCLE_R, fill=color, border='white', borderWidth=2)

        # Draw player number (1-6) inside the circle
        drawLabelS(app, str(pidx + 1), px, py,
                  size=20, bold=True, fill='white')

        drawLabelS(app, player.name.capitalize(), px, py + _CIRCLE_R + 15,
                  size=14, fill='black', bold=True)


def _draw_input_box(app):
    """Draw the 4-slot shortcode entry UI on the left panel."""
    BOX_Y  = 630
    SLOT_W = 80
    SLOT_H = 60
    GAP    = 15
    TOTAL  = 4 * SLOT_W + 3 * GAP
    SX0    = 300 - (TOTAL // 2)    # Centered under the table

    sy = BOX_Y

    # Error banner OR prompt label
    if app.illegalAskMessage:
        drawRectS(app, 50, sy, 500, 30, fill='crimson', border=None)
        drawLabelS(app, app.illegalAskMessage, 300, sy + 15,
                  size=14, bold=True, fill='white')
        sy += 40
    else:
        drawLabelS(app, "Type shortcode",
                  300, sy + 15, size=16, fill='slateGrey', bold=True)
        sy += 30

    # Column hint labels
    hints = ['Who', 'Val', 'Suit', 'Res']
    for i, hint in enumerate(hints):
        cx = SX0 + i * (SLOT_W + GAP) + SLOT_W // 2
        drawLabelS(app, hint, cx, sy, size=12, fill='slateGrey')
    sy += 20

    # Slots
    for i in range(4):
        sx     = SX0 + i * (SLOT_W + GAP)
        ch     = app.inputBuffer[i] if i < len(app.inputBuffer) else ''
        active = (i == len(app.inputBuffer))

        border = 'dodgerBlue' if active else 'lightSteelBlue'
        drawRectS(app,sx, sy, SLOT_W, SLOT_H, fill='white', border=border, borderWidth=2)

        if ch:
            drawLabelS(app, ch.upper(), sx + SLOT_W // 2, sy + SLOT_H // 2,
                      size=32, bold=True, fill='midnightBlue')
        elif active:
            drawLabelS(app, '_', sx + SLOT_W // 2, sy + SLOT_H // 2 + 5,
                      size=24, fill='lightBlue')


def perform_bot_move(app, bot):
    legal_asks = Analyzer.getAllLegalAsks(app.gameState, bot)
    if not legal_asks:
        print(f"  [BOT] {bot.name} has no legal asks.")
        return

    ask = random.choice(legal_asks)

    # Resolve gotCard
    target_info = app.gameState.publicInfo[ask.card.set][ask.card]
    if len(target_info) == 1:
        actual_holder = list(target_info)[0]
        ask.gotCard = (actual_holder == ask.asked)
    else:
        ask.gotCard = random.choice([True, False])

    app.gameState.record_move(ask)
    print(f"  [BOT] {ask}")


# ── Application logic ────────────────────────────────────────────────────────

def onAppStart(app):
    player_names = ['max', 'jack', 'alex', 'kevin', 'ben', 'darren']
    bot_cards = {}
    is_vs_bots = '--vs-bots' in sys.argv

    if is_vs_bots:
        player_names = ['You', 'bot', 'bot', 'bot', 'bot', 'bot']

    args = sys.argv[1:]

    # Extract names and inline hands (first 6 non-flag args)
    if not is_vs_bots:
        names_found = []
        for arg in args:
            if not arg.startswith('--') and not (arg in tests.get_test_cases() or arg == 'test'):
                if not os.path.exists(arg):
                    # Handle "bot:2H,3H" or "name:cards"
                    if ':' in arg:
                        name_part, cards_part = arg.split(':', 1)
                        bot_cards[len(names_found)] = cards_part.split(',')
                        names_found.append(name_part)
                    else:
                        names_found.append(arg)
            if len(names_found) == 6:
                break

        if len(names_found) == 6:
            player_names = names_found

    # Also check for the legacy --bot-cards flag
    for arg in args:
        if arg.startswith('--bot-cards='):
            bc_str = arg.split('=', 1)[1]
            for p_entry in bc_str.split(';'):
                if ':' in p_entry:
                    idx_str, cards_str = p_entry.split(':', 1)
                    try:
                        bot_cards[int(idx_str)] = cards_str.split(',')
                    except ValueError:
                        pass
    all_tests  = tests.get_test_cases()
    is_testing = 'test' in sys.argv or any(arg in all_tests for arg in sys.argv[1:])

    app.gameState = LiteratureGame(player_names, bot_cards=bot_cards,
                                   do_log=not is_testing, shuffle=is_vs_bots)

    app.isListening      = True
    app.useMic           = False
    app.replayMoves      = []
    app.replayLabels     = []
    app.replayIndex      = 0
    app.isReplay         = False
    app.stepDelay        = 60
    app.stepCount        = 0
    app.illegalAskMessage = None
    app.inputBuffer      = ''          # ← shortcode being typed

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == 'test':
            for test_key in all_tests:
                app.gameState = LiteratureGame(
                    player_names, bot_cards=bot_cards, do_log=False)
                TestManager.run_automated_test(app, test_key)
            print("\n" + "=" * 30)
            print("  ALL TESTS PASSED SUCCESSFULLY!  ")
            print("=" * 30 + "\n")
            return True
        elif arg in all_tests:
            app.gameState = LiteratureGame(
                player_names, bot_cards=bot_cards, do_log=False)
            TestManager.run_automated_test(app, arg)
        elif os.path.exists(arg) and arg.endswith('.txt'):
            app.replayMoves = LogParser.parse_log(arg, app.gameState.players)
            if app.replayMoves:
                app.isReplay     = True
                app.isListening  = False
                app.replayLabels = Analyzer.analyzeReplay(app.replayMoves, app.gameState)
                print(f"Loaded {len(app.replayMoves)} moves for replay.")
            else:
                print(f"Failed to parse or empty log: {arg}")

    if not app.isReplay and (not hasattr(app, 'thread') or not app.thread.is_alive()):
        app.listener = Listener(app.gameState)
        app.thread   = threading.Thread(
            target=app.listener.background_listener, args=(app,), daemon=True)
        app.thread.start()
        app.terminalInput = TerminalInputHandler()
        app.terminalInput.start(app)

    return False


def onKeyPress(app, key):
    # Reset always works
    if key == 'r':
        onAppStart(app)
        print("Game reset.")
        return

    # Replay controls
    if app.isReplay:
        if key == 'space':
            app.stepCount = app.stepDelay
        return

    # Live mode controls
    if key == 'm':
        app.useMic = not app.useMic
        print(f"Mic: {'On' if app.useMic else 'Off'}")
        return

    if key == 'escape':
        app.inputBuffer       = ''
        app.illegalAskMessage = None
        return

    if key == 'backspace':
        app.inputBuffer       = app.inputBuffer[:-1]
        app.illegalAskMessage = None
        return

    # Any single printable character feeds the 4-slot shortcode buffer
    if len(key) == 1 and len(app.inputBuffer) < 4:
        app.inputBuffer      += key
        app.illegalAskMessage = None

        # Early submit for bots
        if len(app.inputBuffer) == 3:
            try:
                target_idx = int(app.inputBuffer[0]) - 1
                if 0 <= target_idx < len(app.gameState.players):
                    target = app.gameState.players[target_idx]
                    if target.isBot:
                        _submit_shortcode(app)
                        return
            except:
                pass

        if len(app.inputBuffer) == 4:
            _submit_shortcode(app)


# DO NOT DELETE
def onStep(app):
    if app.isReplay and app.replayIndex < len(app.replayMoves):
        app.stepCount += 1
        if app.stepCount >= app.stepDelay:
            app.stepCount    = 0
            app.gameState.record_move(app.replayMoves[app.replayIndex])
            app.replayIndex += 1
    elif not app.isReplay and app.gameState.winner is None:
        currentPlayer = app.gameState.playerWithTurn
        if currentPlayer.isBot:
            app.stepCount += 1
            if app.stepCount >= app.stepDelay:
                app.stepCount = 0
                perform_bot_move(app, currentPlayer)


def _draw_user_hand(app):
    user = app.gameState.players[0]
    if not user.hand:
        return

    # Sort hand by set, then value/suit
    sorted_hand = sorted(list(user.hand), key=lambda c: (c.set, str(c)))

    # Hand section on the right side of the screen
    START_X = 600
    START_Y = 150
    CARD_W = 75
    CARD_H = 105
    X_SPACING = 85
    Y_SPACING = 125

    drawLabelS(app, "Your Hand:", START_X, START_Y - 40, size=22, bold=True, align='left', fill='midnightBlue')

    for i, card in enumerate(sorted_hand):
        row = i // 8
        col = i % 8
        px = START_X + col * X_SPACING
        py = START_Y + row * Y_SPACING

        # Card rectangle
        drawRectS(app, px, py, CARD_W, CARD_H, fill='white', border='black', borderWidth=1.5)

        # Card text
        color = 'red' if card.suit in ['hearts', 'diamonds', 'red'] else 'black'

        # Value shorthand
        val_short = card.value.capitalize()
        if val_short == 'Ten': val_short = '10'
        elif val_short == 'Ace': val_short = 'A'
        elif val_short == 'Jack': val_short = 'J'
        elif val_short == 'Queen': val_short = 'Q'
        elif val_short == 'King': val_short = 'K'
        elif val_short == 'Joker': val_short = 'X'
        else:
            v_map = {'two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9'}
            val_short = v_map.get(card.value, val_short[0])

        drawLabelS(app, val_short, px + 15, py + 18, size=20, bold=True, fill=color)

        # Suit shorthand
        suit_short = card.suit[0].upper()
        if card.value == 'joker': suit_short = 'J'
        drawLabelS(app, suit_short, px + CARD_W - 15, py + CARD_H - 18, size=18, fill=color)

def _draw_info_panel(app):
    # Legend and Description in bottom right area
    START_X = 600
    START_Y = 600

    # Legend
    drawLabelS(app, "Shortcode Legend:", START_X, START_Y, size=16, bold=True, align='left', fill='dimGrey')
    drawLabelS(app, "A=Ace  2–9  T=Ten  J=Jack  Q=Queen  K=King  X=Joker", START_X, START_Y + 25, size=12, align='left', fill='dimGrey')
    drawLabelS(app, "H=Hearts  D=Diamonds  C=Clubs  S=Spades  R=Red  B=Black", START_X, START_Y + 45, size=12, align='left', fill='dimGrey')
    drawLabelS(app, "Example: 2JH (Ask Player 2 for Jack of Hearts)", START_X, START_Y + 65, size=12, italic=True, align='left', fill='slateGrey')

    # Description
    desc_y = START_Y + 110
    drawLabelS(app, "About Literature:", START_X, desc_y, size=16, bold=True, align='left', fill='dimGrey')
    drawLabelS(app, "Literature is a strategy game of memory and deduction.", START_X, desc_y + 25, size=12, align='left', fill='dimGrey')
    drawLabelS(app, "Collect sets of 6 cards by asking opponents. Complete 5 sets to win!", START_X, desc_y + 45, size=12, align='left', fill='dimGrey')


def redrawAll(app):
    # Logical base dimensions for internal layout
    W, H = 1400, 800

    # Background
    drawRectS(app, 0, 0, W, H, fill='ghostWhite')

    # ── Header ──────────────────────────────────────────────────────────
    drawRectS(app, 0, 0, W, 60, fill='midnightBlue')
    drawLabelS(app, "Literature Game", W // 2, 30, size=32, bold=True, fill='white')

    # Left Panel Area (Table and Input)
    # TABLE_CX = 300, TABLE_CY = 300

    # ── Status bar ──────────────────────────────────────────────────────
    drawLabelS(app, "LIVE MODE", 300, 80, size=16, bold=True, fill='dimGrey')

    # ── Player table ─────────────────────────────────────────────────────
    # We'll rely on _draw_player_table using its own internal logic
    # but we should adjust its CX/CY if needed.
    _draw_player_table(app)

    # ── Turn bar ─────────────────────────────────────────────────────────
    drawRectS(app, 50, 520, 500, 40, fill='aliceBlue', border='lightSteelBlue', borderWidth=1)

    turn_text = f"Turn: {app.gameState.playerWithTurn.name.capitalize()}"
    if not app.isReplay and app.gameState.playerWithTurn.isBot:
        turn_text += " (Bot Thinking...)"

    drawLabelS(app, turn_text,
              300, 540, size=18, fill='navy', bold=True)

    # ── Last move ────────────────────────────────────────────────────────
    if app.gameState.asks:
        last = app.gameState.asks[-1]
        ms   = str(last)
        drawLabelS(app, ms, 300, 580, size=14, fill='darkSlateGrey')

        rc = 'darkGreen' if last.gotCard else 'darkRed'
        drawLabelS(app, "✓ SUCCESS" if last.gotCard else "✗ FAILED",
                  300, 605, size=16, bold=True, fill=rc)
    else:
        drawLabelS(app, "Waiting for first move...",
                  300, 580, size=16, italic=True, fill='grey')

    # ── Shortcode input box ─────────────────────────────────────────────
    if not app.isReplay:
        # We need to ensure _draw_input_box is positioned correctly
        # Let's adjust its internal BOX_Y if needed, or wrap it.
        _draw_input_box(app)

    # ── User Hand ────────────────────────────────────────────────────────
    _draw_user_hand(app)

    # ── Info Panel ───────────────────────────────────────────────────────
    _draw_info_panel(app)

    # ── Footer ───────────────────────────────────────────────────────────
    drawRectS(app, 0, H - 30, W, 30, fill='whitesmoke', border=None)
    drawLabelS(app, "R=Reset  Esc=Clear buffer  Bksp=Delete",
              W // 2, H - 15, size=12, fill='grey')

    # ── Winner overlay ────────────────────────────────────────────────────
    if app.gameState.winner:
        tn = 1 if app.gameState.winner == app.gameState.teams[0] else 2
        drawRectS(app, 0, 0, W, H, fill='black', opacity=60)
        drawRectS(app, W//2 - 200, H//2 - 50, 400, 100, fill='gold', border='white', borderWidth=3)
        drawLabelS(app, f"TEAM {tn} WINS!", W // 2, H // 2, size=40, bold=True)

def main():
    if 'test' in sys.argv:
        class DummyApp:
            def __init__(self):
                self.gameState   = None
                self.isListening = False
                self.useMic      = False
        onAppStart(DummyApp())
    else:
        # Final dimensions as requested: 1400 width, 800 height
        runApp(width=1400, height=800)



if __name__ == '__main__':
    main()
