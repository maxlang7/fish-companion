import os
import random
from datetime import datetime
from models import Card, Player, Team, Ask
from constants import valueMap, suitMap

# Logger written by AI
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
    # names are AI generated
    botNames = [
        "Robo-Jack", "Byte-Ben", "Cyber-Alex", "Data-Kevin", "Circuit-Dan",
        "Silicon-Sam", "Logic-Leo", "Pixel-Pete"
    ]

    # Part AI (built feature son top of what I made)
    def __init__(self, playerNames, botCards=None, doLog=True, shuffle=False, oneSet=False):
        availableBotNames = list(self.botNames)
        random.shuffle(availableBotNames)

        self.players = []
        for i in range(len(playerNames)):
            name      = playerNames[i]
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

        if oneSet:
            self.dealTwoSets()
        elif shuffle:
            self.dealShuffled()
        elif botCards:
            self.dealBotCards(botCards)

    # Me
    def buildPublicInfo(self):
        info = {}
        for card in Card.getAllCards():
            info.setdefault(card.set, {})[card] = set(self.players)
        return info

    # Next 8 functions AI
    def printHands(self):
        print("\n--- Hands ---")
        for p in self.players:
            def handSortKey(c):
                return (c.set, c.value)
            cards = ', '.join(str(c) for c in sorted(p.hand, key=handSortKey))
            print(f"  {p.name}: {cards or '(empty)'}")
        print()

    def dealTwoSets(self):
        testSets = {'Eights and Jokers', 'Low Hearts'}
        cards = [c for c in Card.getAllCards() if c.set in testSets]
        random.shuffle(cards)
        for i in range(len(cards)):
            self.players[i % 6].hand.add(cards[i])
        self.printHands()

    def dealShuffled(self):
        allCards = Card.getAllCards()
        random.shuffle(allCards)
        for i in range(len(allCards)):
            self.players[i % 6].hand.add(allCards[i])

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

    @staticmethod
    def parseCardString(cStr):
        if cStr.startswith('10'):
            return 'ten', suitMap.get(cStr[2]) if len(cStr) > 2 else None
        if len(cStr) >= 2:
            return valueMap.get(cStr[0]), suitMap.get(cStr[1])
        return None, None

    def advanceTurn(self, currentPlayer=None):
        if currentPlayer is None:
            currentPlayer = self.playerWithTurn
        teammates = [p for p in self.players
                     if p.team == currentPlayer.team and p != currentPlayer and p.hand]
        if teammates:
            self.playerWithTurn = random.choice(teammates)
            return
        opponents = [p for p in self.players
                     if p.team != currentPlayer.team and p.hand]
        if opponents:
            self.playerWithTurn = random.choice(opponents)
            return
        if self.winner is None:
            scores = [t.setsTaken for t in self.teams]
            def teamKey(t):
                return t.setsTaken
            self.winner = "tied" if scores[0] == scores[1] else max(self.teams, key=teamKey)

    def advanceTurnIfNeeded(self):
        if self.playerWithTurn.hand:
            return
        self.advanceTurn()

    def resolveSet(self, setName, teamIdx, source="auto"):
        if setName in self.completedSets:
            return
        self.completedSets.add(setName)
        self.teams[teamIdx].setsTaken += 1
        print(f"[{source.upper()}] Team {teamIdx} took {setName}")
        for card in self.publicInfo[setName]:
            self.publicInfo[setName][card] = set()
            for p in self.players:
                p.hand.discard(card)
        if self.teams[teamIdx].setsTaken > 4:
            self.winner = self.teams[teamIdx]
    # Me again
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

        for teamIdx in range(len(self.teams)):
            if not any(p in playersInSet for p in self.teams[teamIdx].players):
                self.resolveSet(s, 1 - teamIdx, source="auto")
                break
    # Me
    def recordMove(self, ask):
        if ask is None:
            return
        self.asks.append(ask)
        self.logger.logMove(str(ask))
        self.applyMove(ask)
