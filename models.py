from constants import valueMap, suitMap

class Card:
    digitToWord = {
        '1': 'ace', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
        '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten'
    }
    lowValues  = {'two', 'three', 'four', 'five', 'six', 'seven'}
    highValues = {'nine', 'ten', 'jack', 'queen', 'king', 'ace'}

    def __init__(self, value, suit):
        self.value = self.digitToWord.get(str(value), str(value))
        self.suit  = suit
        if self.value in ('joker', 'eight'):
            self.set = 'Eights and Jokers'
        elif self.value in self.lowValues:
            self.set = f'Low {self.suit.capitalize()}'
        elif self.value in self.highValues:
            self.set = f'High {self.suit.capitalize()}'

    def __repr__(self):
        if self.value == 'joker':
            return f"{self.suit.capitalize()} Joker"
        return f"{self.value.capitalize()} of {self.suit.capitalize()}"

    def __str__(self):  return self.__repr__()
    def __eq__(self, other):
        return isinstance(other, Card) and self.value == other.value and self.suit == other.suit
    def __hash__(self): return hash((self.value, self.suit))

    @staticmethod
    def getAllCards():
        cards = [
            Card(val, suit)
            for suit in ['hearts', 'diamonds', 'clubs', 'spades']
            for val  in ['ace', 'two', 'three', 'four', 'five', 'six', 'seven',
                         'eight', 'nine', 'ten', 'jack', 'queen', 'king']
        ]
        cards.append(Card('joker', 'black'))
        cards.append(Card('joker', 'red'))
        return cards


class Player:
    def __init__(self, name, team, isBot=False):
        self.name  = name
        self.team  = team
        self.isBot = isBot
        self.hand  = set()

    def __repr__(self):
        return f"{self.name}{' (Bot)' if self.isBot else ''}"


class Team:
    def __init__(self, players):
        self.players   = players
        self.setsTaken = 0


class Ask:
    def __init__(self, asker, asked, card, gotCard=None):
        self.asker   = asker
        self.asked   = asked
        self.card    = card
        self.gotCard = gotCard

    def __repr__(self):
        result = "got it" if self.gotCard is True else ("didn't get it" if self.gotCard is False else "waiting...")
        return (f"{self.asker.name.capitalize()} asked "
                f"{self.asked.name.capitalize()} for {self.card} and {result}")
