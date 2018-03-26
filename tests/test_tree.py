import pytest

from pyheart.cards import Deck, MinionCard, ChargeAbility
from pyheart.tree import GameTree, Node, ActionGenerator


def test_create_tree():
    tree = GameTree()

    assert tree.nodes == 1
    assert tree.height == 0

    tree.root.add_children(Node() for _ in range(10))
    assert tree.nodes == 11
    assert tree.height == 1

    tree.root.children[0].add_children(Node() for _ in range(5))
    assert tree.nodes == 16
    assert tree.height == 2


def test_select_node():
    tree = GameTree()

    assert tree.select_node(tree.root, tree.game) == tree.root


def test_play_action_generator(game):
    deck = Deck([
        MinionCard('test minion', health=1, attack=1, cost=1),
        MinionCard('test minion 2', health=1, attack=1, cost=1),
        MinionCard('test costly minion', health=1, attack=1, cost=100),
    ])
    game.NUMBERS_OF_START_CARDS = (2,)
    g = game(player_decks=[deck])
    player, = g.players
    g.start()
    gen = ActionGenerator(g)

    assert len(player.hand) == 3
    assert len(list(gen.attack_actions())) == 0
    assert len(list(gen.play_actions())) == 2
    assert len(list(gen.endturn_action())) == 1


def test_attack_action_generator_no_board_enemies(game):
    cards = [
        MinionCard('test minion', health=1, attack=1, cost=0),
        MinionCard('test minion 2', health=1, attack=1, cost=0),
        MinionCard('test charge minion', health=1, attack=1, cost=0, ability=ChargeAbility()),
    ]
    deck = Deck(cards)
    game.NUMBERS_OF_START_CARDS = (2,)
    g = game(player_decks=[deck])
    player, = g.players
    g.start()
    for card in cards:
        g.play(player, card)
    gen = ActionGenerator(g)

    assert len(player.hand) == 0
    assert len(list(gen.attack_actions())) == 1
    assert len(list(gen.play_actions())) == 0
    assert len(list(gen.endturn_action())) == 1
    assert player.health == 20
