import random
from typing import Iterable
from pyheart.exceptions import DeadCardError, EmptyDeckError, CardCannotAttackError


class Ability:
    def apply(self, card: 'MinionCard', phase_name: str):
        phase_method_name = f'_{phase_name}_phase'
        getattr(self, phase_method_name, self.__default_method)(card)

    def __default_method(self, *args, **kwargs):
        pass


class ChargeAbility(Ability):
    def _init_phase(self, card: 'MinionCard'):
        card.can_attack = True


class IncreaseAttackAbility(Ability):
    def __init__(self, value: int):
        self._val = value

    def _play_phase(self, card: 'MinionCard'):
        card.attack += self._val


CARDS = (
    # https://www.hearthpwn.com/cards/27400-hungry-naga
    dict(name='Hungry Naga', cost=1, attack=1, health=1),
    # https://www.hearthpwn.com/cards/14652-black-whelp
    dict(name='Black Whelp', cost=1, attack=2, health=1),
    # https://www.hearthpwn.com/cards/27375-mechanical-parrot
    dict(name='Mechanical Parrot', cost=1, attack=3, health=6),
    # https://www.hearthpwn.com/cards/14630-bone-construct
    dict(name='Bone Construct', cost=1, attack=4, health=2),
    # https://www.hearthpwn.com/cards/27334-animated-statue
    dict(name='Animated Statue', cost=1, attack=10, health=10),
    # https://www.hearthpwn.com/cards/14612-aberration
    dict(name='Aberration', cost=1, attack=1, health=1, ability=ChargeAbility()),
    # https://www.hearthpwn.com/cards/77024-abusive-sergeant
    dict(name='Abusive Sergeant', cost=1, attack=2, health=1, ability=IncreaseAttackAbility(2)),
)


class Card:
    def __init__(self, name: str, cost: int):
        self.name = name
        self.cost = cost
        self.was_played = False

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{0.__class__.__name__}: {0.name}>'.format(self)


class MinionCard(Card):
    def __init__(self, name: str, cost: int, attack: int, health: int, ability: Ability = Ability()):
        super(MinionCard, self).__init__(name, cost)
        self.attack = attack
        self.health = health
        self.can_attack = False
        self._was_played = self.was_played
        self.ability = ability
        self.ability.apply(self, phase_name='init')

    @property
    def was_played(self):
        return self._was_played

    @was_played.setter
    def was_played(self, value):
        self._was_played = value
        if value:
            self.ability.apply(self, phase_name='play')

    def take_attack(self, attacker_card: 'MinionCard'):
        if not attacker_card.can_attack:
            raise CardCannotAttackError('Card {0} cannot attack in current turn'.format(attacker_card))

        attacker_card.can_attack = False
        self.health -= attacker_card.attack
        if self.health <= 0:
            raise DeadCardError('After attacking health is below 0')

    def __repr__(self):
        return '<{0.__class__.__name__}: {0.name} {0.health} HP>'.format(self)


class Deck:
    NUMBER_OF_COPIES = 2
    USED_CARDS = CARDS

    def __init__(self, cards: Iterable[Card]=None):
        if cards is not None:
            self.cards = list(cards)
        else:
            self.cards = [
                MinionCard(**card_info)
                for card_info in self.USED_CARDS * self.NUMBER_OF_COPIES
            ]
            self.shuffle()
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
