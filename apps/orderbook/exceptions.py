class QuantityError(ArithmeticError):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


class OrderTypeError(ValueError):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


class OrderNotFoundError(ValueError):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


class OrderStatusError(ValueError):
    pass
