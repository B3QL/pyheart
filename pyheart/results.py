import json
from io import StringIO

import pandas as pd


def parse_file(file, columns):
    game_number = 1
    columns[0] = 'game_over'
    for line in file:
        stats_data = json.loads(line)
        game_over = stats_data['game_over']
        stats_data['game_over'] = game_number
        if game_over:
            game_number += 1

        yield ','.join(str(stats_data.get(col, '')) for col in columns) + '\n'


def read_file(filepath, columns):
    with open(filepath) as f:
        header_row = ','.join(columns) + '\n'
        return StringIO(header_row + ''.join(parse_file(f, columns)))


def file_data(filepath):
    column_names = ['game_number', 'game_turn', 'player_name', 'tree_height', 'tree_exploration', 'tree_nodes', 'loser']
    return pd.read_csv(read_file(filepath, column_names))


if __name__ == '__main__':
    print(file_data('../data/aggressive_mcts_combined.txt'))
