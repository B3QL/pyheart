import pytest
from pyheart.cards import (
    Deck,
    MinionCard,
    ChargeAbility,
    IncreaseDamageAbility,
    AbilityCard,
    IncreaseMinonsHealthAbility,
    SetMinonHealthAndDamage,
    DealDamage)
from pyheart.exceptions import (
    DeadPlayerError,
    InvalidPlayerTurnError,
    MissingCardError,
    NotEnoughManaError,
    TooManyCardsError,
    CardCannotAttackError,
    TargetNotDefinedError
)


def test_create_new_game(game):
    g = game()
    assert len(g.players) == 2
    assert len(g.board) == 0

    first_player, second_player = g.players
    assert first_player.health == 20
    assert second_player.health == 20
    assert len(first_player.hand) == 3
    assert len(second_player.hand) == 4


def test_play_card_to_board(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=1) for _ in range(10))
    g = game(player_decks=[deck])
    player, = g.players
    card = player.hand[0]

    g.start()
    assert player.mana == 1
    g.play(player, card)
    assert len(g.board) == 1
    assert card in g.board.played_cards(player)
    assert card not in player.hand
    assert player.mana == 0


def test_not_enough_mana_to_play_card(game):
    deck = Deck(MinionCard('test', cost=1000, attack=1, health=1) for _ in range(10))
    g = game(player_decks=[deck])
    player, = g.players
    card = player.hand[0]
    g.start()

    with pytest.raises(NotEnoughManaError):
        g.play(player, card)

    assert len(g.board) == 0
    assert card not in g.board.played_cards(player)
    assert card in player.hand


def test_card_played_but_not_in_hand(game):
    card = MinionCard('test', cost=1, attack=1, health=1)
    g = game()
    player, _ = g.players
    player.hand = []
    g.start()

    with pytest.raises(MissingCardError):
        g.play(player, card)

    assert len(g.board) == 0
    assert card not in g.board.played_cards(player)


def test_switch_players_after_turn_end(game):
    g = game()
    first_player, second_player = g.players

    assert g.current_player is None
    g.start()

    assert g.current_player == first_player
    g.end_turn()
    assert g.current_player == second_player
    g.end_turn()
    assert g.current_player == first_player


def test_player_deal_new_card_in_turn_start(game):
    g = game()
    first_player, second_player = g.players

    assert len(first_player.hand) == 3
    assert len(second_player.hand) == 4
    g.start()
    assert len(first_player.hand) == 4
    assert len(second_player.hand) == 4
    g.end_turn()
    assert len(first_player.hand) == 4
    assert len(second_player.hand) == 5
    g.end_turn()
    assert len(first_player.hand) == 5
    assert len(second_player.hand) == 5
    g.end_turn()
    assert len(first_player.hand) == 5
    assert len(second_player.hand) == 6


def test_fill_players_mana(game):
    g = game()
    first_player, second_player = g.players

    assert first_player.mana == 0
    assert second_player.mana == 0
    g.start()
    assert first_player.mana == 1
    assert second_player.mana == 0
    g.end_turn()
    assert first_player.mana == 1
    assert second_player.mana == 1
    g.end_turn()
    assert first_player.mana == 2
    assert second_player.mana == 1


def test_max_mana_not_above_10(game):
    g = game()
    player, _ = g.players
    g.start()
    turns = range(30)
    for _ in turns:
        g.end_turn()

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
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    game.NUMBERS_OF_START_CARDS = (7, 0)
    g = game(player_decks=[deck])
    player, = g.players
    player.mana = 200
    g.start()

    assert len(player.hand) == 8
    assert len(g.board.played_cards(player)) == 0

    last_card, *rest_cards = player.hand
    for card in rest_cards:
        g.play(player, card)

    assert len(g.board.played_cards(player)) == 7
    with pytest.raises(TooManyCardsError):
        g.play(player, last_card)


def test_player_cannot_do_action_until_its_turn(game):
    g = game()
    first_player, second_player = g.players
    g.start()
    card = second_player.hand[0]

    with pytest.raises(InvalidPlayerTurnError):
        g.play(second_player, card)


def test_only_played_minion_can_attack(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()

    first_player_card = first_player.hand[0]
    g.play(first_player, first_player_card)
    g.end_turn()

    second_player_card = second_player.hand[0]
    with pytest.raises(MissingCardError):
        g.attack(second_player, second_player_card, first_player_card)


def test_player_cannot_attack_without_turn(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()

    first_player_card = first_player.hand[0]
    g.play(first_player, first_player_card)
    g.end_turn()

    second_player_card = second_player.hand[0]
    g.play(second_player, second_player_card)

    with pytest.raises(InvalidPlayerTurnError):
        g.attack(first_player, first_player_card, second_player_card)


def test_simple_minion_attack(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players

    g.start()

    first_player_card = first_player.hand[0]
    g.play(first_player, first_player_card)
    g.end_turn()

    second_player_card = second_player.hand[0]
    g.play(second_player, second_player_card)
    g.end_turn()

    g.attack(first_player, first_player_card, second_player_card)

    assert first_player_card.health == 1
    assert second_player_card.health == 1
    assert len(g.board) == 2


def test_minion_removed_from_board_after_die(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.end_turn()

    assert len(g.board) == 2
    g.attack(first_player, first_player_card, second_player_card)
    assert len(g.board) == 0


def test_simple_minion_cannot_attack_in_played_turn(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    with pytest.raises(CardCannotAttackError):
        g.attack(second_player, second_player_card, first_player_card)


def test_minon_cannot_attack_twice(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.end_turn()

    g.attack(first_player, first_player_card, second_player_card)
    with pytest.raises(CardCannotAttackError):
        g.attack(first_player, first_player_card, second_player_card)


def test_attack_player(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.end_turn()

    assert second_player.health == 20
    g.attack(first_player, first_player_card, second_player)
    assert second_player.health == 10


def test_attack_player_not_in_turn(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.end_turn()

    g.end_turn()
    with pytest.raises(InvalidPlayerTurnError):
        g.attack(first_player, first_player_card, second_player)


def test_attack_player_twice_with_same_card(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.end_turn()

    assert second_player.health == 20
    g.attack(first_player, first_player_card, second_player)
    assert second_player.health == 10

    with pytest.raises(CardCannotAttackError):
        g.attack(first_player, first_player_card, second_player)

    assert second_player.health == 10


def test_attack_player_not_played_card(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=1, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.end_turn()

    g.play(second_player, second_player_card)
    g.end_turn()

    with pytest.raises(MissingCardError):
        g.attack(first_player, first_player_card, second_player)


def test_kill_player(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=50, health=2) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.end_turn()

    assert second_player.health == 20
    with pytest.raises(DeadPlayerError):
        g.attack(first_player, first_player_card, second_player)


def test_minion_card_charge_ability_attack_card(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2, ability=ChargeAbility()) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.attack(second_player, second_player_card, first_player_card)


def test_minion_card_charge_ability_attack_player(game):
    deck = Deck(MinionCard(name='test', cost=1, attack=10, health=2, ability=ChargeAbility()) for _ in range(10))
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    first_player_card = first_player.hand[0]
    second_player_card = second_player.hand[0]

    g.play(first_player, first_player_card)
    g.end_turn()

    g.play(second_player, second_player_card)
    g.attack(second_player, second_player_card, first_player)


def test_minion_card_increase_attack_ability(game):
    deck = Deck(
        MinionCard(name='test', cost=1, attack=1, health=2, ability=IncreaseDamageAbility(10)) for _ in range(10)
    )
    g = game(player_decks=[deck, deck])
    first_player, _ = g.players
    g.start()
    first_player_card = first_player.hand[0]

    assert first_player_card.damage == 1
    g.play(first_player, first_player_card)
    assert first_player_card.damage == 11


def test_increase_minions_health_spell(game):
    deck = Deck([
        MinionCard(name='minon 1', cost=0, attack=50, health=2),
        MinionCard(name='minon 2', cost=0, attack=50, health=2),
        AbilityCard(name='spell', cost=1, ability=IncreaseMinonsHealthAbility(10)),
    ])
    g = game(player_decks=[deck])

    first_player, = g.players
    g.start()
    first_player_card, first_player_card_2, first_player_card_3 = first_player.hand
    g.play(first_player, first_player_card)
    g.play(first_player, first_player_card_2)

    assert first_player_card.health == 2
    assert first_player_card_2.health == 2
    g.play(first_player, first_player_card_3)
    assert first_player_card.health == 12
    assert first_player_card_2.health == 12


def test_increase_health_and_damage_spell(game):
    deck = Deck([
        MinionCard(name='minon 1', cost=0, attack=50, health=2),
        MinionCard(name='minon 2', cost=0, attack=50, health=2),
        AbilityCard(name='spell', cost=1, ability=SetMinonHealthAndDamage(10)),
    ])
    g = game(player_decks=[deck])

    first_player, = g.players
    g.start()
    first_player_card, first_player_card_2, first_player_card_3 = first_player.hand
    g.play(first_player, first_player_card)
    g.play(first_player, first_player_card_2)

    assert first_player_card.health == 2
    assert first_player_card.damage == 50
    assert first_player_card_2.health == 2
    assert first_player_card_2.damage == 50
    g.play(first_player, first_player_card_3, first_player_card)
    assert first_player_card.health == 10
    assert first_player_card.damage == 10
    assert first_player_card_2.health == 2
    assert first_player_card_2.damage == 50


def test_increase_health_and_damage_spell_no_target(game):
    deck = Deck([
        MinionCard(name='minon 1', cost=0, attack=50, health=2),
        MinionCard(name='minon 2', cost=0, attack=50, health=2),
        AbilityCard(name='spell', cost=1, ability=SetMinonHealthAndDamage(10)),
    ])
    g = game(player_decks=[deck])

    first_player, = g.players
    g.start()
    first_player_card, first_player_card_2, first_player_card_3 = first_player.hand
    g.play(first_player, first_player_card)
    g.play(first_player, first_player_card_2)

    assert len(g.board.played_cards()) == 2
    assert len(first_player.hand) == 1
    with pytest.raises(TargetNotDefinedError):
        g.play(first_player, first_player_card_3)
    assert len(g.board.played_cards()) == 2
    assert len(first_player.hand) == 1


def test_deal_damage_spell(game):
    game.NUMBERS_OF_START_CARDS = (1, 0)
    deck = Deck([
        MinionCard(name='minon 1', cost=0, attack=50, health=2),
        MinionCard(name='minon 2', cost=0, attack=50, health=12),
        AbilityCard(name='spell', cost=1, ability=DealDamage(10)),
    ])
    g = game(player_decks=[deck, deck])

    first_player, second_player = g.players
    g.start()
    first_player_card, first_player_card_2 = first_player.hand
    g.play(first_player, first_player_card)
    g.play(first_player, first_player_card_2)
    g.end_turn()

    assert len(g.board.played_cards(first_player)) == 2
    assert first_player_card_2.health == 12
    g.play(second_player, second_player.hand[0])
    assert len(g.board.played_cards(first_player)) == 1
    assert first_player_card_2.health == 2
