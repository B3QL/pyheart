import random
from copy import deepcopy
from math import sqrt, log
from functools import partial
from typing import Iterator, Callable, Optional

from pyheart.exceptions import InvalidActionError
from pyheart.game import Game


class Node:
    def __init__(self):
        self.visited = 0
        self.children = []
        self.wins = 0
        self.looses = 0

    @property
    def nodes(self):
        return 1 + sum(child.nodes for child in self.children)

    @property
    def height(self):
        if self.is_leaf:
            return 0
        return 1 + max(child.height for child in self.children)

    @property
    def score(self):
        total_games = self.wins + self.looses
        if total_games:
            return self.wins / total_games
        return 0

    def add_children(self, children):
        self.children.extend(children)

    def visit(self):
        self.visited += 1

    @property
    def is_leaf(self):
        return not bool(self.children)

    def best_child(self, scoring_function: Callable[['Node'], float]) -> Optional['Node']:
        if self.is_leaf:
            return None
        self.children.sort(key=scoring_function, reverse=True)
        return self.children[0]

    def apply(self, game_state: Game):
        pass


class StartGameNode(Node):
    def apply(self, game_state: Game):
        game_state.start()


class AttackNode(Node):
    def __init__(self, player, attacker, victim):
        super(AttackNode, self).__init__()
        self.player = player
        self.attacker = attacker
        self.victim = victim

    def apply(self, game_state):
        game_state.attack(self.player, self.attacker, self.victim)


class PlayCartNode(Node):
    def __init__(self, player, card, target=None):
        super(PlayCartNode, self).__init__()
        self.player = player
        self.card = card
        self.target = target

    def apply(self, game_state: 'Game'):
        game_state.play(self.player, self.card, self.target)


class EndTurnNode(Node):
    def apply(self, game_state: 'Game'):
        game_state.endturn()


# class GameOverNode(Node):
#
#     @property
#     def is_terminal(self):
#         return True


class ActionGenerator:
    def __init__(self, game_state: Game):
        self.game_state = game_state
        self.actions_generators = [self.attack_action(), self.play_action(), self.endturn_action()]

    def random_action(self) -> Node:
        for action in self.action_generator():
            game = deepcopy(self.game_state)
            try:
                action.apply(game)
                return action
            except InvalidActionError:
                continue

    def action_generator(self) -> Iterator[Node]:
        if not self.actions_generators:
            raise StopIteration

        action_generator = random.choice(self.actions_generators)
        try:
            node = next(action_generator)
            yield node
        except StopIteration:
            self.actions_generators.remove(action_generator)
            yield from self.action_generator()

    def attack_action(self) -> Iterator[AttackNode]:
        board = self.game_state.board
        player = self.game_state.current_player
        player_cards = board.played_cards(player)
        random.shuffle(player_cards)

        enemy = self.game_state.next_player
        enemy_cards = board.played_cards(enemy)
        enemy_targets = enemy_cards + [enemy]
        random.shuffle(enemy_targets)

        for attacker in player_cards:
            for victim in enemy_targets:
                yield AttackNode(player, attacker, victim)

    def play_action(self) -> Iterator[PlayCartNode]:
        player = self.game_state.current_player
        hand = player.hand
        random.shuffle(hand)

        player_cards = self.game_state.board.played_cards(player)
        random.shuffle(player_cards)

        for card in hand:
            for target in player_cards:
                yield PlayCartNode(player, card, target)

    def endturn_action(self) -> Iterator[EndTurnNode]:
        yield EndTurnNode()


class GameTree:
    def __init__(self, game_state: Game = None, root: Node = None):
        self._game = game_state or Game()
        self.root = root or StartGameNode()

    @property
    def height(self) -> int:
        return self.root.height

    @property
    def nodes(self) -> int:
        return self.root.nodes

    @property
    def game(self) -> Game:
        return deepcopy(self._game)

    def select_node(self, node: Node, game_state: Game) -> Node:
        node.visit()
        if node.is_leaf:
            return node

        scoring_function = partial(self._calculate_uct, parent=node)
        best_child = node.best_child(scoring_function)
        best_child.apply(game_state)
        return self.select_node(best_child, game_state)

    def _calculate_uct(self, parent: Node, child: Node) -> float:
        const = 1 / sqrt(2)
        return child.score + 2 * const * sqrt(2 * log(parent.visited) / child.visited)

    def expand(self, parent: Node, game_state: Game) -> Node:
        child = ActionGenerator(game_state).random_action()
        parent.add_children(child)
        child.apply(game_state)
        return child

    def run(self):
        game_state_copy = self.game
        selected_node = self.select_node(self.root, game_state_copy)
        new_node = self.expand(selected_node, game_state_copy)
        self.simulate(new_node, game_state_copy)
        # backpropagation

    def simulate(self, new_node: Node, game_state: Game):
        for action in ActionGenerator(game_state):
            action.apply(game_state)
