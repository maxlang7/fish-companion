from cmu_graphics import *
import random
from app_setup import AppSetup
from ui import Renderer
from parser import ShortcodeParser
from logic import BotStrategy

def onAppStart(app):
    AppSetup.initApp(app)

def onMousePress(app, mouseX, mouseY):
    if app.screen != 'startup':
        return
    bx, by = Renderer.baseCoords(app, mouseX, mouseY)

    for i, (cx, cy, r) in enumerate(Renderer.playerBubbles):
        if (bx - cx) ** 2 + (by - cy) ** 2 <= r ** 2:
            app.startupHumanCount = i + 1
            return

    for key, (rx, ry, rw, rh, _label, _sub) in Renderer.startupButtons.items():
        if rx <= bx <= rx + rw and ry <= by <= ry + rh:
            if key == 'play' and app.startupHumanCount == 1:
                AppSetup.startGame(app, 1)
            elif key == 'deal':
                AppSetup.startDeal(app, app.startupHumanCount)
            return

def onKeyPress(app, key):
    if app.screen == 'startup':
        if key == 'space' and app.startupHumanCount == 1:
            AppSetup.startGame(app, 1)
        elif key.isdigit() and 1 <= int(key) <= 6:
            app.startupHumanCount = int(key)
        return

    if app.screen == 'deal':
        if key == 'space':
            if not app.dealRevealed:
                app.dealRevealed = True
            else:
                app.dealPlayerIdx += 1
                if app.dealPlayerIdx >= len(app.dealHumanPlayers):
                    app.screen = 'game'
                else:
                    app.dealRevealed = False
        return

    if key == 'r':
        AppSetup.initApp(app)
        return

    if key == 'm':
        app.useMic = not app.useMic
        print(f"Mic: {'On' if app.useMic else 'Off'}")
        return

    if key == 'escape':
        app.inputBuffer       = ''
        app.illegalAskMessage = None
        return

    if key == 'backspace':
        app.inputBuffer       = app.inputBuffer[:-1]
        app.illegalAskMessage = None
        return

    if len(key) == 1 and len(app.inputBuffer) < 4:
        app.inputBuffer      += key
        app.illegalAskMessage = None

        if len(app.inputBuffer) == 3:
            try:
                targetIdx = int(app.inputBuffer[0]) - 1
                if 0 <= targetIdx < len(app.gameState.players):
                    if app.gameState.players[targetIdx].isBot:
                        ShortcodeParser.submit(app)
                        return
            except (ValueError, IndexError):
                pass

        if len(app.inputBuffer) == 4:
            ShortcodeParser.submit(app)

def onStep(app):
    newBubbles = []
    for bx, by, br, bop in app.bubbles:
        by -= random.uniform(0.5, 2.0)
        if by < -20:
            by = 820
        newBubbles.append((bx, by, br, bop))
    app.bubbles = newBubbles

    newFish = []
    for fx, fy, fsize, fcolor, fdir in app.fish:
        fx += fdir * random.uniform(1, 3)
        if fx > 1450:
            fx = -50
        elif fx < -50:
            fx = 1450
        newFish.append((fx, fy, fsize, fcolor, fdir))
    app.fish = newFish

    if app.screen == 'game' and app.gameState.winner is None \
            and app.gameState.playerWithTurn.isBot:
        app.stepCount += 1
        if app.stepCount >= app.stepDelay:
            app.stepCount = 0
            BotStrategy.performMove(app, app.gameState.playerWithTurn)

def redrawAll(app):
    Renderer.drawAll(app)

def main():
    runApp(width=1400, height=800)

if __name__ == '__main__':
    main()
