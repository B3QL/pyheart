from pyheart.game import Game, DeadPlayerError
from pyheart.tree import GameTree, ActionGenerator


class RandomPlayer:
    NAME = 'Random'

    def get_move(self, game: Game):
        generator = iter(ActionGenerator(game))
        return next(generator)

    def update_state(self, move):
        pass


class MCTSPlayer:
    NAME = 'MCTS'
    ITERATIONS = 100

    def __init__(self):
        self.tree = None

    def get_move(self, game: Game):
        if not self.tree:
            self.tree = GameTree(game_state=game)
        best_move = self.tree.run(self.ITERATIONS)
        return best_move

    def update_state(self, move):
        if self.tree:
            self.tree.play(move)


class Duel:
    def __init__(self, player_1, player_2):
        players = [player_1, player_2]
        self.game = Game(player_names=[player.NAME for player in players])
        self._players = {game_player.id: player for player, game_player in zip(players, self.game.players)}
        self._started = False

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

    def start(self):
        if not self._started:
            self.game.start()
            print(self.format_game())
            print()
            try:
                while True:
                    move = self.player.get_move(self.game)
                    move.apply(self.game)
                    self.update_players_state(move)
                    print('MOVE:', move)
                    print(self.format_game())
                    print()
            except DeadPlayerError as e:
                print('LOSER: {0.name} ({0.id})'.format(e.player))
                print(e)
            self._started = True
