import random
from math import sqrt, log
from collections import deque
from typing import Iterator, Callable, Optional, Iterable

from pyheart.exceptions import InvalidActionError, DeadPlayerError
from pyheart.game import Game


class ChildrenContainer:
    def __init__(self):
        self._list = []
        self._set = set()

    def add(self, child):
        if child in self:
            return False
        self._list.append(child)
        self._set.add(child)
        return True

    def __contains__(self, item):
        return item in self._set

    def __getitem__(self, item):
        return self._list[item]

    def __getattr__(self, item):
        return list(getattr(child, item) for child in self._list)

    def __str__(self):
        return str(self._list)

    def __repr__(self):
        return repr(self._list)

    def __iter__(self):
        return iter(self._list)

    def __len__(self):
        return len(self._list)


class Node:
    def __init__(self):
        self.visits = 0
        self.children = ChildrenContainer()
        self.wins = 0
        self.losses = 0
        self.is_terminal = False
        self.is_expandable = True
        self.parent = None

    def find_node(self, node: 'Node'):
        queue = deque([self])
        while queue:
            n = queue.pop()
            if n == node:
                return n
            queue.extendleft(n.children)
        return node

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
        total_games = self.wins + self.losses
        if total_games:
            return self.wins / total_games
        return 0

    def add_children(self, children: Iterable['Node']):
        for child in children:
            self.add_child(child)

    def add_child(self, child: 'Node') -> bool:
        added = self.children.add(child)
        if added:
            child.parent = self
        return added

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
        self.visits += 1

    def __hash__(self) -> int:
        return hash(self.__class__)

    def __eq__(self, other: 'Node') -> bool:
        return hash(self) == hash(other)


class InitialGameNode(Node):
    def __str__(self):
        return 'Initial game state'


class AttackNode(Node):
    def __init__(self, player, attacker, victim):
        super(AttackNode, self).__init__()
        self.player = player
        self.attacker = attacker
        self.victim = victim

    def apply(self, game_state):
        game_state.attack(self.player.id, self.attacker.id, self.victim.id)

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
        game_state.play(self.player.id, self.card.id, getattr(self.target, 'id', None))

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
        game_state.endturn(self.player.id)

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
    def __init__(self, game_state: Game = None):
        if game_state is None:
            self.game = Game()
            self.game.start()
        else:
            self.game = game_state.copy()
        self.player = self.game.current_player
        self.root = InitialGameNode()

    @property
    def height(self) -> int:
        return self.root.height

    @property
    def nodes(self) -> int:
        return self.root.nodes

    def reply_game(self, node: Node) -> Game:
        game = self.game.copy()
        for action in reversed(node.path[:-1]):
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
            return child.score + 2 * const * sqrt(2 * log(parent.visits) / child.visits)
        return scoring_function

    def expand(self, node: Node) -> Node:
        game = self.reply_game(node)
        for new_action in ActionGenerator(game):
            if node.add_child(new_action):
                return new_action
        node.is_expandable = False
        return node

    def default_policy(self, node: Node) -> float:
        try:
            game = self.reply_game(node)
            action = None
            for action in ActionGenerator(game, apply=True):
                pass
            action.apply(game)
        except DeadPlayerError as e:
            if e.player == self.player:
                return -1
            return 1

    def backup(self, node: Node, reward: float):
        for n in node.path:
            n.visit()
            if reward > 0:
                n.wins += reward
            else:
                n.losses += abs(reward)

    def run(self, iterations: int = 1) -> Node:
        for _ in range(iterations):
            selected_node = self.tree_policy()
            reward = self.default_policy(selected_node)
            self.backup(selected_node, reward)
        return self.best_action

    @property
    def best_action(self) -> Optional[Node]:
        children = list(self.root.children)
        try:
            return sorted(children, key=lambda k: k.wins).pop()
        except IndexError:
            return None

    def play(self, node: Node):
        if node is not None:
            self.root = self.root.find_node(node)
            self.root.parent = None
            self.root.apply(self.game)

    def __repr__(self) -> str:
        return '<{0.__class__.__name__} nodes: {0.nodes}, height: {0.height}>'.format(self)

    def _print_node(self, node: Node, level: int = 0) -> str:
        current_node = '* ' * level + str(node)
        result = [current_node]
        result.extend(self._print_node(child, level+1) for child in node.children)
        return '\n'.join(result)

    def __str__(self):
        return self._print_node(self.root)
