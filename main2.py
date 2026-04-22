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

"""
Required Libraries:
- cmu_graphics
- threading
- speech_recognition
- openai
- thefuzz
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
        self.team = team
    def __repr__(self):
        return self.name

class Team:
    def __init__(self, players):
        self.players = players
        self.setsTaken = 0

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
        self.publicInfo = dict()
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

        self.logger = GameLogger(enabled=do_log)
        self.asks = []
        self.winner = None

    def _apply_move(self, ask_object):
        """
        Apply a move to the game state (updates publicInfo, turn, sets taken, winner).
        Does NOT log or append to self.asks — used by both record_move() and simulation.
        """
        gotCard  = ask_object.gotCard
        card     = ask_object.card
        asker    = ask_object.asker
        asked    = ask_object.asked
        card_set = card.set

        # Asker can't have the card they asked for
        self.publicInfo[card_set][card] -= {asker}

        if gotCard:
            self.publicInfo[card_set][card] = {asker}
            self.playerWithTurn = asker
        else:
            self.publicInfo[card_set][card] -= {asked}
            self.playerWithTurn = asked

        playersInSet = set()
        for possible_players in self.publicInfo[card_set].values():
            playersInSet |= possible_players

        for i in range(len(self.teams)):
            team       = self.teams[i]
            other_team = self.teams[1 - i]
            numInSet   = len(team.players)
            for player in team.players:
                if player not in playersInSet:
                    numInSet -= 1
            if numInSet == 0:
                other_team.setsTaken += 1
                print(f"Team {1-i} took the set: {card_set}!")
                for c in self.publicInfo[card_set]:
                    self.publicInfo[card_set][c] = set()
                if other_team.setsTaken > 4:
                    self.winner = other_team
                break

    def record_move(self, ask_object):
        if ask_object is None:
            return
        self.asks.append(ask_object)
        self.logger.log_move(str(ask_object))
        self._apply_move(ask_object)

class Analyzer:
    @staticmethod
    def isIllegalAsk(gameState, ask, hand=[]):
        info     = gameState.publicInfo
        asker    = ask.asker
        asked    = ask.asked
        card     = ask.card
        card_set = ask.card.set

        if asker == asked:
            return f"You can't ask yourself"

        if info[card_set][card] == {asker} or card in hand:
            return f"You already have {card}"

        playersInSet = set()
        for possible_players in info[card_set].values():
            playersInSet |= possible_players

        if asker not in playersInSet:
            return f"You have no cards in {card_set}"

        return None

    @staticmethod
    def getAllLegalAsks(gameState, player, hand):
        potentialCards   = set()
        potentialPlayers = [p for p in gameState.players if p.team != player.team and p.handSize > 0]
        possibleSets     = set([card.set for card in hand])
        for card in Card.getAllCards():
            if card.set in possibleSets and card not in hand:
                potentialCards.add(card)
        res = []
        for card in potentialCards:
            for toAsk in potentialPlayers:
                res.append(Ask(player, toAsk, card))
        return res

    @staticmethod
    def evaluatePosition(gameState, team_idx):
        """
        Score the position for team_idx (0 or 1). Higher = better for that team.

        Three signals, in order of importance:
          1. Sets already won  (+/-100 each)
          2. Declare-ready sets — all active cards in a set are known to be on one team (+/-30)
          3. Per-card certainty — cards with a smaller 'possible' set are more
             valuable to the team that controls them (+/-5 if certain, smaller
             fractional credit if uncertain)
        """
        team0 = gameState.teams[0]
        team1 = gameState.teams[1]

        if team0.setsTaken > 4:
            raw = math.inf
        elif team1.setsTaken > 4:
            raw = -math.inf
        else:
            raw = (team0.setsTaken - team1.setsTaken) * 100.0

            team0_players = set(team0.players)
            team1_players = set(team1.players)

            for set_name, card_info in gameState.publicInfo.items():
                t0_certain = 0
                t1_certain = 0
                active_count = 0

                for card, possible_players in card_info.items():
                    if not possible_players:
                        continue   # card already out of play
                    active_count += 1

                    if len(possible_players) == 1:
                        # We know exactly who has this card
                        holder = next(iter(possible_players))
                        if holder in team0_players:
                            t0_certain += 1
                            raw += 5
                        else:
                            t1_certain += 1
                            raw -= 5
                    else:
                        # Partial credit proportional to how many candidates
                        # each team has for this card
                        t0_cands = len(possible_players & team0_players)
                        t1_cands = len(possible_players & team1_players)
                        total    = t0_cands + t1_cands
                        if total > 0:
                            raw += (t0_cands - t1_cands) / total * 2

                # Big bonus if one team can declare the whole set right now
                if active_count > 0:
                    if t0_certain == active_count:
                        raw += 30
                    elif t1_certain == active_count:
                        raw -= 30

        return raw if team_idx == 0 else -raw

    @staticmethod
    def _label_move(got_card, delta, possible_size, asked_in_possible):
        """
        Translate a move's outcome and context into a chess-style label + display color.

        got_card        — did the asker receive the card?
        delta           — change in eval for the asker's team after the move
        possible_size   — how many players could have held the card before the ask
        asked_in_possible — was the asked player even a candidate per public info?

        Labels (worst → best): Blunder, Mistake, Inaccuracy, Okay, Good, Excellent, Brilliant
        """
        if not got_card:
            # Asking someone public info already ruled out is the clearest blunder
            if not asked_in_possible:
                return "Blunder",     'darkRed'
            # Failed ask where only 1-2 candidates existed — should have been sure
            if possible_size <= 2:
                return "Blunder",     'darkRed'
            if delta < -8:
                return "Mistake",     'crimson'
            if delta < -3:
                return "Inaccuracy",  'orangeRed'
            return "Risky",           'goldenrod'
        else:
            if delta >= 30:
                return "Brilliant!",  'darkGreen'
            if delta >= 12:
                return "Excellent",   'green'
            if delta >= 4:
                return "Good",        'limeGreen'
            return "Okay",            'olive'

    @staticmethod
    def analyzeReplay(moves, initial_game):
        """
        Pre-compute a move-quality label for every move in a replay.

        We replay the full game on a private simulation (no logging, same player
        names) and compute evaluatePosition() before and after each move.
        Player objects in Ask instances reference the *original* game, so we
        translate every ask to the simulation's own player objects by name.

        Returns a list of (label_str, color_str), one entry per move.
        """
        # Fresh simulation game — same names and teams, no file logging
        sim = LiteratureGame(
            [p.name for p in initial_game.teams[0].players],
            [p.name for p in initial_game.teams[1].players],
            do_log=False
        )
        name_to_player = {p.name: p for p in sim.players}

        def translate(ask):
            """Return a copy of ask whose player references belong to sim."""
            return Ask(
                name_to_player[ask.asker.name],
                name_to_player[ask.asked.name],
                ask.card,
                ask.gotCard
            )

        labels = []

        for ask in moves:
            team_idx = ask.asker.team
            sim_ask  = translate(ask)

            # Snapshot the public info needed for context BEFORE the move
            possible_size      = len(sim.publicInfo[ask.card.set][ask.card])
            asked_in_possible  = sim_ask.asked in sim.publicInfo[ask.card.set][ask.card]

            eval_before = Analyzer.evaluatePosition(sim, team_idx)

            # Simulate the move on a throw-away deepcopy to get eval_after
            # without advancing the main sim yet
            snap = copy.deepcopy(sim)
            snap_name_to_player = {p.name: p for p in snap.players}
            snap_ask = Ask(
                snap_name_to_player[ask.asker.name],
                snap_name_to_player[ask.asked.name],
                ask.card,
                ask.gotCard
            )
            snap._apply_move(snap_ask)
            eval_after = Analyzer.evaluatePosition(snap, team_idx)

            delta = eval_after - eval_before
            label, color = Analyzer._label_move(
                ask.gotCard, delta, possible_size, asked_in_possible
            )
            labels.append((label, color))

            # Now advance the real sim
            sim._apply_move(sim_ask)

        return labels

# mostly AI
class Listener:
    def __init__(self, gameState):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0
        self.player_objects = gameState.players
        self.player_names   = [player.name for player in gameState.players]
        self.card_values    = ["joker","ace","2","3","4","5","6","7","8","9","10","two","three","four","five","six","seven","eight","nine","ten","jack","queen","king"]
        self.card_suits     = ["hearts","diamonds","clubs","spades", "red", "black"]

    def listen(self, current_asker):
        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                text  = self.recognizer.recognize_openai(
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
        found_suit   = None
        found_value  = None
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
            got_card = False
            for word in ['yes', 'got', 'here', 'have']:
                if word in text:
                    got_card = True
                    break
            return Ask(current_asker, found_player, found_card, got_card)
        return None

    def background_listener(self, app):
       while app.isListening and app.gameState.winner == None:
           if not app.useMic:
               time.sleep(0.1)
               continue
           result_ask = self.listen(app.gameState.playerWithTurn)
           if result_ask:                                          # <-- everything must be inside here
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
                if ' asked ' not in line or ' for ' not in line:
                    continue
                try:
                    parts      = line.split(']', 1)[1].strip().split(' asked ')
                    asker_name = parts[0].lower()

                    rest       = parts[1].split(' for ')
                    asked_name = rest[0].lower()

                    card_and_res = rest[1].split(' and ')
                    card_str     = card_and_res[0]
                    res_str      = card_and_res[1]
                    got          = "got it" in res_str

                    if " Joker" in card_str:
                        suit = card_str.replace(" Joker", "").lower()
                        card = Card("joker", suit)
                    else:
                        card_parts = card_str.split(' of ')
                        value = card_parts[0].lower()
                        suit  = card_parts[1].lower()
                        card  = Card(value, suit)

                    asker = name_to_player.get(asker_name)
                    asked = name_to_player.get(asked_name)

                    if asker and asked:
                        moves.append(Ask(asker, asked, card, got))
                except Exception as e:
                    print(f"Error parsing line: {line}\n{e}")
        return moves

class TerminalInputHandler:
    """
    Reads typed corrections from stdin in a background thread.
    Format:  asker  target  value  suit  [got]
    Example: max jack two hearts got
             kevin alex nine spades
    """
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
                if not line:          # EOF
                    break
                line = line.strip().lower()
            except Exception as e:
                print(f"Terminal read error: {e}")
                break
            if line:
                self._handle(app, line)


    def _handle(self, app, line):
        name_to_player = {p.name.lower(): p for p in app.gameState.players}
        parts = line.split()

        # Need at least: asker target value suit
        if len(parts) < 4:
            print("  ✗  Too few words. Format: <asker> <target> <value> <suit> [got]")
            return

        asker_name  = parts[0]
        target_name = parts[1]
        value       = parts[2]
        suit        = parts[3]
        got         = len(parts) >= 5 and parts[4] == 'got'

        asker  = name_to_player.get(asker_name)
        target = name_to_player.get(target_name)

        if not asker:
            print(f"  ✗  Unknown player '{asker_name}'. Players: {list(name_to_player.keys())}")
            return
        if not target:
            print(f"  ✗  Unknown player '{target_name}'. Players: {list(name_to_player.keys())}")
            return

        try:
            card = Card(value, suit)
        except Exception:
            print(f"  ✗  Could not parse card '{value} {suit}'")
            return

        ask    = Ask(asker, target, card, got)
        reason = Analyzer.isIllegalAsk(app.gameState, ask)
        if reason:
            print(f"  ✗  Illegal ask: {reason}")
            app.illegalAskMessage = reason
        else:
            app.illegalAskMessage = None
            app.gameState.record_move(ask)
            print(f"  ✓  {ask}")

# --- Application Logic ---
def onAppStart(app):
    all_tests  = tests.get_test_cases()
    is_testing = 'test' in sys.argv or any(arg in all_tests for arg in sys.argv[1:])
    app.illegalAskMessage = None
    app.gameState    = LiteratureGame(['max', 'alex', 'ben'], ['jack', 'kevin', 'darren'], do_log=not is_testing)
    app.isListening  = True
    app.useMic       = False
    app.replayMoves  = []
    app.replayLabels = []   # (label_str, color_str) for each replay move
    app.replayIndex  = 0
    app.isReplay     = False
    app.stepDelay    = 60
    app.stepCount    = 0

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
                app.isReplay     = True
                app.isListening  = False
                # Pre-compute analysis labels for every move in the replay
                app.replayLabels = Analyzer.analyzeReplay(app.replayMoves, app.gameState)
                print(f"Loaded {len(app.replayMoves)} moves for replay.")
            else:
                print(f"Failed to parse or empty log: {arg}")

    if not app.isReplay and (not hasattr(app, 'thread') or not app.thread.is_alive()):
        app.listener = Listener(app.gameState)
        app.thread   = threading.Thread(target=app.listener.background_listener, args=(app,), daemon=True)
        app.thread.start()
        app.terminalInput = TerminalInputHandler()
        app.terminalInput.start(app)
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
        app.stepCount = app.stepDelay

# DO NOT DELETE
def onStep(app):
    if app.isReplay and app.replayIndex < len(app.replayMoves):
        app.stepCount += 1
        if app.stepCount >= app.stepDelay:
            app.stepCount    = 0
            move             = app.replayMoves[app.replayIndex]
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
        status_text  = f"REPLAY MODE ({app.replayIndex}/{len(app.replayMoves)})"
        status_color = 'orange'
        progress     = (app.replayIndex / len(app.replayMoves)) * 400 if app.replayMoves else 0
        if progress > 0:
            drawRect(0, 50, progress, 5, fill='orange')
    else:
        status_text  = "LIVE MODE"
        status_color = 'green' if app.useMic else 'red'
        mic_text     = "Mic: ON" if app.useMic else "Mic: OFF ('M')"
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

    if not app.isReplay and app.illegalAskMessage:
        drawRect(20, 245, 360, 40, fill='crimson', border=None)
        drawLabel("Illegal ask — speak again", 200, 257, size=13, bold=True, fill='white')
        drawLabel(app.illegalAskMessage, 200, 275, size=11, fill='white')

    # Last Move
    drawLabel("Last Move:", 40, 270, size=14, bold=True, align='left')
    if app.gameState.asks:
        last_move = app.gameState.asks[-1] if app.gameState.asks else None
        if last_move:
            move_str  = str(last_move)
            if len(move_str) > 45:
                move_str = move_str[:42] + "..."
            drawLabel(move_str, 200, 295, size=14)
    
            res_color = 'darkGreen' if last_move.gotCard else 'darkRed'
            res_text  = "SUCCESS"   if last_move.gotCard else "FAILED"
            drawLabel(res_text, 200, 315, size=12, bold=True, fill=res_color)

        # Analysis badge — only shown during replay once at least one move has played
        if app.isReplay and app.replayLabels and app.replayIndex > 0:
            label, badge_color = app.replayLabels[app.replayIndex - 1]
            badge_w = len(label) * 8 + 16   # scale badge width to label length
            badge_x = 200 - badge_w // 2
            drawRect(badge_x, 328, badge_w, 20, fill=badge_color, border=None)
            drawLabel(label, 200, 338, size=11, bold=True, fill='white')
    else:
        drawLabel("Waiting for first move...", 200, 295, size=14, italic=True, fill='grey')

    # Winner
    if app.gameState.winner:
        team_num = 1 if app.gameState.winner == app.gameState.teams[0] else 2
        drawRect(0, 0, 400, 400, fill='black', opacity=60)
        drawRect(50, 150, 300, 100, fill='gold', border='white')
        drawLabel(f"TEAM {team_num} WINS!", 200, 200, size=30, bold=True)

    # Footer
    drawLabel("'R' Reset | 'M' Mic | Terminal: asker target value suit [got]",
              200, 380, size=9, fill='grey')
def main():
    if 'test' in sys.argv:
        class DummyApp:
            def __init__(self):
                self.gameState  = None
                self.isListening = False
                self.useMic     = False
        onAppStart(DummyApp())
    else:
        runApp(width=400, height=400)

if __name__ == '__main__':
    main()
