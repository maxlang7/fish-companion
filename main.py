from cmu_graphics import *
import threading
import speech_recognition as sr
from thefuzz import process # CHANGE: Added fuzzy matching library

"""
Required Libraries:
- cmu_graphics
- threading
- speech_recognition
- openai
- thefuzz

Setup an OpenAI key with export OPENAI_API_KEY="ssh-000000"
"""

class Ask:
    def __init__(self, asker, asked, value, suit, gotCard):
        self.asker=asker
        self.asked=asked
        # AI
        digit_to_word = {
            '1': 'ace', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
            '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten'
        }
        self.value = digit_to_word.get(value, value)
        # Me
        self.suit=suit
        self.gotCard=gotCard
        if self.value == 'joker' or self.value=='eight':
            self.set = 'Eights and Jokers'
        if self.value in ['two', 'three', 'four', 'five', 'six', 'seven']:
            self.set = f'Low {self.suit.capitalize()}'
        if self.value in ['nine', 'ten', 'jack', 'queen', 'king', 'ace']:
            self.set = f'High {self.suit.capitalize()}'

    def __repr__(self):
        if self.value=='joker':
            # Red Joker
            card=f"{self.suit.capitalize()} Joker"
        else:
            # three of clubs
            card=f"{self.value.capitalize()} of {self.suit.capitalize()}"
        return f"{self.asker.capitalize()} asked {self.asked.capitalize()} for the {card}"

class Player:
    def __init__(self, name):
        self.name = name
        self.numCards=0
        self.cards = []
        self.antiCards=[]

    def __repr__(self):
        return f"{self.name} (Score: {self.score})"

def isLegalAsk(app, ask):
    pass

def start_listening(app):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
    recognizer.pause_threshold = 1.0 # Default is 0.8; 1.0 or 1.5 allows for longer pauses
    # CHANGE: Keywords now include digits and words to help the AI model
    game_keywords = f"Players: {', '.join(app.players)}. Cards: {', '.join(app.values)}. Suits: {', '.join(app.suits)}."

    while app.isListening:
        try:
            with mic as source:
                # CHANGE: phrase_time_limit set to 5
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)

            # CHANGE: Prompting implemented
            text = recognizer.recognize_openai(
                audio,
                model="gpt-4o-mini-transcribe",
                prompt=f"Card game: fish or hearts. Commands like 'Max, do you have a 4 of clubs?'. Keywords: {game_keywords}"
            ).lower()

            print(f"Heard: {text}")

            found_suit = None
            found_value = None
            found_player = None

            # Added fuzzy matching logic with AI
            confidence_threshold = 80

            # Match Suit
            s_match, s_score = process.extractOne(text, app.suits)
            if s_score > confidence_threshold: found_suit = s_match

            # Match Value
            v_match, v_score = process.extractOne(text, app.values)
            if v_score > confidence_threshold: found_value = v_match

            # Match Player
            p_match, p_score = process.extractOne(text, app.players)
            if p_score > confidence_threshold: found_player = p_match

            if found_suit is None:
                print("Couldn't parse suit")
            elif found_value is None:
                print("Couldn't parse card value")
            elif found_player is None:
                print("Couldn't parse asking player name")
            else:
                gotCard = 'yes' in text
                app.asks.append(Ask(app.playerWithTurn, found_player, found_value, found_suit, gotCard))
                app.playerWithTurn = found_player

        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            print(f"Error: {e}")

def onAppStart(app):
    app.asks=[]
    app.stepsPerSecond = 10
    app.isListening=True
    app.suits = ['hearts', 'diamonds', 'clubs', 'spades', 'red', 'black']

    # CHANGE: app.values now includes both words and digits for matching
    card_names = ['ace', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'jack', 'queen', 'king', 'joker']
    digits = ['2', '3', '4', '5', '6', '7', '8', '9', '10']
    app.values = card_names + digits

    app.players=['max', 'alex', 'ben', 'jack', 'kevin', 'darren']
    app.playerWithTurn=app.players[0]
    app.thread = threading.Thread(target=start_listening, args=(app,), daemon=True)
    app.thread.start()

def redrawAll(app):
    drawLabel("Asks:", 200, 50, size=20, bold=True)
    if len(app.asks)>0:
        drawLabel(app.asks[-1], 200, 200, size=16)

def onStep(app):
    pass

def main():
    runApp(width=400, height=400)

if __name__ == '__main__':
    main()
