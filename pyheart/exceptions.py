class DeadCardError(Exception):
    pass


class TooManyCardsError(Exception):
    pass


class MissingCardError(Exception):
    pass


class NotEnoughManaError(Exception):
    pass


class EmptyDeckError(Exception):
    def __init__(self, count):
        self.deal_attempt = count


class DeadPlayerError(Exception):
    pass


class GameNotStartedError(Exception):
    pass


class InvalidPlayerTurnError(Exception):
    pass


class CardCannotAttackError(Exception):
    pass


class TargetNotDefinedError(Exception):
    pass
