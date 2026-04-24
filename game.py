import os
import random
from datetime import datetime
from models import Card, Player, Team, Ask
from constants import valueMap, suitMap

class GameLogger:
    logDir = "games"

    def __init__(self, enabled=True):
        self.enabled  = enabled
        self.filename = None
        if self.enabled:
            os.makedirs(self.logDir, exist_ok=True)
            self.filename = self.nextFilename()

    def nextFilename(self):
        dateStr = datetime.now().strftime("%Y-%m-%d")
        n = 1
        while True:
            path = os.path.join(self.logDir, f"{dateStr}_game_{n}.txt")
            if not os.path.exists(path):
                return path
            n += 1

    def logMove(self, moveStr):
        if self.enabled and self.filename:
            with open(self.filename, "a") as f:
                ts = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{ts}] {moveStr}\n")


class LiteratureGame:
    botNames = [
        "Robo-Jack", "Byte-Ben", "Cyber-Alex", "Data-Kevin", "Circuit-Dan",
        "Silicon-Sam", "Logic-Leo", "Pixel-Pete"
    ]

    def __init__(self, playerNames, botCards=None, doLog=True, shuffle=False):
        availableBotNames = list(self.botNames)
        random.shuffle(availableBotNames)

        self.players = []
        for i, name in enumerate(playerNames):
            isBot     = (name.lower() == 'bot')
            finalName = availableBotNames.pop() if isBot else name
            self.players.append(Player(finalName, i % 2, isBot=isBot))

        self.teams = [
            Team([self.players[0], self.players[2], self.players[4]]),
            Team([self.players[1], self.players[3], self.players[5]])
        ]
        self.playerWithTurn = self.players[0]
        self.completedSets  = set()
        self.asks           = []
        self.winner         = None
        self.logger         = GameLogger(enabled=doLog)
        self.publicInfo     = self.buildPublicInfo()

        if shuffle:
            self.dealShuffled()
        elif botCards:
            self.dealBotCards(botCards)

    def buildPublicInfo(self):
        info = {}
        for card in Card.getAllCards():
            info.setdefault(card.set, {})[card] = set(self.players)
        return info

    def dealShuffled(self):
        allCards = Card.getAllCards()
        random.shuffle(allCards)
        i = 0
        for card in allCards:
            player = self.players[i % 6]
            player.hand.add(card)
            self.publicInfo[card.set][card] = {player}
            i += 1

    def dealBotCards(self, botCards):
        for pIdx, cards in botCards.items():
            if pIdx >= len(self.players):
                continue
            player = self.players[pIdx]
            for cStr in cards:
                cStr = cStr.strip().lower()
                if not cStr:
                    continue
                val, suit = self.parseCardString(cStr)
                if val and suit:
                    card = Card(val, suit)
                    player.hand.add(card)
                    self.publicInfo[card.set][card] = {player}

    @staticmethod
    def parseCardString(cStr):
        if cStr.startswith('10'):
            return 'ten', suitMap.get(cStr[2]) if len(cStr) > 2 else None
        if len(cStr) >= 2:
            return valueMap.get(cStr[0]), suitMap.get(cStr[1])
        return None, None

    def resolveSet(self, setName, teamIdx, source="auto"):
        if setName in self.completedSets:
            return
        self.completedSets.add(setName)
        self.teams[teamIdx].setsTaken += 1
        print(f"[{source.upper()}] Team {teamIdx} took {setName}")
        for card in self.publicInfo[setName]:
            self.publicInfo[setName][card] = set()
        if self.teams[teamIdx].setsTaken > 4:
            self.winner = self.teams[teamIdx]

    def applyMove(self, ask):
        card  = ask.card
        s     = card.set

        self.publicInfo[s][card] -= {ask.asker}

        if ask.gotCard:
            self.publicInfo[s][card] = {ask.asker}
            self.playerWithTurn = ask.asker
            ask.asked.hand.discard(card)
            ask.asker.hand.add(card)
        else:
            self.publicInfo[s][card] -= {ask.asked}
            self.playerWithTurn = ask.asked

        playersInSet = set()
        for possible in self.publicInfo[s].values():
            playersInSet |= possible

        for i, team in enumerate(self.teams):
            if not any(p in playersInSet for p in team.players):
                self.resolveSet(s, 1 - i, source="auto")
                break

    def recordMove(self, ask):
        if ask is None:
            return
        self.asks.append(ask)
        self.logger.logMove(str(ask))
        self.applyMove(ask)
