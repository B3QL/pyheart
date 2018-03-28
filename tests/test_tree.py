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
    assert len(list(gen.random_actions())) == 3


def test_attack_action_generator_no_board_enemies(game):
    cards = [
        MinionCard('test minion', health=1, attack=1, cost=0),
        MinionCard('test minion 2', health=1, attack=1, cost=0),
        MinionCard('test charge minion', health=1, attack=1, cost=0, ability=ChargeAbility()),
    ]
    deck = Deck(cards)
    game.NUMBERS_OF_START_CARDS = (2, 0)
    g = game(player_decks=[deck, deck])
    player, _ = g.players
    g.start()
    for card in cards:
        g.play(player, card)
    gen = ActionGenerator(g)

    assert len(player.hand) == 0
    assert len(list(gen.attack_actions())) == 1  # only charge minion can attack
    assert len(list(gen.play_actions())) == 0
    assert len(list(gen.endturn_action())) == 1
    assert len(list(gen.random_actions())) == 2
    assert player.health == 20


def test_attack_action_generator_with_enemies(game):
    cards = [
        MinionCard('test minion', health=1, attack=1, cost=0),
        MinionCard('test minion 2', health=1, attack=1, cost=0),
        MinionCard('test charge minion', health=1, attack=1, cost=0, ability=ChargeAbility()),
    ]
    deck = Deck(cards)
    game.NUMBERS_OF_START_CARDS = (0, 0)
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    g.play(first_player, first_player.hand[0])
    g.endturn(g.current_player)
    g.play(second_player, second_player.hand[0])
    g.endturn(g.current_player)
    g.play(first_player, first_player.hand[0])

    gen = ActionGenerator(g)

    assert len(g.board) == 3
    assert len(g.board.played_cards(first_player)) == 2
    assert len(g.board.played_cards(second_player)) == 1
    # two minions (played in previous turn and having charge ability) can attack minion and second player
    assert len(list(gen.attack_actions())) == 4
    assert len(list(gen.play_actions())) == 0
    assert len(list(gen.endturn_action())) == 1
    assert len(list(gen.random_actions())) == 5
    assert first_player.health == second_player.health == 20
    assert len(g.board) == 3


def test_random_action_generator(game):
    cards = [
        MinionCard('test minion', health=1, attack=1, cost=0),
        MinionCard('test minion 2', health=1, attack=1, cost=0),
        MinionCard('test charge minion', health=1, attack=1, cost=0, ability=ChargeAbility()),
    ]
    deck = Deck(cards)
    game.NUMBERS_OF_START_CARDS = (0, 0)
    g = game(player_decks=[deck, deck])
    first_player, second_player = g.players
    g.start()
    g.play(first_player, first_player.hand[0])
    g.endturn(g.current_player)
    g.play(second_player, second_player.hand[0])
    g.endturn(g.current_player)

    gen = ActionGenerator(g)

    assert len(list(gen.attack_actions())) == 2
    assert len(list(gen.play_actions())) == 1
    assert len(list(gen.endturn_action())) == 1
    assert len(list(gen.random_actions())) == 4


def test_all_generate_actions_are_applicable(game):
    g = game()
    gen = ActionGenerator(g)

    assert list(gen.random_actions()) == []
    g.start()
    available_actions = list(gen.random_actions())
    assert len(available_actions) > 0

    for action in available_actions:
        action.apply(g.copy())


def test_playout(game):
    g = game()
    g.start()
    action = None
    for action in ActionGenerator(g, apply=True):
        pass

    assert action.is_terminal

