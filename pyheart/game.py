from collections import defaultdict
from itertools import chain, cycle
from typing import Iterable

from pyheart.cards import Deck, Card
from pyheart.exceptions import DeadPlayerError, EmptyDeckError, TooManyCardsError, MissingCardError, NotEnoughManaError


class PlayersHand:
    def __init__(self, number_of_cards: int, deck: Deck=None):
        self.deck = deck or Deck()
        self.cards = self.deck.deal(number_of_cards)

    def __contains__(self, card: Card):
        return card in self.cards

    def take_card(self):
        self.cards.append(self.deck.deal())

    def discard(self, card: Card):
        self.cards.remove(card)

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return '<{0.__class__.__name__} cards in hand: {1}, cards in deck {2}>'.format(self, len(self), len(self.deck))

    def __bool__(self):
        return True


class Player:
    HEALTH_LEVEL = 20
    NUMBERS_OF_START_CARDS = (3, 4)
    MAX_MANA_LEVEL = 10

    def __init__(self, name: str, is_first: bool=False, hand: PlayersHand=None, health: int=None, mana: int=None):
        self.name = name
        self.health = health or self.HEALTH_LEVEL
        self.mana = mana or 0
        self.turn = 0
        start_cards_first, start_cards_second = self.NUMBERS_OF_START_CARDS
        self.hand = hand or PlayersHand(start_cards_first if is_first else start_cards_second)

    def play(self, card: Card):
        if card not in self.hand:
            raise MissingCardError("Card {0} is not in player's hand".format(card))

        if card.cost > self.mana:
            raise NotEnoughManaError(
                "Card {0} cost [{0.cost}] is bigger than available player's mana [{1.mana}]".format(card, self)
            )

        self.mana -= card.cost
        self.hand.discard(card)

    def start_turn(self):
        self.turn += 1
        self.mana = min(self.turn, self.MAX_MANA_LEVEL)
        try:
            self.hand.take_card()
        except EmptyDeckError as e:
            new_health = self.health - e.deal_attempt
            if new_health <= 0:
                self.health = 0
                raise DeadPlayerError("Player's health reaches 0 [{0}]".format(new_health))
            self.health = new_health

    def __repr__(self):
        return '<{0.__class__.__name__} {0.name} mana: {0.mana}, health: {0.health}>'.format(self)


class Board:
    MAX_CARDS_PER_PLAYER = 7

    def __init__(self, cards: Iterable[Card]=None):
        self.played_cards = defaultdict(set)  # TODO: Change to list, players can have multiple same cards
        if cards:
            self.played_cards.update(cards)

    def play_card(self, player: Player, card: Card):
        played_cards = self.played_cards[player]
        if len(played_cards) >= self.MAX_CARDS_PER_PLAYER:
            raise TooManyCardsError('Player can have only {0} cards on board'.format(self.MAX_CARDS_PER_PLAYER))

        player.play(card)
        played_cards.add(card)

    def cards(self, player: Player=None):
        if player:
            return self.played_cards[player]

        all_cards = set(chain(*self.played_cards.values()))
        return all_cards

    def __len__(self):
        return len(self.cards())


class Game:
    def __init__(self, players: Iterable[Player]=(), board: Board=None):
        self.players = list(players) or [Player(name='1', is_first=True), Player(name='2')]
        self._player_order = cycle(self.players)
        self.current_player = None
        self.board = board or Board()
        self._game_started = False

    def start(self):
        if not self._game_started:
            self._game_started = True
            self.end_turn()

    def end_turn(self):
        if self._game_started:
            self.current_player = next(self._player_order)
            self.current_player.start_turn()

    def play(self, player: Player, card: Card):
        self.board.play_card(player, card)
