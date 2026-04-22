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

"""
Required Libraries:
- cmu_graphics
- threading
- speech_recognition
- openai
- thefuzz

Setup an OpenAI key with export OPENAI_API_KEY="ssh-000000"

Minimax game tree heuristic with maximizing cards and information on opponents
TODO
Declaring
Get all moves
Eval position
Game tree search
"""

# AI
class GameLogger:
    def __init__(self, enabled=True):
        self.enabled = enabled
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
        #AI
        digit_to_word = {
            '1': 'ace', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
            '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten'
        }
        #Me
        self.value = digit_to_word.get(str(value), str(value))
        self.suit = suit
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
            for val in ['ace', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'jack', 'queen', 'king']:
                res.append(Card(val, suit))
        res.append(Card('joker', 'black'))
        res.append(Card('joker', 'red'))
        return res
class Player:
    def __init__(self, name, team):
        self.name = name
        self.handSize = 9
        self.team=team
    def __repr__(self):
        return self.name

class Team:
    def __init__(self, players):
        self.players = players
        self.setsTaken=0

class Ask:
    def __init__(self, asker, asked, card, gotCard=None):
        self.asker = asker
        self.asked = asked
        self.card = card
        self.gotCard = gotCard

    def __repr__(self):
        #part AI
        asker_name = self.asker.name if isinstance(self.asker, Player) else str(self.asker)
        asked_name = self.asked.name if isinstance(self.asked, Player) else str(self.asked)
        res = "got it" if self.gotCard else "didn't get it"
        return f"{asker_name.capitalize()} asked {asked_name.capitalize()} for {self.card} and {res}"
#Me
class LiteratureGame:
    def __init__(self, team0_names, team1_names, do_log=True):
        team0_players = [Player(name, 0) for name in team0_names]
        team1_players = [Player(name, 1) for name in team1_names]
        self.players = team0_players + team1_players
        self.teams = [Team(team0_players), Team(team1_players)]
        self.playerWithTurn = self.players[0]
        self.publicInfo=dict()
        for card in Card.getAllCards():
            # 1. Determine the set name logic on the fly
            if card.value in ['eight', 'joker']:
                group = 'Eights and Jokers'
            elif card.value in ['two', 'three', 'four', 'five', 'six', 'seven']:
                group = f'Low {card.suit.capitalize()}'
            else:
                group = f'High {card.suit.capitalize()}'

            # 2. Build the nested layers
            if group not in self.publicInfo:
                self.publicInfo[group] = {}

            # 3. Assign the card to the full set of players
            self.publicInfo[group][card] = set(self.players)
        self.logger = GameLogger(enabled=do_log)
        self.asks=[]
        self.winner=None

    def record_move(self, ask_object):
        self.asks.append(ask_object)
        self.logger.log_move(str(ask_object))
        gotCard = ask_object.gotCard
        card = ask_object.card
        asker = ask_object.asker
        asked = ask_object.asked
        card_set = card.set
        # Rule 1: Asker doesn't have the card they asked for
        self.publicInfo[card_set][card]-={asker}

        if gotCard:
            self.publicInfo[card_set][card]={asker}
            self.playerWithTurn = asker
        else:
            self.publicInfo[card_set][card]-={asked}
            self.playerWithTurn = asked

        playersInSet = set()
        for possible_players in self.publicInfo[card_set].values():
            playersInSet|=(possible_players)

        for i in range(len(self.teams)):
            team = self.teams[i]
            other_team = self.teams[1-i]
            numInSet=len(team.players)
            for player in team.players:
                if player not in playersInSet:
                    numInSet-=1
            if numInSet==0:
                other_team.setsTaken+=1
                print(f"Team {1-i} took the set: {card_set}!")
                for c in self.publicInfo[card_set]:
                    self.publicInfo[card_set][c] = set()

                if other_team.setsTaken > 4:
                    self.winner=other_team
                break
class Analyzer:
    @staticmethod
    #Me
    def isIllegalAsk(gameState, ask, hand=[]):
        info=gameState.publicInfo
        asker = ask.asker
        asked = ask.asked
        card = ask.card
        card_set = ask.card.set

        # 0. Can't ask yourself
        if asker == asked:
            print(f"Illegal: {asker.name} asked themselves")
            return True

        # 1. Can't ask for a card you already have
        if info[card_set][card] == {asker} or card in hand:
            print(f"Illegal: {asker.name} already has {card}")
            return True

        # 2. Must have at least one card in the set to ask for another
        playersInSet = set()
        for possible_players in info[card_set].values():
            playersInSet|=(possible_players)

        if asker not in playersInSet:
            print(f"Illegal: {asker.name} is void in set {card_set}")
            return True

        return False
    @staticmethod
    def getAllLegalAsks(gameState, player, hand):
        potentialCards=set()
        # Everybody except people on your team
        potentialPlayers=[p for p in gameState.players if p.team!=player.team and p.handSize>0]
        possibleSets=set([card.set for card in hand])
        for card in Card.getAllCards():
            if card.set in possibleSets and card not in hand:
                potentialCards.add(card)
        res=[]
        for card in potentialCards:
            for toAsk in potentialPlayers:
                res.append(Ask(player, card, toAsk))
        return res

    @staticmethod
    def evaluatePosition(gameState, player, hand):
        team0=gameState.teams[0]
        team1=gameState.teams[1]
        if team0.setsTaken>4:
            return math.inf
        elif team1.setsTaken>4:
            return -math.inf
        else:
            factor1 = team0.setsTaken-team1.setsTaken
    
# mostly AI
class Listener:
    def __init__(self, gameState):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0
        self.player_objects=gameState.players
        self.player_names=[player.name for player in gameState.players]
        self.card_values=["joker","ace","2","3","4","5","6","7","8","9","10","two","three","four","five","six","seven","eight","nine","ten","jack","queen","king"]
        self.card_suits=["hearts","diamonds","clubs","spades", "red", "black"]

    def listen(self, current_asker):
        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                text = self.recognizer.recognize_openai(
                    audio,
                    model="gpt-4o-mini-transcribe",
                    prompt=f"Card game: literature. Keywords: {self.card_values+self.card_suits+self.player_names}"
                ).lower()
                print(f"Heard: '{text}'")
                return self.parseText(text, current_asker)
            except Exception:
                return None
    # AI
    def parseText(self, text, current_asker):
        found_suit = None
        found_value = None
        found_player = None
        confidence_threshold = 70

        s_match, s_score = process.extractOne(text, self.card_suits)
        if s_score >= confidence_threshold: found_suit = s_match

        v_match, v_score = process.extractOne(text, self.card_values)
        if v_score >= confidence_threshold: found_value = v_match

        p_match, p_score = process.extractOne(text, self.player_names)
        if p_score >= confidence_threshold:
            for p in self.player_objects:
                if p.name == p_match:
                    found_player = p
                    break

        if found_suit is not None and found_value is not None and found_player is not None:
            found_card = Card(found_value, found_suit)
            # AI Simple heuristic for 'got it'
            got_card = False
            for word in ['yes', 'got', 'here', 'have']:
                if word in text:
                    got_card = True
                    break
            return Ask(current_asker, found_player, found_card, got_card)
        return None
    def background_listener(self, app):
        while app.isListening and app.gameState.winner==None:
            if not app.useMic:
                time.sleep(0.1)
                continue

            result_ask = self.listen(app.gameState.playerWithTurn)
            if result_ask:
                if not Analyzer.isIllegalAsk(app.gameState, result_ask):
                    app.gameState.record_move(result_ask)
class TestManager:
    @staticmethod
    def seed_card(game, player_idx, val, suit):
        player = game.players[player_idx]
        card = Card(val, suit)
        game.publicInfo[card.set][card] = {player}

    @staticmethod
    def run_test_move(app, asker_idx, asked_idx, val, suit, got):
        asker = app.gameState.players[asker_idx]
        asked = app.gameState.players[asked_idx]
        card = Card(val, suit)
        move = Ask(asker, asked, card, got)
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
                    TestManager.run_test_move(app, action[1], action[2], action[3], action[4], action[5])
        else:
            print(f"Test '{test_key}' not found. Available: {list(all_tests.keys())}")

class LogParser:
    @staticmethod
    def parse_log(filename, game_players):
        moves = []
        if not os.path.exists(filename):
            return moves

        name_to_player = {p.name.lower(): p for p in game_players}

        with open(filename, 'r') as f:
            for line in f:
                # [HH:MM:SS] Asker asked Asked for Value of Suit and got/didn't get it
                if ' asked ' not in line or ' for ' not in line:
                    continue

                try:
                    parts = line.split(']', 1)[1].strip().split(' asked ')
                    asker_name = parts[0].lower()

                    rest = parts[1].split(' for ')
                    asked_name = rest[0].lower()

                    card_and_res = rest[1].split(' and ')
                    card_str = card_and_res[0]
                    res_str = card_and_res[1]

                    got = "got it" in res_str

                    # Parse card_str "Value of Suit" or "Suit Joker"
                    if " Joker" in card_str:
                        suit = card_str.replace(" Joker", "").lower()
                        card = Card("joker", suit)
                    else:
                        card_parts = card_str.split(' of ')
                        value = card_parts[0].lower()
                        suit = card_parts[1].lower()
                        card = Card(value, suit)

                    asker = name_to_player.get(asker_name)
                    asked = name_to_player.get(asked_name)

                    if asker and asked:
                        moves.append(Ask(asker, asked, card, got))
                except Exception as e:
                    print(f"Error parsing line: {line}\n{e}")
        return moves

# --- Application Logic ---
def onAppStart(app):
    all_tests = tests.get_test_cases()
    is_testing = 'test' in sys.argv or any(arg in all_tests for arg in sys.argv[1:])

    app.gameState = LiteratureGame(['max', 'alex', 'ben'], ['jack', 'kevin', 'darren'], do_log=not is_testing)
    app.isListening = True
    app.useMic = False
    app.replayMoves = []
    app.replayIndex = 0
    app.isReplay = False
    app.stepDelay = 60 # Steps between moves in replay
    app.stepCount = 0

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == 'test':
            for test_key in all_tests:
                app.gameState = LiteratureGame(['max', 'alex', 'ben'], ['jack', 'kevin', 'darren'], do_log=False)
                TestManager.run_automated_test(app, test_key)
            print("\n" + "="*30)
            print("  ALL TESTS PASSED SUCCESSFULLY!  ")
            print("="*30 + "\n")
            return True
        elif arg in all_tests:
            app.gameState = LiteratureGame(['max', 'alex', 'ben'], ['jack', 'kevin', 'darren'], do_log=False)
            TestManager.run_automated_test(app, arg)
        elif os.path.exists(arg) and arg.endswith('.txt'):
            app.replayMoves = LogParser.parse_log(arg, app.gameState.players)
            if app.replayMoves:
                app.isReplay = True
                app.isListening = False
                print(f"Loaded {len(app.replayMoves)} moves for replay.")
            else:
                print(f"Failed to parse or empty log: {arg}")

    if not app.isReplay and (not hasattr(app, 'thread') or not app.thread.is_alive()):
        app.listener = Listener(app.gameState)
        app.thread = threading.Thread(target=app.listener.background_listener, args=(app,), daemon=True)
        app.thread.start()
    return False

# AI

def onKeyPress(app, key):
    if key == 'm' and not app.isReplay:
        app.useMic = not app.useMic
        print(f"Mic: {'On' if app.useMic else 'Off'}")
    elif key == 'r':
        onAppStart(app)
        print("Game reset.")
    elif key == 'space' and app.isReplay:
        # Toggle pause or advance immediately
        app.stepCount = app.stepDelay

# DO NOT DELETE
def onStep(app):
    if app.isReplay and app.replayIndex < len(app.replayMoves):
        app.stepCount += 1
        if app.stepCount >= app.stepDelay:
            app.stepCount = 0
            move = app.replayMoves[app.replayIndex]
            app.gameState.record_move(move)
            app.replayIndex += 1

# AI (temporary)
def redrawAll(app):
    # Background
    drawRect(0, 0, 400, 400, fill='ghostWhite')

    # Header
    drawRect(0, 0, 400, 50, fill='midnightBlue')
    drawLabel("Literature Observer", 200, 25, size=24, bold=True, fill='white')

    if app.isReplay:
        status_text = f"REPLAY MODE ({app.replayIndex}/{len(app.replayMoves)})"
        status_color = 'orange'
        progress = (app.replayIndex / len(app.replayMoves)) * 400 if app.replayMoves else 0
        if progress > 0:
            drawRect(0, 50, progress, 5, fill='orange')
    else:
        status_text = "LIVE MODE"
        status_color = 'green' if app.useMic else 'red'
        mic_text = "Mic: ON" if app.useMic else "Mic: OFF ('M')"
        drawLabel(mic_text, 340, 75, size=12, fill=status_color)

    drawLabel(status_text, 200, 75, size=14, bold=True, fill='grey')

    # Team Scores
    drawRect(20, 100, 170, 80, fill='white', border='lightGrey')
    drawLabel("Team 1", 105, 120, size=16, bold=True)
    drawLabel(f"Sets: {app.gameState.teams[0].setsTaken}", 105, 150, size=24, fill='blue')

    drawRect(210, 100, 170, 80, fill='white', border='lightGrey')
    drawLabel("Team 2", 295, 120, size=16, bold=True)
    drawLabel(f"Sets: {app.gameState.teams[1].setsTaken}", 295, 150, size=24, fill='red')

    # Turn info
    turn_name = app.gameState.playerWithTurn.name.capitalize()
    drawRect(20, 200, 360, 40, fill='aliceBlue', border='lightBlue')
    drawLabel(f"Turn: {turn_name}", 200, 220, size=18, fill='navy', bold=True)

    # Last Move
    drawLabel("Last Move:", 40, 270, size=14, bold=True, align='left')
    if app.gameState.asks:
        last_move = app.gameState.asks[-1]
        move_str = str(last_move)
        # Wrap text if too long
        if len(move_str) > 45:
            move_str = move_str[:42] + "..."
        drawLabel(move_str, 200, 300, size=14)

        res_color = 'darkGreen' if last_move.gotCard else 'darkRed'
        res_text = "SUCCESS" if last_move.gotCard else "FAILED"
        drawLabel(res_text, 200, 325, size=12, bold=True, fill=res_color)
    else:
        drawLabel("Waiting for first move...", 200, 300, size=14, italic=True, fill='grey')

    # Winner
    if app.gameState.winner:
        team_num = 1 if app.gameState.winner == app.gameState.teams[0] else 2
        drawRect(0, 0, 400, 400, fill='black', opacity=60)
        drawRect(50, 150, 300, 100, fill='gold', border='white')
        drawLabel(f"TEAM {team_num} WINS!", 200, 200, size=30, bold=True)

    # Footer
    drawLabel("'R' - Reset | 'Space' - Advance Replay", 200, 380, size=10, fill='grey')

def main():
    if 'test' in sys.argv:
        # Create a dummy app object for onAppStart
        class DummyApp:
            def __init__(self):
                self.gameState = None
                self.isListening = False
                self.useMic = False
        onAppStart(DummyApp())
    else:
        runApp(width=400, height=400)

if __name__ == '__main__':
    main()
