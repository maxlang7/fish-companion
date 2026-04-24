from models import Card, Ask
from constants import valueMap, suitMap
from logic import Analyzer

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
        if code[0].lower() == 'd':
            return ShortcodeParser.parseDeclare(code)
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
    def parseDeclare(code):
        setCode = code[1:3].lower()
        result  = code[3].lower()
        if setCode not in setMap:
            return None, "Invalid set code"
        if result not in ('y', 'n'):
            return None, "Must end in Y or N"
        return ('DECLARE', setMap[setCode], result == 'y'), None

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
        if isinstance(parsed, tuple) and parsed[0] == 'DECLARE':
            _, setName, success = parsed
            if setName in app.gameState.completedSets:
                app.illegalAskMessage = "Set already declared"
                return
            winningTeam = app.gameState.playerWithTurn.team if success else 1 - app.gameState.playerWithTurn.team
            app.gameState.resolveSet(setName, winningTeam, source="manual")
            return
        reason = Analyzer.illegalAskReason(app.gameState, parsed)
        if reason:
            app.illegalAskMessage = reason
        else:
            app.illegalAskMessage = None
            app.gameState.recordMove(parsed)
            print(f"  ✓  {parsed}")
