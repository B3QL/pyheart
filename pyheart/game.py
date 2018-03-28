from copy import deepcopy
from typing import Iterable, Union, List, Optional
from collections import defaultdict

from pyheart.cards import Deck, DefaultDeck, Card, MinionCard
from pyheart.mixins import UniqueIdentifierMixin
from pyheart.exceptions import (
    DeadPlayerError,
    EmptyDeckError,
    GameNotStartedError,
    InvalidPlayerTurnError,
    TooManyCardsError,
    MissingCardError,
    NotEnoughManaError,
)


class Player(UniqueIdentifierMixin):
    HEALTH_LEVEL = 20
    MAX_MANA_LEVEL = 10

    def __init__(self, name: str, cards_number: int, deck: Deck, board: 'Board'):
        super(Player, self).__init__()
        self.name = name
        self._health = self.HEALTH_LEVEL
        self._current_mana = 0
        self.used_mana = 0
        self.deck = deck
        self._hand = {card.id: card for card in deck.deal(cards_number)}
        self._board = board

    @property
    def hand(self) -> List[Card]:
        return list(self._hand.values())

    @hand.setter
    def hand(self, cards: List[Card]):
        self._hand = {card.id: card for card in cards}

    @property
    def health(self) -> int:
        return self._health

    @health.setter
    def health(self, new_health: int):
        if new_health <= 0:
            self._health = 0
            raise DeadPlayerError("{0} health reaches 0 [{1}]".format(self, new_health))
        self._health = new_health

    @property
    def mana(self) -> int:
        return self._current_mana - self.used_mana

    @mana.setter
    def mana(self, value: int):
        self._current_mana = value

    @property
    def current_mana(self) -> int:
        return self._current_mana

    @current_mana.setter
    def current_mana(self, value: int):
        self._current_mana = min(value, self.MAX_MANA_LEVEL)

    def play(self, card_id: str, target_id: Optional[str]):
        if card_id not in self._hand:
            raise MissingCardError("Card {0} is not in player's hand".format(card_id))

        card = self._hand[card_id]
        if card.cost > self.mana:
            raise NotEnoughManaError(
                "Card {0} cost [{0.cost}] is bigger than available player's mana [{1.mana}]".format(card, self)
            )
        card.play(player=self, board=self._board, target_id=target_id)
        self.used_mana += card.cost
        del self._hand[card.id]

    def attack(self, attacker_id: str, victim: Union['Player', str]):
        attacker = self._board.get_card(attacker_id, player=self)
        self._board.attack(attacker, victim)

    def take_cards(self, number: int):
        try:
            new_cards = {card.id: card for card in self.deck.deal(number)}
            self._hand.update(new_cards)
        except EmptyDeckError as e:
            self.health -= e.deal_attempt

    def __repr__(self) -> str:
        return '<{0.__class__.__name__} {0.name} mana: {0.mana}, health: {0.health}>'.format(self)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: 'Player') -> bool:
        attrs = ['__class__', 'name', 'health', 'mana', 'current_mana', 'hand', 'deck']
        return all(getattr(self, a) == getattr(other, a) for a in attrs)


class Board:
    MAX_CARDS_PER_PLAYER = 7

    def __init__(self):
        self._player_cards = defaultdict(set)
        self._cards = {}

    def reset_cards(self, player: Player):
        player_cards = self._player_cards[player.id]
        for card_id in player_cards:
            self._cards[card_id].can_attack = True

    def play_card(self, player: Player, card: Card):
        played_cards = self.played_cards(player)
        if len(played_cards) >= self.MAX_CARDS_PER_PLAYER:
            raise TooManyCardsError('Player can have only {0} cards on board'.format(self.MAX_CARDS_PER_PLAYER))
        self._add_card(player, card)

    def attack(self, attacker: MinionCard, victim: Union[str, Player]):
        try:
            victim = self._cards[victim]
        except KeyError:
            raise MissingCardError('{0} cannot attack not played {1} card'.format(attacker, victim))
        except TypeError:
            pass  # victim is an unhashable Player

        for dead_card in attacker.attack(victim):
            self._remove_card(dead_card)

    def played_cards(self, player: Union[Player, str]=None) -> List[MinionCard]:
        if player:
            player_id = getattr(player, 'id', player)
            player_cards = self._player_cards[player_id]
            return list(map(lambda card_id: self._cards[card_id], player_cards))
        return list(self._cards.values())

    def enemy_cards(self, player: Player) -> List[MinionCard]:
        all_players = set(self._player_cards.keys())
        enemy_player_id = all_players - {player.id}
        return self.played_cards(enemy_player_id.pop())

    def get_card(self, card_id: str, player: Player) -> MinionCard:
        try:
            if card_id not in self._player_cards[player.id]:
                raise KeyError

            return self._cards[card_id]
        except KeyError:
            raise MissingCardError('Card {0} not played'.format(self, card_id))

    def _add_card(self, player: Player, card: Card):
        self._player_cards[player.id].add(card.id)
        self._cards[card.id] = card

    def _remove_card(self, card: Card):
        del self._cards[card.id]

        # We can remove card from all players because id is globally unique
        for player_cards in self._player_cards.values():
            player_cards.discard(card.id)

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
            Player(name, start_cards, deck, self.board)
            for name, start_cards, deck in zip(player_names, self.NUMBERS_OF_START_CARDS, player_decks)
        ]
        self._turn = 0
        self._game_started = False

    def _calculate_turn(self, turn):
        players_number = len(self.players)
        return self.players[turn % players_number]

    @property
    def turn(self):
        return max(self._turn, 1)

    @property
    def current_player(self):
        return self._calculate_turn(self.turn - 1)

    @property
    def next_player(self):
        return self._calculate_turn(self.turn)

    def start(self):
        if not self._game_started:
            self._game_started = True
            self.endturn(self.current_player)

    def endturn(self, player: Player):
        self._check_state(player)
        self._turn += 1
        self.board.reset_cards(self.current_player)
        self._reset_player(self.current_player)

    @staticmethod
    def _reset_player(player: Player):
        player.current_mana += 1
        player.used_mana = 0
        player.take_cards(1)

    def _check_state(self, player: Player):
        if not self._game_started:
            raise GameNotStartedError('Action allowed only after game start')

        if player != self.current_player:
            raise InvalidPlayerTurnError('Player {0.name} cannot play card in this turn')

    def attack(self, player: Player, attacker: MinionCard, victim: Union[MinionCard, Player]):
        self._check_state(player)

        victim = victim.id
        players = {player.id: player for player in self.players}
        if victim in players:
            victim = players[victim]

        self.current_player.attack(attacker.id, victim)

    def play(self, player: Player, card: Card, target: MinionCard = None):
        self._check_state(player)
        self.current_player.play(card.id, getattr(target, 'id', None))

    def copy(self) -> 'Game':
        return deepcopy(self)
