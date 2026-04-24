import math
from cmu_graphics import *
import random
from constants import (
    teamColors, tableCx, tableCy, playerR, circleR,
    colorDeepSea, colorWaterMid, colorWaterTop,
    colorTable, colorCoral, colorBubble
)

suitSymbol = {
    'hearts': '♥', 'diamonds': '♦', 'clubs': '♣', 'spades': '♠',
    'red': '♥', 'black': '♣'
}

valShort = {
    'ten': '10', 'ace': 'A', 'jack': 'J', 'queen': 'Q', 'king': 'K',
    'joker': 'Jkr', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
    'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
}


class Renderer:
    baseW = 1400
    baseH = 800

    startupButtons = {
        'play': (430, 702, 210, 58, 'PLAY',       'Start digital game'),
        'deal': (760, 702, 210, 58, 'DEAL CARDS', 'Physical game setup'),
    }

    playerBubbles = [(550 + i * 60, 660, 22) for i in range(6)]

    @staticmethod
    def scale(app):
        return app.width / Renderer.baseW, app.height / Renderer.baseH

    @staticmethod
    def scaled(app, x, y):
        sx, sy = Renderer.scale(app)
        return x * sx, y * sy

    @staticmethod
    def baseCoords(app, screenX, screenY):
        sx, sy = Renderer.scale(app)
        return screenX / sx, screenY / sy

    @staticmethod
    def rect(app, x, y, w, h, **kw):
        nx, ny = Renderer.scaled(app, x, y)
        sx, sy = Renderer.scale(app)
        drawRect(nx, ny, w * sx, h * sy, **kw)

    @staticmethod
    def circle(app, x, y, r, **kw):
        nx, ny = Renderer.scaled(app, x, y)
        avg    = min(*Renderer.scale(app))
        drawCircle(nx, ny, r * avg, **kw)

    @staticmethod
    def oval(app, x, y, w, h, **kw):
        nx, ny = Renderer.scaled(app, x, y)
        sx, sy = Renderer.scale(app)
        drawOval(nx, ny, w * sx, h * sy, **kw)

    @staticmethod
    def label(app, text, x, y, size=12, **kw):
        nx, ny = Renderer.scaled(app, x, y)
        avg    = min(*Renderer.scale(app))
        drawLabel(text, nx, ny, size=size * avg, **kw)

    @staticmethod
    def playerPos(app, seatIdx):
        angle = math.radians(90 - seatIdx * 60)
        lx = tableCx + playerR * math.cos(angle)
        ly = tableCy + playerR * math.sin(angle)
        return Renderer.scaled(app, lx, ly)

    # ── Decorations ──────────────────────────────────────────────────────

    @staticmethod
    def drawBackground(app):
        W, H = Renderer.baseW, Renderer.baseH
        Renderer.rect(app, 0, 0, W, H,
                      fill=gradient(colorWaterTop, colorWaterMid, colorDeepSea, start='top'))
        for bx, by, br, bop in app.bubbles:
            Renderer.circle(app, bx, by, br, fill=colorBubble, opacity=bop)
        for fx, fy, fsize, fcolor, fdir in app.fish:
            Renderer.drawFish(app, fx, fy, fsize, fcolor, fdir)

    @staticmethod
    def drawFish(app, x, y, size, color, direction):
        Renderer.oval(app, x, y, size * 2, size, fill=color)
        tail_x = x - size if direction > 0 else x + size
        Renderer.label(app, "▶" if direction > 0 else "◀", tail_x, y, size=size, fill=color)
        eye_x = x + size * 0.5 if direction > 0 else x - size * 0.5
        Renderer.circle(app, eye_x, y - size * 0.2, size * 0.1, fill='white')

    # ── Card Drawing ─────────────────────────────────────────────────────

    @staticmethod
    def drawCard(app, card, px, py, w=75, h=105):
        isRed   = card.suit in ('hearts', 'diamonds', 'red')
        color   = 'crimson' if isRed else 'black'
        v       = valShort.get(card.value, card.value[0].upper())
        sym     = '★' if card.value == 'joker' else suitSymbol.get(card.suit, '?')

        Renderer.rect(app, px, py, w, h, fill='white', border=color, borderWidth=1.5)
        Renderer.label(app, v,   px + w * 0.2, py + h * 0.13, size=13, bold=True, fill=color)
        Renderer.label(app, sym, px + w * 0.2, py + h * 0.28, size=12, fill=color)
        Renderer.label(app, sym, px + w * 0.5, py + h * 0.5,  size=28, fill=color)
        Renderer.label(app, v,   px + w * 0.8, py + h * 0.87, size=13, bold=True, fill=color)
        Renderer.label(app, sym, px + w * 0.8, py + h * 0.72, size=12, fill=color)

    @staticmethod
    def drawCardBack(app, px, py, w=75, h=105):
        Renderer.rect(app, px, py, w, h, fill='navy', border='gold', borderWidth=2)
        Renderer.rect(app, px + 6, py + 6, w - 12, h - 12,
                      fill='midnightBlue', border='gold', borderWidth=1)
        Renderer.label(app, '◆', px + w * 0.5, py + h * 0.5, size=22, fill='gold')

    @staticmethod
    def drawCardGrid(app, cards, startX, startY,
                     cardsPerRow=9, cardW=75, cardH=105, xGap=87, yGap=120):
        sortedCards = sorted(cards, key=lambda c: (c.set, str(c)))
        col = row = 0
        for card in sortedCards:
            Renderer.drawCard(app, card,
                              startX + col * xGap,
                              startY + row * yGap,
                              cardW, cardH)
            col += 1
            if col == cardsPerRow:
                col = 0
                row += 1

    # ── Startup Screen ───────────────────────────────────────────────────

    @staticmethod
    def drawStartupScreen(app):
        Renderer.drawBackground(app)
        W = Renderer.baseW

        Renderer.rect(app, W // 2 - 320, 82, 640, 138,
                      fill='white', opacity=80, border='gold', borderWidth=4)
        Renderer.label(app, "FISH", W // 2, 135, size=68, bold=True, fill=colorDeepSea)
        Renderer.label(app, "The Deep Sea Card Game", W // 2, 198,
                       size=23, italic=True, fill=colorWaterMid)

        Renderer.rect(app, 150, 255, 500, 315,
                      fill='white', opacity=90, border=colorTable, borderWidth=2)
        Renderer.label(app, "How to Play", 400, 283, size=22, bold=True, fill=colorDeepSea)
        rules = [
            "• Ask opponents for cards in sets you hold.",
            "• Got it? Keep your turn. No? It's theirs.",
            "• You cannot ask for a card you already have.",
            "• Teammates cannot ask each other.",
            "• Declare a set when your team holds all 6.",
            "• First team to 5 sets wins the ocean!",
        ]
        y = 330
        for rule in rules:
            Renderer.label(app, rule, 172, y, size=13, align='left', fill='black')
            y += 38

        Renderer.rect(app, 750, 255, 500, 315,
                      fill='white', opacity=90, border=colorCoral, borderWidth=2)
        Renderer.label(app, "Game Modes", 1000, 283, size=22, bold=True, fill=colorDeepSea)
        modeLines = [
            ("PLAY",       "Start a digital game on this device."),
            ("",           "Non-human seats become bots."),
            ("DEAL CARDS", "Reveal each player's hand privately"),
            ("",           "to set up a physical card game."),
        ]
        y = 326
        for title, desc in modeLines:
            if title:
                Renderer.label(app, title, 775, y, size=16, bold=True, align='left', fill='navy')
                y += 22
            Renderer.label(app, desc, 775, y, size=13, align='left', fill='dimGrey')
            y += 34

        humanCount = getattr(app, 'startupHumanCount', 1)
        Renderer.label(app, "Human players:", W // 2, 622, size=17, bold=True, fill='white')
        n = 0
        for cx, cy, r in Renderer.playerBubbles:
            n += 1
            selected = (n == humanCount)
            Renderer.circle(app, cx, cy, r,
                            fill='gold' if selected else colorDeepSea,
                            border='gold' if selected else 'white', borderWidth=2)
            Renderer.label(app, str(n), cx, cy, size=16, bold=True,
                           fill=colorDeepSea if selected else 'white')

        bots     = 6 - humanCount
        hWord    = "human" if humanCount == 1 else "humans"
        botWord  = "bot" if bots == 1 else "bots"
        summary  = f"{humanCount} {hWord} + {bots} {botWord}" if bots > 0 else f"{humanCount} humans, no bots"
        Renderer.label(app, summary, W // 2, 693, size=14, fill='lightSteelBlue')

        for key, (bx, by, bw, bh, blabel, bsub) in Renderer.startupButtons.items():
            disabled = (key == 'play' and humanCount > 1)
            bgColor  = 'grey'     if disabled else colorDeepSea
            bdColor  = 'dimGrey'  if disabled else 'gold'
            txColor  = 'darkGrey' if disabled else 'white'
            subColor = 'darkGrey' if disabled else 'lightSteelBlue'
            Renderer.rect(app, bx, by, bw, bh, fill=bgColor, border=bdColor, borderWidth=2)
            Renderer.label(app, blabel, bx + bw // 2, by + bh * 0.4, size=21, bold=True, fill=txColor)
            Renderer.label(app, bsub,  bx + bw // 2, by + bh * 0.75, size=11, fill=subColor)

        if humanCount > 1:
            Renderer.label(app, "Use DEAL CARDS for multi-player games",
                           W // 2, 776, size=13, fill='gold')
        else:
            Renderer.label(app, "Type 1–6 to set player count  •  SPACE to play vs bots",
                           W // 2, 776, size=13, fill='white')

    # ── Deal Screen ──────────────────────────────────────────────────────

    @staticmethod
    def drawDealScreen(app):
        Renderer.drawBackground(app)
        W, H    = Renderer.baseW, Renderer.baseH
        players = app.dealHumanPlayers
        pidx    = app.dealPlayerIdx
        total   = len(players)

        Renderer.rect(app, 0, 0, W, 58, fill=colorDeepSea, opacity=88)
        Renderer.label(app, f"Fish — Dealing Cards  ({min(pidx + 1, total)} of {total})",
                       W // 2, 29, size=26, bold=True, fill='white')

        if pidx >= total:
            Renderer.rect(app, W // 2 - 310, H // 2 - 70, 620, 140,
                          fill='white', opacity=92, border='gold', borderWidth=3)
            Renderer.label(app, "All players have seen their cards!",
                           W // 2, H // 2 - 22, size=26, bold=True, fill=colorDeepSea)
            Renderer.label(app, "Press SPACE to start the game.",
                           W // 2, H // 2 + 22, size=20, fill=colorWaterMid)
            return

        player = players[pidx]

        if not app.dealRevealed:
            cardCount    = len(player.hand)
            cols         = min(cardCount, 9)
            backW, backH = 72, 100
            xGap         = 80
            totalW       = (cols - 1) * xGap + backW
            startX       = (W - totalW) // 2
            for i in range(cols):
                Renderer.drawCardBack(app, startX + i * xGap, 295, backW, backH)
            if cardCount > 9:
                remaining = cardCount - 9
                totalW2   = (remaining - 1) * xGap + backW
                startX2   = (W - totalW2) // 2
                for i in range(remaining):
                    Renderer.drawCardBack(app, startX2 + i * xGap, 410, backW, backH)
            Renderer.rect(app, W // 2 - 310, 535, 620, 95,
                          fill='white', opacity=88, border='gold', borderWidth=2)
            Renderer.label(app, f"Pass to  {player.name}",
                           W // 2, 567, size=30, bold=True, fill=colorDeepSea)
            Renderer.label(app, "Press SPACE to reveal your cards.",
                           W // 2, 607, size=18, fill=colorWaterMid)
        else:
            Renderer.rect(app, W // 2 - 300, 68, 600, 46,
                          fill='white', opacity=88, border=colorTable, borderWidth=2)
            Renderer.label(app, f"{player.name}'s Hand  ({len(player.hand)} cards)",
                           W // 2, 91, size=22, bold=True, fill=colorDeepSea)
            cardW, cardH, xGap = 72, 100, 82
            cols    = min(len(player.hand), 9)
            totalW  = (cols - 1) * xGap + cardW
            startX  = (W - totalW) // 2
            Renderer.drawCardGrid(app, player.hand, startX, 128,
                                  cardsPerRow=9, cardW=cardW, cardH=cardH,
                                  xGap=xGap, yGap=115)
            Renderer.rect(app, W // 2 - 290, 672, 580, 48,
                          fill='white', opacity=88, border='gold', borderWidth=2)
            if pidx + 1 < total:
                nxt = players[pidx + 1].name
                Renderer.label(app, f"Done? Press SPACE to pass to {nxt}.",
                               W // 2, 696, size=18, fill=colorDeepSea)
            else:
                Renderer.label(app, "Done? Press SPACE to start the game.",
                               W // 2, 696, size=18, fill=colorDeepSea)

    # ── Main Game UI ─────────────────────────────────────────────────────

    @staticmethod
    def drawPlayerTable(app):
        Renderer.oval(app, tableCx, tableCy, 240, 160,
                      fill=colorTable, border='white', borderWidth=3)
        Renderer.label(app, f"T1: {app.gameState.teams[0].setsTaken}",
                       tableCx - 40, tableCy, size=18, bold=True, fill='white')
        Renderer.label(app, f"T2: {app.gameState.teams[1].setsTaken}",
                       tableCx + 40, tableCy, size=18, bold=True, fill='white')

        sx, sy = Renderer.scale(app)
        for seat in range(6):
            player = app.gameState.players[seat]
            px, py = Renderer.playerPos(app, seat)
            lx, ly = px / sx, py / sy

            if player == app.gameState.playerWithTurn:
                Renderer.circle(app, lx, ly, circleR + 6, fill='gold', opacity=70)

            Renderer.circle(app, lx, ly, circleR,
                            fill=teamColors[player.team], border='white', borderWidth=2)
            Renderer.label(app, str(seat + 1), lx, ly, size=20, bold=True, fill='white')

            labelOffset = (circleR + 15) if ly >= tableCy else -(circleR + 15)
            Renderer.label(app, player.name.capitalize(), lx, ly + labelOffset,
                           size=14, fill='white', bold=True)

    @staticmethod
    def drawInputBox(app):
        slotW = 80
        slotH = 60
        gap   = 15
        total = 4 * slotW + 3 * gap
        sx0   = tableCx - total // 2
        sy    = 630

        if app.illegalAskMessage:
            Renderer.rect(app, 50, sy, 500, 30, fill='crimson', border=None)
            Renderer.label(app, app.illegalAskMessage, tableCx, sy + 15,
                           size=14, bold=True, fill='white')
            sy += 40
        else:
            Renderer.label(app, "Type shortcode", tableCx, sy + 15,
                           size=16, fill='white', bold=True)
            sy += 30

        cx = sx0 + slotW // 2
        for hint in ['Who', 'Val', 'Suit', 'Res']:
            Renderer.label(app, hint, cx, sy, size=12, fill='white')
            cx += slotW + gap
        sy += 20

        sx  = sx0
        buf = app.inputBuffer
        for i in range(4):
            ch     = buf[i] if i < len(buf) else ''
            active = (i == len(buf))
            Renderer.rect(app, sx, sy, slotW, slotH,
                          fill='white', opacity=90,
                          border='gold' if active else 'white', borderWidth=2)
            if ch:
                Renderer.label(app, ch.upper(), sx + slotW // 2, sy + slotH // 2,
                               size=32, bold=True, fill=colorDeepSea)
            elif active:
                Renderer.label(app, '_', sx + slotW // 2, sy + slotH // 2 + 5,
                               size=24, fill='lightBlue')
            sx += slotW + gap

    @staticmethod
    def drawUserHand(app):
        user = app.gameState.players[0]
        if not user.hand:
            return
        startX, startY = 600, 155
        cardW, cardH   = 72, 100
        availableW     = 790

        n    = len(user.hand)
        xGap = min(82, (availableW - cardW) // max(n - 1, 1))

        Renderer.label(app, "Your Hand:", startX, startY - 28,
                       size=20, bold=True, align='left', fill='white')
        for i, card in enumerate(sorted(user.hand, key=lambda c: (c.set, str(c)))):
            Renderer.drawCard(app, card, startX + i * xGap, startY, cardW, cardH)

    @staticmethod
    def drawInfoPanel(app):
        x, y = 600, 600
        Renderer.label(app, "Shortcode Legend:", x, y,
                       size=16, bold=True, align='left', fill='white')
        Renderer.label(app, "A=Ace  2–9  T=Ten  J=Jack  Q=Queen  K=King  X=Joker",
                       x, y + 25, size=12, align='left', fill='white')
        Renderer.label(app, "H=Hearts  D=Diamonds  C=Clubs  S=Spades  R=Red  B=Black",
                       x, y + 45, size=12, align='left', fill='white')
        Renderer.label(app, "Example: 2JH (Ask Player 2 for Jack of Hearts)",
                       x, y + 65, size=12, italic=True, align='left', fill='white')

    @staticmethod
    def drawAll(app):
        if app.screen == 'startup':
            Renderer.drawStartupScreen(app)
            return

        if app.screen == 'deal':
            Renderer.drawDealScreen(app)
            return

        Renderer.drawBackground(app)
        W, H = Renderer.baseW, Renderer.baseH

        Renderer.rect(app, 0, 0, W, 60, fill=colorDeepSea, opacity=80)
        Renderer.label(app, "Fish: Ocean Edition", W // 2, 30,
                       size=32, bold=True, fill='white')

        Renderer.drawPlayerTable(app)

        Renderer.rect(app, 50, 520, 500, 40,
                      fill='white', opacity=80, border='white', borderWidth=1)
        turnText = f"Turn: {app.gameState.playerWithTurn.name.capitalize()}"
        if app.gameState.playerWithTurn.isBot:
            turnText += " (Bot Thinking...)"
        Renderer.label(app, turnText, tableCx, 540,
                       size=18, fill=colorDeepSea, bold=True)

        if app.gameState.asks:
            last = app.gameState.asks[-1]
            Renderer.label(app, str(last), tableCx, 580,
                           size=14, fill='white', bold=True)
            rc = 'springGreen' if last.gotCard else 'orangeRed'
            Renderer.label(app, "✓ SUCCESS" if last.gotCard else "✗ FAILED",
                           tableCx, 605, size=16, bold=True, fill=rc)

        Renderer.drawInputBox(app)
        if getattr(app, 'isVsBots', True):
            Renderer.drawUserHand(app)
            Renderer.drawInfoPanel(app)

        Renderer.label(app, "R=Reset  Esc=Clear buffer  Bksp=Delete  M=Mic",
                       W // 2, H - 15, size=12, fill='white')

        if app.gameState.winner:
            teamNum = 1 if app.gameState.winner == app.gameState.teams[0] else 2
            Renderer.rect(app, 0, 0, W, H, fill='black', opacity=60)
            Renderer.rect(app, W // 2 - 200, H // 2 - 50, 400, 100,
                          fill='gold', border='white', borderWidth=3)
            Renderer.label(app, f"TEAM {teamNum} WINS!", W // 2, H // 2,
                           size=40, bold=True)
