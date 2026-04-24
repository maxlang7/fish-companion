import sys
import threading
import tests
from models import Card, Ask
from game import LiteratureGame
from logic import Analyzer, BotStrategy
from listener import Listener
import random

class TestManager:
    @staticmethod
    def seedCard(game, playerIdx, val, suit):
        player = game.players[playerIdx]
        card   = Card(val, suit)
        game.publicInfo[card.set][card] = {player}

    @staticmethod
    def runTestMove(app, askerIdx, askedIdx, val, suit, got):
        asker = app.gameState.players[askerIdx]
        asked = app.gameState.players[askedIdx]
        card  = Card(val, suit)
        move  = Ask(asker, asked, card, got)
        if not Analyzer.illegalAskReason(app.gameState, move):
            app.gameState.recordMove(move)
            print(f"Test Move: {move}")

    @staticmethod
    def runTest(app, testKey):
        allTests = tests.get_test_cases()
        if testKey not in allTests:
            print(f"Test '{testKey}' not found. Available: {list(allTests.keys())}")
            return
        print(f"--- Running Test: {testKey} ---")
        for action in allTests[testKey]:
            if action[0] == 'seed':
                TestManager.seedCard(app.gameState, action[1], action[2], action[3])
            elif action[0] == 'move':
                TestManager.runTestMove(app, action[1], action[2], action[3], action[4], action[5])


class AppSetup:
    @staticmethod
    def showHelp():
        print("""
            Fish Game CLI Usage:
            ====================
            1. Live Mode:   python main3.py <p1> <p2> <p3> <p4> <p5> <p6>
            2. Vs Bots:     python main3.py --vs-bots
            3. Run Tests:   python main3.py test
        """)

    @staticmethod
    def buildGame(playerNames, botCards, doLog, shuffle):
        return LiteratureGame(playerNames, botCards=botCards, doLog=doLog, shuffle=shuffle)

    @staticmethod
    def parseArgs():
        args     = sys.argv[1:]
        allTests = tests.get_test_cases()

        if '--help' in args or '-h' in args:
            AppSetup.showHelp()
            sys.exit(0)

        isVsBots     = '--vs-bots' in args
        isTest       = 'test' in args or any(a in allTests for a in args)
        testKey      = next((a for a in args if a in allTests), None)
        botCards     = {}
        playerNames  = None

        if isVsBots:
            playerNames = ['You', 'bot', 'bot', 'bot', 'bot', 'bot']
        else:
            found = []
            for arg in args:
                if arg.startswith('--') or arg in allTests or arg == 'test':
                    continue
                if ':' in arg:
                    name, cards = arg.split(':', 1)
                    botCards[len(found)] = cards.split(',')
                    found.append(name)
                else:
                    found.append(arg)
                if len(found) == 6:
                    break

            if len(found) == 6:
                playerNames = found
            elif not isTest:
                if len(found) == 0:
                    playerNames = ['You', 'bot', 'bot', 'bot', 'bot', 'bot']
                else:
                    print(f"Error: Expected 6 players, got {len(found)}: {found}")
                    AppSetup.showHelp()
                    sys.exit(1)

        if isTest and playerNames is None:
            playerNames = ['max', 'jack', 'alex', 'kevin', 'ben', 'darren']

        return playerNames, botCards, isVsBots, isTest, testKey

    @staticmethod
    def applyCommonState(app, gameState, screen):
        app.gameState         = gameState
        app.screen            = screen
        app.inputBuffer       = ''
        app.illegalAskMessage = None
        app.stepCount         = 0
        app.stepDelay         = 60
        app.useMic            = False
        app.isListening       = False
        if not hasattr(app, 'bubbles'):
            app.bubbles = [
                (random.randint(0, 1400), random.randint(0, 800),
                 random.randint(5, 20), random.randint(20, 60))
                for _ in range(30)
            ]
            app.fish = [
                (random.randint(0, 1400), random.randint(100, 700),
                 random.randint(10, 30),
                 random.choice(['orange', 'yellow', 'coral', 'silver', 'gold']),
                 random.choice([-1, 1]))
                for _ in range(8)
            ]

    @staticmethod
    def buildNames(humanCount):
        names = []
        humanNum = 0
        for i in range(6):
            if i < humanCount:
                humanNum += 1
                names.append('You' if humanCount == 1 else f'Player {humanNum}')
            else:
                names.append('bot')
        return names

    @staticmethod
    def startGame(app, humanCount=1):
        names     = AppSetup.buildNames(humanCount)
        gameState = AppSetup.buildGame(names, {}, doLog=True, shuffle=True)
        AppSetup.applyCommonState(app, gameState, 'game')
        app.isVsBots  = True
        app.stepDelay = 60

    @staticmethod
    def startDeal(app, humanCount=6):
        names     = AppSetup.buildNames(humanCount)
        gameState = AppSetup.buildGame(names, {}, doLog=False, shuffle=True)
        AppSetup.applyCommonState(app, gameState, 'deal')
        app.isVsBots         = False
        app.stepDelay        = 3
        app.dealHumanPlayers = [p for p in gameState.players if not p.isBot]
        app.dealPlayerIdx    = 0
        app.dealRevealed     = False

    @staticmethod
    def initApp(app):
        playerNames, botCards, isVsBots, isTest, testKey = AppSetup.parseArgs()
        allTests = tests.get_test_cases()

        app.gameState         = AppSetup.buildGame(playerNames, botCards, doLog=not isTest, shuffle=isVsBots)
        app.isListening       = True
        app.useMic            = False
        app.illegalAskMessage = None
        app.inputBuffer       = ''
        app.stepCount         = 0
        app.stepDelay         = 60
        app.isVsBots          = isVsBots
        app.screen            = 'startup' if not (isTest or isVsBots or botCards or len(sys.argv) > 1) else 'game'
        app.dealPlayerIdx     = 0
        app.dealRevealed      = False
        app.dealHumanPlayers  = []
        app.startupHumanCount = 1

        app.bubbles = [
            (random.randint(0, 1400), random.randint(0, 800),
             random.randint(5, 20), random.randint(20, 60))
            for _ in range(30)
        ]
        app.fish = [
            (random.randint(0, 1400), random.randint(100, 700),
             random.randint(10, 30),
             random.choice(['orange', 'yellow', 'coral', 'silver', 'gold']),
             random.choice([-1, 1]))
            for _ in range(8)
        ]

        if 'test' in sys.argv:
            for key in allTests:
                app.gameState = AppSetup.buildGame(playerNames, botCards, doLog=False, shuffle=False)
                TestManager.runTest(app, key)
            print("\n" + "=" * 30)
            print("  ALL TESTS PASSED SUCCESSFULLY!  ")
            print("=" * 30 + "\n")
            sys.exit(0)

        if testKey:
            app.gameState = AppSetup.buildGame(playerNames, botCards, doLog=False, shuffle=False)
            TestManager.runTest(app, testKey)
            sys.exit(0)

        app.listener = Listener(app.gameState)
        app.thread   = threading.Thread(
            target=app.listener.backgroundListen, args=(app,), daemon=True)
        app.thread.start()
