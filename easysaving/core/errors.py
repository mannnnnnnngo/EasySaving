"""도메인 예외."""


class EasySavingError(Exception):
    """앱 내부에서 사용자에게 보여줄 수 있는 오류의 최상위 타입."""

    def __init__(self, message, detail=""):
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotAPdfError(EasySavingError):
    pass


class PdfReadError(EasySavingError):
    pass


class PdfEncryptedError(EasySavingError):
    pass


class OutputError(EasySavingError):
    pass


class CancelledError(EasySavingError):
    pass
