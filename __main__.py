from pyheart.duel import Duel, RandomPlayer, MCTSPlayer

if __name__ == '__main__':
    d = Duel(MCTSPlayer(), RandomPlayer())
    d.start()
