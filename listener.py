import time
import speech_recognition as sr
from thefuzz import process
from models import Card, Ask
from logic import Analyzer

class Listener:
    def __init__(self, gameState):
        self.recognizer  = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0
        self.players     = gameState.players
        self.playerNames = [p.name for p in gameState.players]
        self.cardValues  = [
            "joker", "ace", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "jack", "queen", "king"
        ]
        self.cardSuits = ["hearts", "diamonds", "clubs", "spades", "red", "black"]

    def listen(self, currentAsker):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                text  = self.recognizer.recognize_openai(
                    audio,
                    model="gpt-4o-mini-transcribe",
                    prompt=f"Card game: fish. Keywords: "
                           f"{self.cardValues + self.cardSuits + self.playerNames}"
                ).lower()
                print(f"Heard: '{text}'")
                return self.parseText(text, currentAsker)
            except Exception:
                return None

    def parseText(self, text, currentAsker):
        thresh = 70
        sMatch, sScore = process.extractOne(text, self.cardSuits)
        vMatch, vScore = process.extractOne(text, self.cardValues)
        pMatch, pScore = process.extractOne(text, self.playerNames)

        foundSuit   = sMatch if sScore >= thresh else None
        foundValue  = vMatch if vScore >= thresh else None
        foundPlayer = next((p for p in self.players if p.name == pMatch), None) if pScore >= thresh else None

        if foundSuit and foundValue and foundPlayer:
            gotCard = any(w in text for w in ('yes', 'got', 'here', 'have'))
            return Ask(currentAsker, foundPlayer, Card(foundValue, foundSuit), gotCard)
        return None

    def backgroundListen(self, app):
        while app.isListening and app.gameState.winner is None:
            if not app.useMic:
                time.sleep(0.1)
                continue
            result = self.listen(app.gameState.playerWithTurn)
            if result:
                reason = Analyzer.illegalAskReason(app.gameState, result)
                if reason:
                    app.illegalAskMessage = reason
                else:
                    app.illegalAskMessage = None
                    app.gameState.recordMove(result)
                    print(f"  ✓  Recorded: {result}")
