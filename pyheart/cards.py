import random
from typing import Iterable
from pyheart.exceptions import DeadCardError, EmptyDeckError


CARDS = (
    # https://www.hearthpwn.com/cards/27400-hungry-naga
    dict(name='Hungry Naga', cost=1, attack=1, health=1),
    # https://www.hearthpwn.com/cards/27375-mechanical-parrot
    dict(name='Mechanical Parrot', cost=1, attack=3, health=6),
)


class Card:
    def __init__(self, name: str, cost: int):
        self.name = name
        self.cost = cost

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{0.__class__.__name__}: {0.name}>'.format(self)


class MinionCard(Card):
    def __init__(self, name: str, cost: int, attack: int, health: int):
        super(MinionCard, self).__init__(name, cost)
        self.attack = attack
        self.health = health

    def attack(self, card):
        card.health -= self.attack
        self.health -= card.attack
        if self.health <= 0:
            raise DeadCardError('After attacking health is below 0')

    def __repr__(self):
        return '<{0.__class__.__name__}: {0.name} {0.health} HP>'.format(self)


class Deck:
    NUMBER_OF_COPIES = 2

    def __init__(self, cards: Iterable[Card]=None):
        if cards is not None:
            self.cards = list(cards)
        else:
            self.cards = [
                MinionCard(name, cost, attack, health)
                for name, cost, attack, health in CARDS
            ] * self.NUMBER_OF_COPIES
        self.empty_card = 0

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, number: int=1):
        next_cards = self.cards[:number]
        self.cards = self.cards[number:]
        if not next_cards and number > 0:
            self.empty_card += 1
            raise EmptyDeckError(self.empty_card)
        return next_cards

    def __len__(self):
        return len(self.cards)

    def __bool__(self):
        return True

    def __repr__(self):
        return '<{0.__class__.__name__} available cards: {1}>'.format(self, len(self))
