from cmu_graphics import *
import threading
import speech_recognition as sr
from thefuzz import process
import sys
import os
import time
from datetime import datetime
import tests

"""
Required Libraries:
- cmu_graphics
- threading
- speech_recognition
- openai
- thefuzz

Setup an OpenAI key with export OPENAI_API_KEY="ssh-000000"
"""

# AI
class GameLogger:
    def __init__(self):
        self.directory = "games"
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        self.filename = self._get_filename()

    def _get_filename(self):
        date_str = datetime.now().strftime("%Y-%m-%d")
        game_num = 1
        while True:
            fname = os.path.join(self.directory, f"{date_str}_game_{game_num}.txt")
            if not os.path.exists(fname):
                return fname
            game_num += 1

    def log_move(self, move_str):
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

class Player:
    def __init__(self, name, cards_by_set):
        self.name = name
        self.hand = []
        self.information = {
            set_name: { card: 0 for card in cards }
            for set_name, cards in cards_by_set.items()
        }
        self.knownSets = { set_name: 0 for set_name in cards_by_set.keys() }

    def __repr__(self):
        return self.name

class Ask:
    def __init__(self, asker, asked, card, gotCard):
        self.asker = asker
        self.asked = asked
        self.card = card
        self.gotCard = gotCard
        self.set = card.set

    def __repr__(self):
        #part AI
        asker_name = self.asker.name if isinstance(self.asker, Player) else str(self.asker)
        asked_name = self.asked.name if isinstance(self.asked, Player) else str(self.asked)
        res = "got it" if self.gotCard else "didn't get it"
        return f"{asker_name.capitalize()} asked {asked_name.capitalize()} for {self.card} and {res}"
#Me
class LiteratureGame:
    def __init__(self, players):
        self.players = players
        self.playerWithTurn = players[0]
        self.asks = []
        self.logger = GameLogger()

    def record_move(self, ask_object):
        self.asks.append(ask_object)
        self.logger.log_move(str(ask_object))
        gotCard = ask_object.gotCard
        card = ask_object.card
        asker = ask_object.asker
        asked = ask_object.asked
        card_set = card.set

        card_str = str(card)
        if gotCard:
            asker.information[card_set][card_str] = 1
            asked.information[card_set][card_str] = -1
            self.playerWithTurn = asker
        else:
            asked.information[card_set][card_str] = -1
            asker.knownSets[card_set] = 1
            self.playerWithTurn = asked
#Me (print statements are AI)
def isIllegalAsk(ask):
    asker = ask.asker
    asked = ask.asked
    card_str = str(ask.card)
    card_set = ask.card.set

    # 0. Can't ask yourself
    if asker == asked:
        print(f"Illegal: {asker.name} asked themselves")
        return True

    # 1. Can't ask for a card you already have
    if asker.information[card_set].get(card_str) == 1:
        print(f"Illegal: {asker.name} already has {card_str}")
        return True

    # 2. Must have at least one card in the set to ask for another
    # We only block if we are CERTAIN they have none (all marked -1)
    set_info = asker.information[card_set]
    has_possible_card = False
    for status in set_info.values():
        if status != -1:
            has_possible_card = True
            break

    if not has_possible_card:
        print(f"Illegal: {asker.name} proven to have no cards in {card_set}")
        return True

    return False

# mostly AI
class Listener:
    def __init__(self, players, values, suits):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0
        self.player_objects = players
        self.players = [p.name if isinstance(p, Player) else p for p in players]
        self.values = values
        self.suits = suits
        self.game_keywords = f"Players: {', '.join(self.players)}. Cards: {', '.join(values)}. Suits: {', '.join(suits)}."

    def listen(self, current_asker):
        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                text = self.recognizer.recognize_openai(
                    audio,
                    model="gpt-4o-mini-transcribe",
                    prompt=f"Card game: literature. Keywords: {self.game_keywords}"
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

        s_match, s_score = process.extractOne(text, self.suits)
        if s_score >= confidence_threshold: found_suit = s_match

        v_match, v_score = process.extractOne(text, self.values)
        if v_score >= confidence_threshold: found_value = v_match

        p_match, p_score = process.extractOne(text, self.players)
        if p_score >= confidence_threshold:
            for p in self.player_objects:
                if p.name == p_match:
                    found_player = p
                    break

        if found_suit is not None and found_value is not None and found_player is not None:
            found_card = Card(found_value, found_suit)
            # Simple heuristic for 'got it'
            got_card = False
            for word in ['yes', 'got', 'here', 'have']:
                if word in text:
                    got_card = True
                    break
            return Ask(current_asker, found_player, found_card, got_card)
        return None

# --- Application Logic ---
#AI
def get_initial_data():
    player_names = ['max', 'alex', 'ben', 'jack', 'kevin', 'darren']
    suits_regular = ['hearts', 'diamonds', 'clubs', 'spades']
    low_values = ['two', 'three', 'four', 'five', 'six', 'seven']
    high_values = ['nine', 'ten', 'jack', 'queen', 'king', 'ace']

    cards_by_set = {}
    for suit in suits_regular:
        cards_by_set[f'Low {suit.capitalize()}'] = [f"{v.capitalize()} of {suit.capitalize()}" for v in low_values]
        cards_by_set[f'High {suit.capitalize()}'] = [f"{v.capitalize()} of {suit.capitalize()}" for v in high_values]

    ej_cards = [f"Eight of {s.capitalize()}" for s in suits_regular] + ["Red Joker", "Black Joker"]
    cards_by_set['Eights and Jokers'] = ej_cards

    all_values = low_values + high_values + ['eight', 'joker'] + [str(i) for i in range(2, 11)]
    all_suits = suits_regular + ['red', 'black']

    return player_names, cards_by_set, all_values, all_suits
# some AI
def background_listener(app):
    listener = Listener(app.players, app.values, app.suits)
    while app.isListening:
        if not app.useMic: continue

        result_ask = listener.listen(app.game.playerWithTurn)
        if result_ask:
            if not isIllegalAsk(result_ask):
                app.game.record_move(result_ask)
# AI
def run_test_move(app, asker_idx, asked_idx, val, suit, got):
    asker = app.players[asker_idx]
    asked = app.players[asked_idx]
    card = Card(val, suit)
    move = Ask(asker, asked, card, got)
    if not isIllegalAsk(move):
        app.game.record_move(move)
        print(f"Test Move: {move}")
# AI
def seed_card(player, val, suit):
    card = Card(val, suit)
    player.information[card.set][str(card)] = 1
# AI
def run_automated_test(app, test_key):
    all_tests = tests.get_test_cases()
    if test_key in all_tests:
        print(f"--- Running Test: {test_key} ---")
        for action in all_tests[test_key]:
            if action[0] == 'seed':
                seed_card(app.players[action[1]], action[2], action[3])
            elif action[0] == 'move':
                run_test_move(app, action[1], action[2], action[3], action[4], action[5])
    else:
        print(f"Test '{test_key}' not found. Available: {list(all_tests.keys())}")

def onAppStart(app):
    names, cards_by_set, app.values, app.suits = get_initial_data()
    app.players = [Player(name, cards_by_set) for name in names]
    app.game = LiteratureGame(app.players)

    app.isListening = True
    app.useMic = False

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if not arg.startswith('-'):
                run_automated_test(app, arg)
                break

    if not hasattr(app, 'thread') or not app.thread.is_alive():
        app.thread = threading.Thread(target=background_listener, args=(app,), daemon=True)
        app.thread.start()

# AI
def onKeyPress(app, key):
    if key == 'm':
        app.useMic = not app.useMic
        print(f"Mic: {'On' if app.useMic else 'Off'}")
    elif key == 'r':
        onAppStart(app)
        print("Game reset.")

# DO NOT DELETE
def onStep(app):
    pass

# AI (temporary)
def redrawAll(app):
    drawLabel("Literature Observer", 200, 30, size=22, bold=True)

    mic_status = "Microphone: ON" if app.useMic else "Microphone: OFF (Press 'M')"
    fill = 'green' if app.useMic else 'red'
    drawLabel(mic_status, 200, 60, size=16, fill=fill)

    turn_name = app.game.playerWithTurn.name.capitalize()
    drawLabel(f"Current Turn: {turn_name}", 200, 100, size=18, fill='navy')

    drawLabel("Last Move:", 200, 150, size=16, bold=True)
    if app.game.asks:
        drawLabel(str(app.game.asks[-1]), 200, 180, size=14)
    else:
        drawLabel("No moves recorded yet", 200, 180, size=14, italic=True)
    drawLabel("Controls:", 200, 280, size=14, bold=True)
    drawLabel("'M' - Toggle Mic | 'R' - Reset Game", 200, 310, size=12)
    drawLabel(f"Log: {app.game.logger.filename}", 200, 335, size=10, fill='grey')

def main():
    runApp(width=400, height=400)

if __name__ == '__main__':
    main()
