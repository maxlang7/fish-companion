"""
Literature (Fish) — Rules and Feature Guide
============================================

GAME OVERVIEW
-------------
Literature (also called Fish) is a 6-player card game with 2 teams of 3.
Players sit in alternating seats: Team 0 = seats 0, 2, 4 / Team 1 = seats 1, 3, 5.
The deck is divided into 9 "sets" of 6 cards each (e.g. Low Hearts = 2-7 of hearts,
High Hearts = 8-A of hearts, Eights and Jokers = all 8s + both jokers, etc.).
Each player is dealt 9 cards at the start.

ON YOUR TURN
------------
You must ask an opponent for a specific card. Two rules apply:
  1. You must already hold at least one card from that card's set.
  2. You cannot ask for a card you already have.
If the opponent has it, you get it and keep your turn. If not, their turn begins.
Teammates cannot ask each other.

DECLARING A SET
---------------
At any point when it is your team's turn, you (or a teammate) can declare a set.
To declare, you assign each of the 6 cards in the set to a specific teammate.
If every assignment is correct, your team scores the set.
If any assignment is wrong (misdeclare), the opposing team scores the set instead.
All 6 cards are removed from play regardless of outcome.
First team to 5 sets wins. There are 9 sets total so ties (4-4 with 1 remaining)
are resolved by whoever declares the last set.

HOW TO PLAY (DIGITAL MODE)
---------------------------
Run:  python main.py

STARTUP SCREEN BUTTONS:
  PLAY       — 1 human vs 5 bots. Type shortcodes to make moves.
  SHORT GAME — Same but with only 2 sets (12 cards total), good for quick testing.
  WATCH      — All 6 players are bots. Runs instantly with no delay.
  DEAL CARDS — For a physical card game: reveals each player's hand privately
               so they can pick up their real cards, then hides them.

IN-GAME CONTROLS:
  Shortcode format to ask: <player#><value><suit>
    e.g. "23h" = ask player 2 for 3 of hearts
    e.g. "2ah" = ask player 2 for ace of hearts
    Values: a=ace, 2-9, t=ten, j=jack, q=queen, k=king, r=red joker, b=black joker
    Suits:  h=hearts, d=diamonds, c=clubs, s=spades
    When asking a bot (who has a known hand), 3 chars suffice (no Y/N needed).
    When asking a human, add y/n as 4th char to confirm if they had the card.

  D          — Enter declare mode (works on your team's turn, not just yours).
               First type a 2-char set code (e.g. "lh" = Low Hearts, "ej" = Eights
               and Jokers). Cards you hold are auto-assigned. For remaining cards,
               type <player#><value><suit> to assign each one. Wrong assignment =
               misdeclare. Press Escape to cancel.
  P          — Toggle "I want the turn" flag. If a bot teammate can declare a set
               with certainty, it will do so and pass the turn to you.
  R          — Reset / restart the game.
  Escape     — Cancel declare mode or clear the input buffer.
  Backspace  — Delete last character from input buffer.

SET CODES FOR DECLARING:
  lh=Low Hearts, ld=Low Diamonds, lc=Low Clubs, ls=Low Spades
  hh=High Hearts, hd=High Diamonds, hc=High Clubs, hs=High Spades
  ej=Eights and Jokers

CLI FLAGS:
  --vs-bots    : 1 human vs 5 bots (same as PLAY button)
  --short-game : 2-set game (same as SHORT GAME button)
  --bots-only  : all 6 bots, no human (same as WATCH button)
  test         : run all automated test cases and exit

BOT INTELLIGENCE
----------------
Bots use public information (the history of all asks) to infer card locations.
Each ask narrows down who might hold a card. Bots only ask opponents they
know could have a card. Bot strategy priority:
  1. Continue asking in the same set if the last ask succeeded (momentum).
  2. 90% chance: follow a teammate's set to help them declare.
  3. 10% chance (or no teammate lead): pick the set with most known locations.
  4. If no legal asks: declare if certain, otherwise make a best guess.
  Bots set a "wants the turn" flag when they know all card locations in a set
  and at least one is held by an opponent — signaling a teammate to pass them
  the turn after declaring.

GAME LOGGING
------------
Every move in a live game is automatically logged to the games/ directory as a
timestamped .txt file (e.g. games/2025-04-24_game_1.txt). Each line records the
time and a human-readable description of the ask. Logging is disabled during
tests and deal-mode setup games.

TESTING FRAMEWORK
-----------------
Run:  python main.py test

Tests live in tests.py and are defined as sequences of two action types:
  ('seed', player_idx, value, suit)      — force a card into publicInfo as known
  ('move', asker_idx, asked_idx, value, suit, got) — simulate an ask

Test cases cover:
  duplicate     — asking for a card you already have is rejected
  empty_set     — asking when publicInfo has no info yet is allowed
  simple_success — a valid ask succeeds and the card transfers
  simple_fail    — a failed ask passes the turn correctly
  ask_self       — asking yourself is rejected
  exhaust_set    — after all cards in a set are proven absent from a player,
                   asking that player for another card in the set is rejected
  take_set       — acquiring all 6 cards in a set triggers automatic set resolution

To run a single named test:  python main.py <test_name>
  e.g.  python main.py take_set
"""

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
