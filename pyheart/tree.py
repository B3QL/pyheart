import random
from math import sqrt, log
from typing import Iterator, Callable, Optional, Iterable

from pyheart.exceptions import InvalidActionError, DeadPlayerError
from pyheart.game import Game


class Node:
    def __init__(self):
        self.visited = 0
        self.children = set()
        self._wins = 0
        self._looses = 0
        self.is_terminal = False
        self.is_expandable = True
        self.parent = None

    @property
    def wins(self):
        return self._wins

    @wins.setter
    def wins(self, value):
        if value > 0:
            self._wins += value
        else:
            self._looses += abs(value)

    @property
    def nodes(self) -> int:
        return 1 + sum(child.nodes for child in self.children)

    @property
    def height(self) -> int:
        if self.is_leaf:
            return 0
        return 1 + max(child.height for child in self.children)

    @property
    def score(self) -> float:
        total_games = self._wins + self._looses
        if total_games:
            return self._wins / total_games
        return 0

    def add_children(self, children: Iterable['Node']):
        for child in children:
            self.add_child(child)

    def add_child(self, child: 'Node') -> bool:
        child.parent = self
        before_add = set(self.children)
        self.children.add(child)
        return bool(self.children - before_add)

    @property
    def path(self) -> Iterator['Node']:
        path = [self]
        parent_node = self.parent
        while parent_node:
            path.append(parent_node)
            parent_node = parent_node.parent
        return path

    @property
    def is_leaf(self) -> bool:
        return not bool(self.children)

    def best_child(self, scoring_function: Callable[['Node'], float]) -> Optional['Node']:
        if self.is_leaf:
            return None
        children = list(self.children)
        children.sort(key=scoring_function)
        return children.pop()

    def apply(self, game_state: Game):
        pass

    def visit(self):
        self.visited += 1

    def __hash__(self) -> int:
        return hash(self.__class__)

    def __eq__(self, other: 'Node') -> bool:
        return hash(self) == hash(other)


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

    def __str__(self) -> str:
        return '{0.player} attacked {0.victim} with {0.attacker}'.format(self)

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.player) ^ hash(self.attacker) ^ hash(self.victim)


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

    def __str__(self) -> str:
        fmt = '{0.player} played {0.card}'
        if self.target:
            fmt += ' on {0.target}'
        return fmt.format(self)

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.player) ^ hash(self.card) ^ hash(self.target)


class EndTurnNode(Node):
    def __init__(self, player: 'Player'):
        super(EndTurnNode, self).__init__()
        self.player = player

    def apply(self, game_state: 'Game'):
        game_state.endturn(self.player)

    def __str__(self) -> str:
        return '{0.player} ended turn'.format(self)

    def __repr__(self) -> str:
        return '<{0.__class__.__name__} player: {0.player!r}>'.format(self)

    def __hash__(self) -> int:
        return super(EndTurnNode, self).__hash__() ^ hash(self.player)


class ActionGenerator:
    def __init__(self, game_state: Game, apply: bool = False):
        self.game_state = game_state
        self.apply = apply

    def _is_valid_action(self, action: Optional[Node]) -> bool:
        if action is None:
            return False

        try:
            action.apply(self.game_state.copy())
        except InvalidActionError:
            return False
        return True

    def _handle_invalid_actions(self, generator: Iterator[Node]) -> Iterator[Node]:
        all_actions = generator
        while True:
            action = next(all_actions)
            is_valid = True
            try:
                is_valid = self._is_valid_action(action)
            except DeadPlayerError:
                action.is_terminal = True

            if is_valid:
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
        actions_generator = iter([action])
        yield from self._handle_invalid_actions(actions_generator)

    def random_actions(self) -> Iterator[Node]:
        available_generators = [self.play_actions(), self.attack_actions(), self.endturn_action()]
        while available_generators:
            index = random.randint(0, len(available_generators) - 1)
            current_generator = available_generators[index]
            try:
                yield next(current_generator)
            except StopIteration:
                available_generators.remove(current_generator)

    def __iter__(self):
        action_generator = self.random_actions()
        random_action = next(action_generator)
        while not random_action.is_terminal:
            yield random_action
            if self.apply:
                random_action.apply(self.game_state)
                random_action = next(self.random_actions())
            else:
                random_action = next(action_generator)
        yield random_action


class GameTree:
    def __init__(self, player: int = 1, game_state: Game = None, root: Node = None):
        self.game = game_state or Game()
        self.player = self.game.players[player - 1]
        self.root = root or StartGameNode()

    @property
    def height(self) -> int:
        return self.root.height

    @property
    def nodes(self) -> int:
        return self.root.nodes

    def reply_game(self, node: Node) -> Game:
        game = self.game.copy()
        for action in reversed(node.path):
            action.apply(game)
        return game

    def tree_policy(self) -> Node:
        node = self.root
        while not node.is_terminal:
            if node.is_expandable:
                return self.expand(node)
            else:
                node = node.best_child(self._calculate_uct(node))
        return node

    def _calculate_uct(self, parent: Node) -> Callable[[Node], float]:
        def scoring_function(child: Node) -> float:
            const = 1 / sqrt(2)
            return child.score + 2 * const * sqrt(2 * log(parent.visited) / child.visited)
        return scoring_function

    def expand(self, node: Node) -> Node:
        game = self.reply_game(node)
        for new_action in ActionGenerator(game):
            if node.add_child(new_action):
                return new_action
        node.is_expandable = False
        return node

    def default_policy(self, node: Node) -> float:
        game = self.reply_game(node)
        action = None
        for action in ActionGenerator(game, apply=True):
            pass

        try:
            action.apply(game)
        except DeadPlayerError as e:
            if e.player == self.player:
                return -1
            return 1

    def backup(self, node: Node, reward: float):
        current_player = getattr(node, 'player')
        for n in node.path[:-1]:
            n.visit()
            if getattr(n, 'player') == current_player:
                n.wins += reward
            else:
                n.wins -= reward

    def run(self, iterations: int) -> Node:
        for _ in range(iterations):
            selected_node = self.tree_policy()
            reward = self.default_policy(selected_node)
            self.backup(selected_node, reward)
        return self.best_action()

    def best_action(self) -> Node:
        children = list(self.root.children)
        return sorted(children, key=lambda k: k.wins).pop()

    def __repr__(self) -> str:
        return '<{0.__class__.__name__} nodes: {0.nodes}, height: {0.height}>'.format(self)
