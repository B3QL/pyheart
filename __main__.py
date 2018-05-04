from pyheart.duel import Duel, RandomPlayer

if __name__ == '__main__':
    d = Duel(RandomPlayer(), RandomPlayer())
    d.start()
