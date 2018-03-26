import pytest
from pyheart import Game


@pytest.fixture()
def game():
    start_cards = Game.NUMBERS_OF_START_CARDS
    yield Game
    Game.NUMBERS_OF_START_CARDS = start_cards
