class BaseError(Exception):
    """폰트 관련 예외의 공통 베이스 클래스"""

    def __init__(self, message: str, cause: Exception | None = None):
        self.cause = cause
        full_msg = message
        if cause:
            full_msg += f" (원인: {cause.__class__.__name__}: {cause})"
        super().__init__(full_msg)


class FontDownloadError(BaseError):
    pass


class FontApplyError(BaseError):
    pass


class ChromiumInstallError(BaseError):
    pass


class ConfigLoadError(BaseError):
    pass


class ConfigSaveError(BaseError):
    pass
