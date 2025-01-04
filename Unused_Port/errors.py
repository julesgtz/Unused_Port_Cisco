class UPC_ERROR(Exception):
    """UPC BASE ERROR."""

    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        """Retourne le nom de la classe suivi du message."""
        return f"{self.__class__.__name__}: {self.msg}"


class UPC_UP_TIME_ERROR(UPC_ERROR):
    """Erreur à cause de l'uptime du switch."""


class UPC_VALIDATION_ERROR(UPC_ERROR):
    """Erreur lors de la validation de la data reçue."""


class UPC_SSH_CONNEXION_ERROR(UPC_ERROR):
    """Erreur lors de la connexion au switch."""


class UPC_UNKNOWN_ERROR(UPC_ERROR):
    """Erreur inconnue."""


class UPC_RETRY_ERROR(UPC_ERROR):
    """Erreur retry."""
