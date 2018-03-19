import pytest

from pyheart import Game
from pyheart.cards import Deck, MinionCard, ChargeAbility, IncreaseAttackAbility
from pyheart.exceptions import (
    DeadPlayerError,
    InvalidPlayerTurnError,
    MissingCardError,
    NotEnoughManaError,
    TooManyCardsError,
    CardCannotAttackError
)


@pytest.fixture()
def game():
    start_cards = Game.NUMBERS_OF_START_CARDS
    yield Game
    Game.NUMBERS_OF_START_CARDS = start_cards


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
    card = MinionCard(name='test', cost=1, attack=1, health=1)
    deck = Deck([card])
    game = Game(player_decks=[deck])
    player, = game.players

    game.start()
    assert player.mana == 1
    game.play(player, card)
    assert len(game.board) == 1
    assert card in game.board.played_cards(player)
    assert card not in player.hand
    assert player.mana == 0


def test_not_enough_mana_to_play_card():
    card = MinionCard('test', cost=1000, attack=1, health=1)
    deck = Deck([card])
    game = Game(player_decks=[deck])
    player, = game.players
    game.start()

    with pytest.raises(NotEnoughManaError):
        game.play(player, card)

    assert len(game.board) == 0
    assert card not in game.board.played_cards(player)
    assert card in player.hand


def test_card_played_but_not_in_hand():
    card = MinionCard('test', cost=1, attack=1, health=1)
    game = Game()
    player, _ = game.players
    player.hand = []
    game.start()

    with pytest.raises(MissingCardError):
        game.play(player, card)

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
    game = Game()
    first_player, second_player = game.players

    assert len(first_player.hand) == 3
    assert len(second_player.hand) == 4
    game.start()
    assert len(first_player.hand) == 4
    assert len(second_player.hand) == 4
    game.end_turn()
    assert len(first_player.hand) == 4
    assert len(second_player.hand) == 5
    game.end_turn()
    assert len(first_player.hand) == 5
    assert len(second_player.hand) == 5
    game.end_turn()
    assert len(first_player.hand) == 5
    assert len(second_player.hand) == 6


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
    game = Game()
    player, _ = game.players
    game.start()
    turns = range(20)
    for _ in turns:
        game.end_turn()

    assert player.mana == 10


def test_player_no_available_cards(game):
    empty_deck = Deck([])
    game.NUMBERS_OF_START_CARDS = (0, 0)
    g = game(player_decks=[empty_deck])
    player, = g.players
    start_health = 5
    player.health = start_health

    assert player.health == start_health
    g.start()
    assert player.health == start_health - 1
    g.end_turn()
    assert player.health == start_health - 3
    with pytest.raises(DeadPlayerError):
        g.end_turn()
    assert player.health == 0


def test_to_many_minions_on_board(game):
    game.NUMBERS_OF_START_CARDS = (6, 0)
    g = game()
    player, _ = g.players
    player.mana = 200
    g.start()

    assert len(player.hand) == 7
    assert len(g.board.played_cards(player)) == 0
    for card in player.hand:
        g.play(player, card)
    assert len(g.board.played_cards(player)) == 7
    g.end_turn()
    g.end_turn()
    card = player.hand[0]

    with pytest.raises(TooManyCardsError):
        g.play(player, card)


def test_player_cannot_do_action_until_its_turn():
    game = Game()
    first_player, second_player = game.players
    game.start()
    card = second_player.hand[0]

    with pytest.raises(InvalidPlayerTurnError):
        game.play(second_player, card)


def test_only_played_minion_can_attack():
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()

    first_player_card = first_player.hand[0]
    game.play(first_player, first_player_card)
    game.end_turn()

    second_player_card = second_player.hand[0]
    with pytest.raises(MissingCardError):
        game.attack(second_player, second_player_card, first_player_card)


def test_player_cannot_attack_without_turn():
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()

    first_player_card = first_player.hand[0]
    game.play(first_player, first_player_card)
    game.end_turn()

    second_player_card = second_player.hand[0]
    game.play(second_player, second_player_card)

    with pytest.raises(InvalidPlayerTurnError):
        game.attack(first_player, first_player_card, second_player_card)


def test_simple_minion_attack():
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
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


def test_minion_removed_from_board_after_die():
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
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
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    with pytest.raises(CardCannotAttackError):
        game.attack(second_player, second_player_card, first_player_card)


def test_minon_cannot_attack_twice():
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
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


def test_attack_player():
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
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


def test_attack_player_not_in_turn():
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    game.end_turn()

    game.end_turn()
    with pytest.raises(InvalidPlayerTurnError):
        game.attack_player(first_player, first_player_card, second_player)


def test_attack_player_twice_with_same_card():
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
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

    with pytest.raises(CardCannotAttackError):
        game.attack_player(first_player, first_player_card, second_player)

    assert second_player.health == 10


def test_attack_player_not_played_card():
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.end_turn()

    game.play(second_player, second_player_card)
    game.end_turn()

    with pytest.raises(MissingCardError):
        game.attack_player(first_player, first_player_card, second_player)


def test_kill_player():
    deck = Deck(MinionCard(name='test', cost=1, attack=50, health=2) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    game.end_turn()

    assert second_player.health == 20
    with pytest.raises(DeadPlayerError):
        game.attack_player(first_player, first_player_card, second_player)


def test_minion_card_charge_ability_attack_card():
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2, ability=ChargeAbility()) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    game.attack(second_player, second_player_card, first_player_card)


def test_minion_card_charge_ability_attack_player():
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2, ability=ChargeAbility()) for _ in range(10))
    game = Game(player_decks=[deck, deck])
    first_player, second_player = game.players
    game.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    game.play(first_player, first_player_card)
    game.end_turn()

    game.play(second_player, second_player_card)
    game.attack_player(second_player, second_player_card, first_player)


def test_minion_card_increase_attack_ability():
    deck = Deck(
        MinionCard(name='test', cost=1, attack=1, health=2, ability=IncreaseAttackAbility(10)) for _ in range(10)
    )
    game = Game(player_decks=[deck, deck])
    first_player, _ = game.players
    game.start()
    first_player_card = first_player.hand[0]

    assert first_player_card.attack == 1
    game.play(first_player, first_player_card)
    assert first_player_card.attack == 11
