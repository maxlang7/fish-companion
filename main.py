from cmu_graphics import *
import random
import os
import time

from app_setup import AppSetup
from logic import BotStrategy
from parser import ShortcodeParser, DeclareManager
from ui import Renderer

# WHOLE FILE AI
def onAppStart(app):
    AppSetup.initApp(app)
    Renderer.initDecorations(app)

def onMousePress(app, mouseX, mouseY):
    if app.screen != "startup":
        return
    bx, by = Renderer.baseCoords(app, mouseX, mouseY)

    for i in range(len(Renderer.playerBubbles)):
        cx, cy, r = Renderer.playerBubbles[i]
        if (bx - cx) ** 2 + (by - cy) ** 2 <= r**2:
            app.startupHumanCount = i + 1
            return

    for key, (rx, ry, rw, rh, label, sub) in Renderer.startupButtons.items():
        if rx <= bx <= rx + rw and ry <= by <= ry + rh:
            if key == "play" and app.startupHumanCount == 1:
                AppSetup.startGame(app, 1)
            elif key == "short":
                AppSetup.startShortGame(app)
            elif key == "watch":
                AppSetup.startBotsOnly(app)
            elif key == "deal":
                AppSetup.startDeal(app, app.startupHumanCount)
            return

#AI
def onKeyPress(app, key, modifiers):
    if app.screen == "startup":
        if key == "space" and app.startupHumanCount == 1:
            AppSetup.startGame(app, 1)
        elif key == "0":
            AppSetup.startBotsOnly(app)
        elif key.isdigit() and 1 <= int(key) <= 6:
            app.startupHumanCount = int(key)
        return

    if app.screen == "deal":
        if key == "space":
            if not app.dealRevealed:
                app.dealRevealed = True
            else:
                app.dealPlayerIdx += 1
                if app.dealPlayerIdx >= len(app.dealHumanPlayers):
                    app.screen = "game"
                else:
                    app.dealRevealed = False
        return

    if key == "R":
        AppSetup.initApp(app)
        return

    if key == "escape":
        if app.declareMode:
            DeclareManager.cancel(app)
        else:
            app.inputBuffer = ""
            app.illegalAskMessage = None
        return

    if key == "backspace" and not app.gameState.playerWithTurn.isBot:
        app.inputBuffer = app.inputBuffer[:-1]
        app.illegalAskMessage = None
        return

    if key == "p" and not app.gameState.playerWithTurn.isBot:
        player = app.gameState.playerWithTurn
        player.wantsTheTurn = not player.wantsTheTurn
        print(f"  {player.name}: wants the turn = {player.wantsTheTurn}")
        return

    if key == "D" and not app.declareMode:
        human = next((p for p in app.gameState.players if not p.isBot), None)
        if human and human.hand and app.gameState.playerWithTurn.team == human.team:
            DeclareManager.start(app, declarer=human)
        return

    if app.declareMode:
        if len(key) == 1:
            app.inputBuffer += key
            app.illegalAskMessage = None
            if app.declarePhase == "select" and len(app.inputBuffer) == 2:
                DeclareManager.submitSetCode(app)
            elif app.declarePhase == "assign" and len(app.inputBuffer) == 3:
                DeclareManager.submitAssignment(app)
        return

    if app.gameState.playerWithTurn.isBot and not app.declareMode:
        return
    
    
    if len(key) == 1 and len(app.inputBuffer) < 4:
        app.inputBuffer += key
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
    if app.declareMessageTimer > 0:
        app.declareMessageTimer -= 1

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

    if app.screen == "game" and app.gameState.winner is not None:
        if app.exitAt is None:
            app.exitAt = time.time() + 5
        elif time.time() >= app.exitAt:
            os._exit(0)

    if (
        app.screen == "game"
        and app.gameState.winner is None
        and app.gameState.playerWithTurn.isBot
    ):
        app.stepCount += 1
        if app.stepCount >= app.stepDelay:
            app.stepCount = 0
            BotStrategy.performMove(app, app.gameState.playerWithTurn)


def redrawAll(app):
    Renderer.drawAll(app)


def main():
    runApp(width=1200, height=700)


if __name__ == "__main__":
    main()
