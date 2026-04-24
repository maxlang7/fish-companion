from models import Card, Ask
from constants import valueMap, suitMap
from logic import Analyzer


# Whole file AI
setMap = {
    'lh': 'Low Hearts',    'ld': 'Low Diamonds',
    'lc': 'Low Clubs',     'ls': 'Low Spades',
    'hh': 'High Hearts',   'hd': 'High Diamonds',
    'hc': 'High Clubs',    'hs': 'High Spades',
    'ej': 'Eights and Jokers'
}

class ShortcodeParser:
    @staticmethod
    def parse(code, gameState):
        if len(code) < 3:
            return None, "Shortcode too short"
        if code[0].isdigit() and len(code) == 3:
            return ShortcodeParser.parseBotAsk(code, gameState)
        if len(code) != 4:
            return None, "Need 4 chars (3 for bots)"
        return ShortcodeParser.parseHumanAsk(code, gameState)

    @staticmethod
    def parseBotAsk(code, gameState):
        targetIdx = int(code[0]) - 1
        if not (0 <= targetIdx < len(gameState.players)):
            return None, f"Player must be 1–{len(gameState.players)}"
        target = gameState.players[targetIdx]
        if not target.isBot:
            return None, "3-char codes are only for bot targets"
        val  = valueMap.get(code[1].lower())
        suit = suitMap.get(code[2].lower())
        if not val or not suit:
            return None, "Invalid card"
        card    = Card(val, suit)
        gotCard = card in target.hand
        return Ask(gameState.playerWithTurn, target, card, gotCard), None

    @staticmethod
    def parseHumanAsk(code, gameState):
        try:
            targetIdx = int(code[0]) - 1
            if not (0 <= targetIdx < len(gameState.players)):
                raise ValueError
            target = gameState.players[targetIdx]
        except (ValueError, IndexError):
            return None, f"Player must be 1–{len(gameState.players)}"
        val  = valueMap.get(code[1].lower())
        suit = suitMap.get(code[2].lower())
        if not val:  return None, f"Unknown value '{code[1].upper()}'"
        if not suit: return None, f"Unknown suit '{code[2].upper()}'"
        if code[3].lower() not in ('y', 'n'):
            return None, "4th char must be Y or N"
        card = Card(val, suit)
        ask  = Ask(gameState.playerWithTurn, target, card, code[3].lower() == 'y')
        return ask, None

    @staticmethod
    def submit(app):
        parsed, error = ShortcodeParser.parse(app.inputBuffer, app.gameState)
        app.inputBuffer = ''
        if error:
            app.illegalAskMessage = error
            return
        reason = Analyzer.illegalAskReason(app.gameState, parsed)
        if reason:
            app.illegalAskMessage = reason
        else:
            app.illegalAskMessage = None
            app.gameState.recordMove(parsed)
            print(f"  ✓  {parsed}")


class DeclareManager:
    @staticmethod
    def start(app, declarer=None):
        if declarer is None:
            declarer = app.gameState.playerWithTurn
        if declarer.isBot:
            return
        availableSets = {c.set for c in declarer.hand} - app.gameState.completedSets
        if not availableSets:
            app.illegalAskMessage = "No sets to declare"
            return
        app.declarer         = declarer
        app.declareMode      = True
        app.declarePhase     = 'select'
        app.declareSet       = None
        app.declareRemaining = []
        app.inputBuffer      = ''
        app.illegalAskMessage = None

    @staticmethod
    def cancel(app):
        app.declarer         = None
        app.declareMode      = False
        app.declarePhase     = None
        app.declareSet       = None
        app.declareRemaining = []
        app.inputBuffer      = ''

    @staticmethod
    def submitSetCode(app):
        code = app.inputBuffer.lower()
        app.inputBuffer = ''
        setName = setMap.get(code)
        if not setName:
            app.illegalAskMessage = f"Unknown set code '{code.upper()}'"
            return
        if setName in app.gameState.completedSets:
            app.illegalAskMessage = "Set already completed"
            return
        declarer = app.declarer
        if not any(c.set == setName for c in declarer.hand):
            app.illegalAskMessage = "You have no cards in that set"
            return
        app.declareSet    = setName
        app.declarePhase  = 'assign'
        app.illegalAskMessage = None
        # auto-skip cards the declarer already holds
        app.declareRemaining = [c for c in app.gameState.publicInfo[setName]
                                if c not in declarer.hand]
        if not app.declareRemaining:
            app.declareMessage      = (f"{setName} declared! Team scores!", True)
            app.declareMessageTimer = 180
            app.gameState.playerWithTurn = declarer
            DeclareManager.resolveAndClear(app, declarer.team)
            DeclareManager.passToWaiting(app, declarer)
            DeclareManager.cancel(app)

    @staticmethod
    def submitAssignment(app):
        code = app.inputBuffer.lower()
        app.inputBuffer = ''
        try:
            playerIdx = int(code[0]) - 1
            target = app.gameState.players[playerIdx]
        except (ValueError, IndexError):
            app.illegalAskMessage = f"Player must be 1–{len(app.gameState.players)}"
            return
        declarer = app.declarer
        if target.team != declarer.team:
            app.illegalAskMessage = "Can only assign to teammates"
            return
        val  = valueMap.get(code[1])
        suit = suitMap.get(code[2])
        if not val or not suit:
            app.illegalAskMessage = "Invalid card code"
            return
        card = Card(val, suit)
        if card.set != app.declareSet:
            app.illegalAskMessage = f"Card not in {app.declareSet}"
            return
        if card not in app.declareRemaining:
            app.illegalAskMessage = "Card already assigned"
            return
        if card not in target.hand:
            app.illegalAskMessage   = "MISDECLARE! Opponents get the set!"
            app.declareMessage      = (f"MISDECLARE! {app.declareSet} goes to opponents!", False)
            app.declareMessageTimer = 180
            opponentTeam = 1 - declarer.team
            DeclareManager.resolveAndClear(app, opponentTeam)
            opponents = [p for p in app.gameState.players if p.team == opponentTeam and p.hand]
            if opponents:
                app.gameState.playerWithTurn = opponents[0]
            DeclareManager.cancel(app)
        else:
            app.declareRemaining.remove(card)
            app.illegalAskMessage = None
            if not app.declareRemaining:
                app.declareMessage      = (f"{app.declareSet} declared! Team scores!", True)
                app.declareMessageTimer = 180
                app.gameState.playerWithTurn = declarer
                DeclareManager.resolveAndClear(app, declarer.team)
                DeclareManager.passToWaiting(app, declarer)
                DeclareManager.cancel(app)

    @staticmethod
    def passToWaiting(app, declarer):
        for p in app.gameState.players:
            if p.team == declarer.team and p != declarer and p.wantsTheTurn:
                if app.gameState.playerWithTurn == declarer:
                    p.wantsTheTurn = False
                    app.gameState.playerWithTurn = p
                break

    @staticmethod
    def resolveAndClear(app, teamIdx):
        setName = app.declareSet
        app.gameState.resolveSet(setName, teamIdx, source="declare")
        app.gameState.advanceTurnIfNeeded()
