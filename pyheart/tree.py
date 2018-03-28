import random
from math import sqrt, log
from functools import partial
from typing import Iterator, Callable, Optional, TypeVar

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

    def __repr__(self) -> str:
        return '<{0.__class__.__name__} attacker: {0.attacker!r} victim: {0.victim!r}>'.format(self)


class PlayCartNode(Node):
    def __init__(self, player, card, target=None):
        super(PlayCartNode, self).__init__()
        self.player = player
        self.card = card
        self.target = target

    def apply(self, game_state: 'Game'):
        game_state.play(self.player, self.card, self.target)

    def __repr__(self) -> str:
        return '<{0.__class__.__name__} card: {0.card!r} target: {0.target!r}>'.format(self)


class EndTurnNode(Node):
    def __init__(self, player: 'Player'):
        super(EndTurnNode, self).__init__()
        self.player = player

    def apply(self, game_state: 'Game'):
        game_state.endturn(self.player)


# class GameOverNode(Node):
#
#     @property
#     def is_terminal(self):
#         return True

T = TypeVar('T')


class ActionGenerator:
    def __init__(self, game_state: Game):
        self.game_state = game_state

    def _is_valid_action(self, action: Optional[Node]) -> bool:
        if action is None:
            return False
        try:
            action.apply(self.game_state.copy())
            return True
        except InvalidActionError:
            return False

    def _handle_invalid_actions(self, generator: Iterator[T]) -> Iterator[T]:
        all_actions = generator
        while True:
            action = next(all_actions)
            if self._is_valid_action(action):
                yield action

    def attack_actions(self) -> Iterator[AttackNode]:
        actions_generator = self._all_attack_actions()
        yield from self._handle_invalid_actions(actions_generator)

    def _all_attack_actions(self) -> Iterator[AttackNode]:
        board = self.game_state.board
        player = self.game_state.current_player
        player_cards = board.played_cards(player)
        random.shuffle(player_cards)

        enemy = self.game_state.next_player
        enemy_targets = board.played_cards(enemy)
        enemy_targets.append(enemy)
        random.shuffle(enemy_targets)

        for attacker in player_cards:
            for victim in enemy_targets:
                yield AttackNode(player, attacker, victim)

    def play_actions(self) -> Iterator[PlayCartNode]:
        actions_generator = self._all_play_actions()
        yield from self._handle_invalid_actions(actions_generator)

    def _all_play_actions(self) -> Iterator[PlayCartNode]:
        player = self.game_state.current_player
        hand = player.hand
        random.shuffle(hand)

        player_cards = self.game_state.board.played_cards(player)
        player_cards.append(None)
        for card in hand:
            random.shuffle(player_cards)
            for target in player_cards:
                yield PlayCartNode(player, card, target)

    def endturn_action(self) -> Iterator[EndTurnNode]:
        action = EndTurnNode(self.game_state.current_player)
        if self._is_valid_action(action):
            yield action

    def random_actions(self) -> Iterator[Node]:
        available_generators = [self.play_actions(), self.attack_actions(), self.endturn_action()]
        while available_generators:
            index = random.randint(0, len(available_generators) - 1)
            current_generator = available_generators[index]
            try:
                yield next(current_generator)
            except StopIteration:
                available_generators.remove(current_generator)


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
        return self._game.copy()

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
