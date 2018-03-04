import pytest

from pyheart import Game, Player, PlayersHand
from pyheart.cards import Deck, MinionCard
from pyheart.exceptions import (
    DeadPlayerError,
    InvalidPlayerTurnError,
    MissingCardError,
    NotEnoughManaError,
    TooManyCardsError,
    CardCannotAttackError
)


@pytest.fixture()
def deck():
    used_cards = Deck.USED_CARDS
    cards_num = Deck.NUMBER_OF_COPIES
    yield Deck
    Deck.USED_CARDS = used_cards
    Deck.NUMBER_OF_COPIES = cards_num


def test_create_new_game():
    game = Game()
    assert len(game.players) == 2
    assert len(game.board) == 0

    first_player, second_player = game.players
    assert first_player.health == 20
    assert second_player.health == 20
    assert len(first_player.hand) == 3
    assert len(second_player.hand) == 4


def test_play_card_to_board():
    card = MinionCard('test', cost=5, attack=1, health=1)
    deck = Deck([card])
    hand = PlayersHand(1, deck)
    player = Player(name='test', hand=hand, mana=10)
    game = Game(players=[player])
    game.start()
    game.play(player, card)
    assert len(game.board) == 1
    assert card in game.board.played_cards(player)
    assert card not in player.hand
    assert player.mana == 5


def test_not_enough_mana_to_play_card():
    card = MinionCard('test', cost=1000, attack=1, health=1)
    deck = Deck([card])
    hand = PlayersHand(1, deck)
    player = Player(name='test', hand=hand)
    game = Game(players=[player])
    game.start()

    with pytest.raises(NotEnoughManaError):
        game.play(player, card)

    assert len(game.board) == 0
    assert card not in game.board.played_cards(player)
    assert card in player.hand


def test_card_played_but_not_in_hand():
    card = MinionCard('test', cost=1, attack=1, health=1)
    other_card = MinionCard('other', cost=1, attack=1, health=1)
    deck = Deck([card, other_card])
    hand = PlayersHand(0, deck)
    player = Player(name='test', hand=hand)
    game = Game(players=[player])
    game.start()

    with pytest.raises(MissingCardError):
        game.play(player, other_card)

    assert len(game.board) == 0
    assert card not in game.board.played_cards(player)


def test_switch_players_after_turn_end():
    game = Game()
    first_player, second_player = game.players

    assert game.current_player is None
    game.start()

    assert game.current_player == first_player
    game.end_turn()
    assert game.current_player == second_player
    game.end_turn()
    assert game.current_player == first_player


def test_player_deal_new_card_in_turn_start():
    deck = Deck(MinionCard('test', cost=1, attack=1, health=1) for _ in range(20))
    first_player_hand = PlayersHand(1, deck)
    second_player_hand = PlayersHand(1, deck)
    first_player = Player(name='test', hand=first_player_hand)
    second_player = Player(name='test 2', hand=second_player_hand)
    game = Game(players=[first_player, second_player])

    assert len(first_player.hand) == 1
    assert len(second_player.hand) == 1
    game.start()
    assert len(first_player.hand) == 2
    assert len(second_player.hand) == 1
    game.end_turn()
    assert len(first_player.hand) == 2
    assert len(second_player.hand) == 2
    game.end_turn()
    assert len(first_player.hand) == 3
    assert len(second_player.hand) == 2
    game.end_turn()
    assert len(first_player.hand) == 3
    assert len(second_player.hand) == 3


def test_fill_players_mana():
    game = Game()
    first_player, second_player = game.players

    assert first_player.mana == 0
    assert second_player.mana == 0
    game.start()
    assert first_player.mana == 1
    assert second_player.mana == 0
    game.end_turn()
    assert first_player.mana == 1
    assert second_player.mana == 1
    game.end_turn()
    assert first_player.mana == 2
    assert second_player.mana == 1


def test_max_mana_not_above_10():
    deck = Deck(MinionCard('test', cost=1, attack=1, health=1) for _ in range(50))
    hand = PlayersHand(number_of_cards=0, deck=deck)
    player = Player(name='test', hand=hand)
    game = Game(players=[player])
    game.start()
    turns = range(20)
    for _ in turns:
        game.end_turn()

    assert player.mana == 10


def test_player_no_available_cards():
    empty_deck = Deck([])
    hand = PlayersHand(number_of_cards=0, deck=empty_deck)
    start_health = 5
    player = Player(name='test', hand=hand, health=start_health)
    game = Game(players=[player])
    assert player.health == start_health
    game.start()
    assert player.health == start_health - 1
    game.end_turn()
    assert player.health == start_health - 3
    with pytest.raises(DeadPlayerError):
        game.end_turn()
    assert player.health == 0


def test_to_many_minions_on_board():
    deck = Deck(MinionCard('test', cost=1, attack=1, health=1) for _ in range(50))
    hand = PlayersHand(number_of_cards=6, deck=deck)
    player = Player(name='test', hand=hand, mana=100)
    game = Game(players=[player])
    game.start()

    assert len(game.board.played_cards(player)) == 0
    for card in player.hand:
        game.play(player, card)
    assert len(game.board.played_cards(player)) == 7
    game.end_turn()
    card = player.hand[0]

    with pytest.raises(TooManyCardsError):
        game.play(player, card)


def test_player_cannot_do_action_until_its_turn():
    game = Game()
    first_player, second_player = game.players
    game.start()
    card = second_player.hand[0]

    with pytest.raises(InvalidPlayerTurnError):
        game.play(second_player, card)


def test_only_played_minion_can_attack():
    game = Game()
    first_player, second_player = game.players
    game.start()

    first_player_card = first_player.hand[0]
    game.play(first_player, first_player_card)
    game.end_turn()

    second_player_card = second_player.hand[0]
    with pytest.raises(MissingCardError):
        game.attack(second_player, second_player_card, first_player_card)


def test_player_cannot_attack_without_turn():
    game = Game()
    first_player, second_player = game.players
    game.start()

    first_player_card = first_player.hand[0]
    game.play(first_player, first_player_card)
    game.end_turn()

    second_player_card = second_player.hand[0]
    game.play(second_player, second_player_card)

    with pytest.raises(InvalidPlayerTurnError):
        game.attack(first_player, first_player_card, second_player_card)


def test_simple_minion_attack(deck):
    deck.USED_CARDS = (
        dict(name='test', cost=1, attack=1, health=2),
    )
    deck.NUMBER_OF_COPIES = 10
    game = Game()
    first_player, second_player = game.players

    game.start()

    first_player_card = first_player.hand[0]
    game.play(first_player, first_player_card)
    game.end_turn()

    second_player_card = second_player.hand[0]
    game.play(second_player, second_player_card)
    game.end_turn()

    game.attack(first_player, first_player_card, second_player_card)

    assert first_player_card.health == 1
    assert second_player_card.health == 1
    assert len(game.board) == 2


def test_minion_removed_from_board_after_die(deck):
    deck.USED_CARDS = (
        dict(name='test', cost=1, attack=10, health=2),
    )
    game = Game()
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    game.end_turn()

    assert len(game.board) == 2
    game.attack(first_player, first_player_card, second_player_card)
    assert len(game.board) == 0


def test_simple_minion_cannot_attack_in_played_turn():
    game = Game()
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    with pytest.raises(CardCannotAttackError):
        game.attack(second_player, second_player_card, first_player_card)


def test_minon_cannot_attack_twice(deck):
    deck.USED_CARDS = (
        dict(name='test', cost=1, attack=1, health=2),
    )
    game = Game()
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    game.end_turn()

    game.attack(first_player, first_player_card, second_player_card)
    with pytest.raises(CardCannotAttackError):
        game.attack(first_player, first_player_card, second_player_card)


def test_attack_player(deck):
    deck.USED_CARDS = (
        dict(name='test', cost=1, attack=10, health=2),
    )
    deck.NUMBER_OF_COPIES = 10
    game = Game()
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    game.end_turn()

    assert second_player.health == 20
    game.attack_player(first_player, first_player_card, second_player)
    assert second_player.health == 10

