class InvalidActionError(Exception):
    pass


class DeadCardError(Exception):
    pass


class TooManyCardsError(InvalidActionError):
    pass


class MissingCardError(InvalidActionError):
    pass


class NotEnoughManaError(InvalidActionError):
    pass


class EmptyDeckError(Exception):
    def __init__(self, count):
        self.deal_attempt = count


class DeadPlayerError(Exception):
    pass


class GameNotStartedError(InvalidActionError):
    pass


class InvalidPlayerTurnError(InvalidActionError):
    pass


class CardCannotAttackError(InvalidActionError):
    pass


class TargetNotDefinedError(InvalidActionError):
    pass


class InvalidTargetError(InvalidActionError):
    pass
