import random
from typing import Iterable, List, Union, Optional
from pyheart.exceptions import (
    DeadCardError,
    EmptyDeckError,
    CardCannotAttackError,
    TargetNotDefinedError,
    InvalidTargetError,
    MissingCardError)
from pyheart.mixins import UniqueIdentifierMixin


class Ability:
    def __init__(self, value: int = None, allow_target: bool = False):
        self._val = value
        self.can_target = allow_target

    def apply(self, card: 'Card', phase_name: str, **kwargs):
        phase_method_name = f'_{phase_name}_phase'
        getattr(self, phase_method_name, self.__default_method)(card=card, **kwargs)

    def _discard_target(self, target_id: Optional[str] = None, **kwargs):
        if target_id is not None:
            raise InvalidTargetError('Card cannot target other cards')

    def __default_method(self, **kwargs):
        pass

    def __eq__(self, other: 'Ability') -> bool:
        return self.__class__ == other.__class__ and self._val == other._val

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._val)


class ChargeAbility(Ability):
    def _init_phase(self, card: 'MinionCard', **kwargs):
        self._discard_target(**kwargs)
        card.can_attack = True


class IncreaseDamageAbility(Ability):
    def _play_phase(self, card: 'MinionCard', **kwargs):
        self._discard_target(**kwargs)
        card.damage += self._val


class IncreaseMinonsHealthAbility(Ability):
    def _play_phase(self, board: 'Board', player: 'Player', **kwargs):
        self._discard_target(**kwargs)
        for card in board.played_cards(player):
            card.health += self._val


class SetMinonHealthAndDamage(Ability):
    def _play_phase(self, board: 'Board', player: 'Player', card: 'Card', target_id: Optional[str], **kwargs):
        if target_id is None:
            raise TargetNotDefinedError('You have to pass target, to play {0}'.format(card))

        target = board.get_card(target_id, player)
        target.health = self._val
        target.damage = self._val


class DealDamage(Ability):
    def _init_phase(self, card: 'AbilityCard', **kwargs):
        card.damage = self._val

    def _play_phase(self, card: 'AbilityCard', board: 'Board', player: 'Player', target_id: Optional[str], **kwargs):
        if self.can_target:
            try:
                board.get_card(target_id, player)
                raise InvalidTargetError('Card must target enemy card')
            except MissingCardError:
                card.can_attack = True
                board.attack(card, target_id)
        else:
            self._discard_target(target_id)
            for victim in board.enemy_cards(player):
                board.attack(card, victim.id)


class Card(UniqueIdentifierMixin):
    def __init__(self, name: str, cost: int, ability: Ability):
        super(Card, self).__init__()
        self.name = name
        self.cost = cost
        self._was_played = False
        self.ability = ability
        self.ability.apply(self, phase_name='init')
        self.type = ''

    def play(self, **kwargs):
        if not self._was_played:
            self.ability.apply(self, phase_name='play', **kwargs)
            self._was_played = True

    def __str__(self) -> str:
        return '{0.name} ({0.id}) {0.type}'.format(self)

    def __repr__(self) -> str:
        return '<{0.__class__.__name__}: {0.name}>'.format(self)


class AbilityCard(Card):
    def __init__(self, name: str, cost: int, ability: Ability):
        self.damage = 0  # ability can change it during init phase
        super(AbilityCard, self).__init__(name, cost, ability)
        self.type = 'spell'

    def attack(self, victim: Union['MinionCard', 'Player']) -> List['MinionCard']:
        try:
            victim.health -= self.damage
        except DeadCardError:
            return [victim]
        return []


class MinionCard(Card):
    def __init__(self, name: str, cost: int, attack: int, health: int, ability: Ability = Ability()):
        self.damage = attack
        self._health = health
        self.can_attack = False
        super(MinionCard, self).__init__(name, cost, ability)
        self.type = 'minon'

    def play(self, player: 'Player', board: 'Board', target_id: Optional[str], **kwargs):
        if not self.ability.can_target and target_id is not None:
            raise InvalidTargetError('Minion card cannot target other cards')

        board.play_card(player=player, card=self)
        super(MinionCard, self).play(player=player, board=board, target_id=target_id, **kwargs)

    @property
    def health(self):
        return self._health

    @health.setter
    def health(self, value):
        self._health = max(0, value)
        if value <= 0:
            raise DeadCardError('After attacking health is below 0')

    def attack(self, victim: Union['MinionCard', 'Player']) -> List['MinionCard']:
        if not self.can_attack:
            raise CardCannotAttackError('Card {0} cannot attack in current turn'.format(self))

        self.can_attack = False
        dead_cards = []
        try:
            victim.health -= self.damage
        except DeadCardError:
            dead_cards.append(victim)

        try:
            self.health -= getattr(victim, 'damage', 0)
        except DeadCardError:
            dead_cards.append(self)

        return dead_cards

    def __repr__(self):
        return '<{0.__class__.__name__}: {0.name} {0.health} HP>'.format(self)


class Deck:
    def __init__(self, cards: Iterable[Card]):
        self._all_cards = {c.id: c for c in cards}
        self.cards = self.all_cards
        self.empty_card = 0

    @property
    def all_cards(self) -> List[Card]:
        return list(self._all_cards.values())

    def card_by_id(self, id: str) -> Card:
        return self._all_cards[id]

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, number: int = 1)->Iterable[Card]:
        next_cards = self.cards[:number]
        self.cards = self.cards[number:]
        difference = number - len(next_cards)
        if difference > 0:
            self.empty_card += difference
            raise EmptyDeckError(self.empty_card)
        return next_cards

    def remove(self, card: Card):
        self.cards.remove(card)

    def __len__(self):
        return len(self.cards)

    def __eq__(self, other: 'Deck') -> bool:
        return self.__class__ == other.__class__ and self.cards == other.cards and self.empty_card == other.empty_card

    def __repr__(self):
        return '<{0.__class__.__name__} available cards: {1}>'.format(self, len(self))


class DefaultDeck(Deck):
    CARDS = (
        # https://www.hearthpwn.com/cards/76996-dire-mole
        dict(name='Dire Mole', cost=1, attack=1, health=3),
        # https://www.hearthpwn.com/cards/535-river-crocolisk
        dict(name='River Crocolisk', cost=2, attack=2, health=3),
        # https://www.hearthpwn.com/cards/362-magma-rager
        dict(name='Magma Rager', cost=3, attack=5, health=1),
        # https://www.hearthpwn.com/cards/31-chillwind-yeti
        dict(name='Chillwind Yeti', cost=4, attack=4, health=5),
        # https://www.hearthpwn.com/cards/325-stormpike-commando
        dict(name='Stormpike Commando', cost=5, attack=4, health=2, ability=DealDamage(2, allow_target=True)),
        # https://www.hearthpwn.com/cards/60-boulderfist-ogre
        dict(name='Boulderfist Ogre', cost=6, attack=6, health=7),
        # https://www.hearthpwn.com/cards/44-flamestrike
        dict(name='Flamestrike', cost=7, ability=DealDamage(4)),
        # https://www.hearthpwn.com/cards/55455-dinosize
        dict(name='Dinosize', cost=8, ability=SetMinonHealthAndDamage(10)),
        # https://www.hearthpwn.com/cards/194-king-krush
        dict(name='King Krush', cost=9, attack=8, health=8, ability=ChargeAbility()),
        # https://www.hearthpwn.com/cards/49823-goldthorn
        dict(name='Goldthorn', cost=10, ability=IncreaseMinonsHealthAbility(6)),

    )

    NUMBER_OF_COPIES = 2

    def __init__(self):
        cards = [
            self._construct_card(card_info)
            for card_info in self.CARDS * self.NUMBER_OF_COPIES
        ]
        super(DefaultDeck, self).__init__(cards)
        self.shuffle()

    @staticmethod
    def _construct_card(card_info):
        if not all(key in card_info for key in ['attack', 'health']):
            return AbilityCard(**card_info)
        return MinionCard(**card_info)
