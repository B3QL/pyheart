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
    def __init__(self, count: int):
        self.deal_attempt = count


class DeadPlayerError(Exception):
    def __init__(self, msg: str, player: 'Player'):
        super(DeadPlayerError, self).__init__(msg)
        self.player = player


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
