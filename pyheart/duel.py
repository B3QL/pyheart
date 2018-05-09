import json
import random
import multiprocessing as mp
from datetime import datetime

from pyheart.game import Game, DeadPlayerError, Player as GamePlayer
from pyheart.tree import GameTree, ActionGenerator, AttackNode


class Player:
    DEFAULT_NAME = ''

    def __init__(self, name: str = None):
        self.name = name or self.DEFAULT_NAME

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{0.__class__.__name__} name: {0.name}>'.format(self)

    def update_state(self, move):
        pass

    @property
    def stats(self):
        return {}

    def clone(self):
        return self.__class__(self.name)


class RandomPlayer(Player):
    DEFAULT_NAME = 'Random'

    def get_move(self, game: Game):
        generator = iter(ActionGenerator(game))
        return next(generator)


class AggressivePlayer(Player):
    DEFAULT_NAME = 'Aggressive'

    def get_move(self, game: Game):
        actions = set(ActionGenerator(game))
        attack_actions = set(filter(lambda a: isinstance(a, AttackNode), actions))
        attack_hero = set(filter(lambda a: isinstance(a.victim, GamePlayer), attack_actions))
        attack_minions = attack_actions - attack_hero
        for action_type in [attack_hero, attack_minions, actions]:
            actions = list(action_type)
            random.shuffle(actions)
            for action in actions:
                return action


class ControllingPlayer(Player):
    DEFAULT_NAME = 'Controlling'

    def get_move(self, game: Game):
        actions = set(ActionGenerator(game))
        attack_actions = set(filter(lambda a: isinstance(a, AttackNode), actions))
        attack_hero = set(filter(lambda a: isinstance(a.victim, GamePlayer), attack_actions))
        attack_minions = attack_actions - attack_hero

        all_actions = [attack_minions, actions]
        for action_type in all_actions:
            actions = list(action_type)
            random.shuffle(actions)
            for action in actions:
                return action


class MCTSPlayer(Player):
    DEFAULT_NAME = 'MCTS'
    DEFAULT_ITERATIONS = 100

    def __init__(self, name: str = None, iterations: int = DEFAULT_ITERATIONS):
        super(MCTSPlayer, self).__init__(name)
        self.tree = None
        self.iterations = iterations

    def get_move(self, game: Game):
        if not self.tree:
            self.tree = GameTree(game_state=game)
        best_move = self.tree.run(self.iterations)
        return best_move

    def update_state(self, move):
        if self.tree:
            self.tree.play(move)

    @property
    def stats(self):
        return {
            'tree_height': self.tree.height,
            'tree_exploration': self.tree.exploration_rate,
            'tree_nodes': self.tree.nodes
        }

    def clone(self):
        return MCTSPlayer(self.name, self.iterations)


class Duel:
    def __init__(self, player_1, player_2):
        players = [player_1, player_2]
        self.game = Game(player_names=[player.name for player in players])
        self.game.start()
        self._players = {game_player.id: player for player, game_player in zip(players, self.game.players)}

    @property
    def player(self):
        return self._players[self.game.current_player.id]

    def update_players_state(self, move):
        for player in self._players.values():
            player.update_state(move)

    def format_game(self):
        representation = str(self.game)
        lines = representation.split('\n')
        turn = '%s: ' % self.game.turn
        return '\n'.join(turn + l for l in lines)

    def print_game_status(self):
        print(self.format_game())
        print()

    @property
    def stats(self):
        return {'game_turn': self.game.turn, 'player_name': self.player.name}

    def make_move(self):
        info = {'game_over': False}
        move = self.player.get_move(self.game)
        info['last_move'] = move
        info.update(self.stats)
        info.update(self.player.stats)
        try:
            move.apply(self.game)
            self.update_players_state(move)
        except DeadPlayerError as e:
            info['game_over'] = True
            info['loser'] = e.player
        return info

    def start(self):
        self.print_game_status()
        info = {'game_over': False}
        while not info.get('game_over'):
            info = self.make_move()
            print('MOVE:', info['last_move'])
            self.print_game_status()
        print('LOSER: {0}'.format(info['loser']))


class Arena:
    def __init__(self, fights, fighter_pairs):
        self.duels = [
            Duel(first.clone(), second.clone())
            for _ in range(fights)
            for first, second in fighter_pairs
        ]

    def start(self):
        with mp.Pool() as pool:
            start = datetime.now()
            print('Start:', start)
            for i, result in enumerate(pool.imap_unordered(self.start_duel, self.duels), start=1):
                print(i, '/', len(self.duels), datetime.now())
                players = list(set(move.get('player_name', 'unknown').lower() for move in result))
                filename = '_'.join(sorted(players))
                with open(filename + '.txt', 'a') as f:
                    f.writelines('\n'.join(map(json.dumps, result)) + '\n')
            end = datetime.now()
            print('End:', end)
            print('Elapsed:', end - start)

    def start_duel(self, duel):
        latest_info = {}
        all_info = []
        while not latest_info.get('game_over'):
            latest_info = duel.make_move()
            del latest_info['last_move']
            if 'loser' in latest_info:
                latest_info['loser'] = latest_info['loser'].name
            all_info.append(latest_info)
        return all_info


if __name__ == '__main__':
    fighter_pairs = [
        (MCTSPlayer(iterations=10), AggressivePlayer()),
        (MCTSPlayer(iterations=10), RandomPlayer()),
        (MCTSPlayer(iterations=10), ControllingPlayer()),
    ]
    arena = Arena(fights=2, fighter_pairs=fighter_pairs)
    arena.start()
