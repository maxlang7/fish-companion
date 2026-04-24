import random
from models import Card, Ask

class Analyzer:
    @staticmethod
    def illegalAskReason(game, ask):
        s = ask.card.set

        if ask.asker == ask.asked:
            return "You can't ask yourself"
        if ask.asker.team == ask.asked.team:
            return "You can't ask a teammate"
        if ask.card in ask.asker.hand or game.publicInfo[s][ask.card] == {ask.asker}:
            return f"You already have {ask.card}"

        playersInSet = set()
        for possible in game.publicInfo[s].values():
            playersInSet |= possible

        if ask.asker.isBot and ask.asker.hand:
            if not any(c.set == s for c in ask.asker.hand):
                return f"You have no cards in {s}"
        if ask.asker not in playersInSet:
            return f"You have no cards in {s}"

        return None

    @staticmethod
    def getLegalAsks(game, player):
        if not player.hand:
            return []
        opponents    = [p for p in game.players if p.team != player.team]
        possibleSets = {card.set for card in player.hand}
        candidates   = {c for c in Card.getAllCards()
                        if c.set in possibleSets and c not in player.hand}
        return [
            Ask(player, opp, card)
            for card in candidates
            for opp  in opponents
            if not Analyzer.illegalAskReason(game, Ask(player, opp, card))
        ]


class BotStrategy:
    selfishProb = 0.10

    @staticmethod
    def opponentPool(game, card, opponents):
        return game.publicInfo[card.set][card] & opponents

    @staticmethod
    def setCompletionScore(game, bot, setName):
        teamPlayers = {p for p in game.players if p.team == bot.team}
        return sum(
            1 for possible in game.publicInfo[setName].values()
            if len(possible) == 1 and next(iter(possible)) in teamPlayers
        )

    @staticmethod
    def bestAskInSet(game, bot, asks):
        opponents = {p for p in game.players if p.team != bot.team}

        def score(ask):
            opPool = BotStrategy.opponentPool(game, ask.card, opponents)
            if not opPool:
                return (float('inf'), float('inf'), random.random())
            inPool = 0 if ask.asked in opPool else 1
            return (len(opPool), inPool, random.random())

        return min(asks, key=score)

    @staticmethod
    def selfishAsk(game, bot, legalAsks):
        opponents  = {p for p in game.players if p.team != bot.team}
        setGroups  = {}
        for ask in legalAsks:
            # what is s
            setGroups.setdefault(ask.card.set, []).append(ask)

        def setScore(setName, askList):
            certainty  = sum(
                1.0 / max(len(BotStrategy.opponentPool(game, a.card, opponents)), 1)
                for a in askList
            )
            completion = BotStrategy.setCompletionScore(game, bot, setName)
            return (certainty, completion)

        bestSet = max(setGroups, key=lambda s: setScore(s, setGroups[s]))
        return BotStrategy.bestAskInSet(game, bot, setGroups[bestSet])

    @staticmethod
    def followTeammate(game, bot, legalAsks):
        teammates = {p for p in game.players if p.team == bot.team and p != bot}
        targetSet = None
        for ask in reversed(game.asks):
            if ask.asker in teammates:
                targetSet = ask.card.set
                break
        if targetSet is None:
            return None
        setAsks = [a for a in legalAsks if a.card.set == targetSet]
        if not setAsks:
            return None
        return BotStrategy.bestAskInSet(game, bot, setAsks)

    @staticmethod
    def chooseMove(game, bot):
        legalAsks = Analyzer.getLegalAsks(game, bot)
        if not legalAsks:
            return None
        if random.random() > BotStrategy.selfishProb:
            ask = BotStrategy.followTeammate(game, bot, legalAsks)
            if ask:
                return ask
        return BotStrategy.selfishAsk(game, bot, legalAsks)

    @staticmethod
    def resolveOutcome(game, ask):
        possible = game.publicInfo[ask.card.set][ask.card]
        if len(possible) == 1:
            return next(iter(possible)) == ask.asked
        return random.choice([True, False])

    @staticmethod
    def performMove(app, bot):
        ask = BotStrategy.chooseMove(app.gameState, bot)
        if ask is None:
            print(f"  [BOT] {bot.name} has no legal asks.")
            return
        ask.gotCard = BotStrategy.resolveOutcome(app.gameState, ask)
        app.gameState.recordMove(ask)
        print(f"  [BOT] {ask}")
