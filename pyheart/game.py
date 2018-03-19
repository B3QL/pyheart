from collections import defaultdict
from itertools import chain
from typing import Dict, Iterable, Sequence

from pyheart.cards import Deck, DefaultDeck, Card, MinionCard
from pyheart.exceptions import (
    DeadPlayerError,
    EmptyDeckError,
    DeadCardError,
    GameNotStartedError,
    InvalidPlayerTurnError,
    TooManyCardsError,
    MissingCardError,
    NotEnoughManaError,
    CardCannotAttackError
)


class Player:
    HEALTH_LEVEL = 20
    MAX_MANA_LEVEL = 10

    def __init__(self, name: str, cards_number: int, deck: Deck):
        self.name = name
        self._health = self.HEALTH_LEVEL
        self.current_mana = 0
        self.used_mana = 0
        self.turn = 0
        self.deck = deck
        self._hand = list(deck.deal(cards_number))

    @property
    def hand(self):
        return list(self._hand)

    @hand.setter
    def hand(self, value):
        self._hand = value

    @property
    def health(self):
        return self._health

    @health.setter
    def health(self, new_health):
        if new_health <= 0:
            self._health = 0
            raise DeadPlayerError("Player's health reaches 0 [{0}]".format(new_health))
        self._health = new_health

    @property
    def mana(self):
        return self.current_mana - self.used_mana

    @mana.setter
    def mana(self, value):
        self.current_mana = value

    def play(self, card: Card):
        if card not in self._hand:
            raise MissingCardError("Card {0} is not in player's hand".format(card))

        if card.cost > self.mana:
            raise NotEnoughManaError(
                "Card {0} cost [{0.cost}] is bigger than available player's mana [{1.mana}]".format(card, self)
            )

        self.used_mana += card.cost
        self._hand.remove(card)
        card.was_played = True

    def take_attack(self, attacker_card: MinionCard):
        if not attacker_card.can_attack:
            raise CardCannotAttackError('Card {0} cannot attack in current turn'.format(attacker_card))

        attacker_card.can_attack = False
        self.health -= attacker_card.attack

    def start_turn(self):
        self.turn += 1
        self.current_mana = max(min(self.turn, self.MAX_MANA_LEVEL), self.current_mana)
        self.used_mana = 0
        self.take_cards(1)

    def take_cards(self, number):
        try:
            new_card = self.deck.deal(number)
            self._hand.extend(new_card)
        except EmptyDeckError as e:
            self.health -= e.deal_attempt

    def __repr__(self):
        return '<{0.__class__.__name__} {0.name} mana: {0.mana}, health: {0.health}>'.format(self)


class Board:
    MAX_CARDS_PER_PLAYER = 7

    def __init__(self, cards: Dict[Player, Sequence[Card]]=None):
        self._played_cards = defaultdict(set)
        if cards:
            self._played_cards.update(cards)

    def activate_cards(self, player: Player):
        for card in self.played_cards(player):
            card.can_attack = True

    def play_card(self, player: Player, card: Card):
        played_cards = self._played_cards[player]
        if len(played_cards) >= self.MAX_CARDS_PER_PLAYER:
            raise TooManyCardsError('Player can have only {0} cards on board'.format(self.MAX_CARDS_PER_PLAYER))

        player.play(card)
        played_cards.add(card)

    def attack_card(self, attacker: Player, attack_card: MinionCard, victim: Player, victim_card: MinionCard):
        if attack_card not in self.played_cards(attacker):
            raise MissingCardError('Player {0} cannot attack with not played {1} card'.format(attacker, attack_card))

        if victim_card not in self.played_cards(victim):
            raise MissingCardError('Player {0} cannot attack not played card'.format(attacker))

        try:
            victim_card.take_attack(attack_card)
        except DeadCardError:
            self.played_cards(victim).remove(victim_card)

        try:
            attack_card.take_attack(victim_card)
        except DeadCardError:
            self.played_cards(attacker).remove(attack_card)

    def played_cards(self, player: Player=None):
        if player:
            return self._played_cards[player]

        all_cards = set(chain(*self._played_cards.values()))
        return all_cards

    def __len__(self):
        return len(self.played_cards())


class Game:
    NUMBERS_OF_START_CARDS = (3, 4)
    DEFAULT_PLAYER_NAMES = ('Player 1', 'Player 2')

    def __init__(self, player_names: Iterable[str] = DEFAULT_PLAYER_NAMES, player_decks: Iterable[Deck] = None):
        self.board = Board()
        if player_decks is None:
            player_decks = [DefaultDeck() for _ in player_names]

        self.players = [
            Player(name, start_cards, deck)
            for name, start_cards, deck in zip(player_names, self.NUMBERS_OF_START_CARDS, player_decks)
        ]
        self._turn = -1
        self._game_started = False

    def _calculate_turn(self, turn):
        players_number = len(self.players)
        return self.players[turn % players_number]

    @property
    def current_player(self):
        if self._turn < 0:
            return None
        return self._calculate_turn(self._turn)

    @property
    def next_player(self):
        return self._calculate_turn(self._turn + 1)

    def start(self):
        if not self._game_started:
            self._game_started = True
            self.end_turn()

    def end_turn(self):
        if not self._game_started:
            raise GameNotStartedError('Action allowed only after game start')
        self.board.activate_cards(self.current_player)
        self._turn += 1
        self.current_player.start_turn()

    def _check_state(self, player: Player):
        if not self._game_started:
            raise GameNotStartedError('Action allowed only after game start')

        if player != self.current_player:
            raise InvalidPlayerTurnError('Player {0.name} cannot play card in this turn')

    def attack(self, player: Player, attacker: MinionCard, victim: MinionCard):
        self._check_state(player)
        opponent = self.next_player
        self.board.attack_card(player, attacker, opponent, victim)

    def attack_player(self, player: Player, attacker: MinionCard, victim: Player):
        self._check_state(player)
        if attacker not in self.board.played_cards(player):
            raise MissingCardError('Player {0} cannot attack not played card'.format(attacker))
        victim.take_attack(attacker)

    def play(self, player: Player, card: Card):
        self._check_state(player)
        self.board.play_card(player, card)
