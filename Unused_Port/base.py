import logging
import os
from typing import ClassVar, Union

from Unused_Port.errors import UPC_SSH_CONNEXION_ERROR
from Unused_Port.helper import retry

_log = logging.getLogger(__name__)

try:
    from paramiko import SSHClient
except ImportError:
    _log.warning("Installation de paramiko en cours ...")
    os.system("pip install paramiko -q -q -q")
    from paramiko import SSHClient


class BaseConnexion(SSHClient):
    """
    Classe permettant la connexion SSH à un switch, hérite de la classe
    SSHClient de Paramiko.
    """

    _instance: ClassVar[dict[tuple[str, str, str], "BaseConnexion"]] = {}

    def __new__(
        cls, hostname: str, username: str, password: str, *args, **kwargs
    ) -> "BaseConnexion":
        """
        Check si aucune instance n'existe deja pour cet hostname avec le
        meme compte.
        """
        _check: tuple[str, str, str] = (hostname, username, password)
        if _instance := cls._instance.get(_check, None):
            return _instance
        _instance = super().__new__(cls)
        cls._instance[_check] = _instance
        return _instance

    def __init__(self, hostname: str, username: str, password: str):
        """Instancie la classe et crée les attributs _* utilisés par les childs."""
        if not hostname or not username or not password:
            raise Exception(
                "Les paramètres 'hostname','username' et 'password' sont obligatoires"
            )
        self._hostname: str = hostname
        self._username: str = username
        self._password: str = password
        self.valid = False

        super().__init__()

    @retry(max_retries=3, delay=1)
    def _connect(self) -> Union[str, bool]:
        """
        Cette fonction permet d'essayer de se connecter 3 fois avec des
        délais de 1 seconde entre chaque essai, au switch dont
        l'hostname est self._hostname.

        :return: False si connecté, raise UPC_SSH_CONNEXION_ERROR()
            après 3 essais non concluants
        """
        _log.debug(
            f"Connexion SSH au switch {self._hostname}... (20s avant de timeout)"
        )
        try:
            self.connect(
                hostname=self._hostname,
                username=self._username,
                password=self._password,
            )

        except (OSError, Exception) as e:
            self.close()
            if isinstance(e, OSError) and e.winerror == 10060:
                raise UPC_SSH_CONNEXION_ERROR(
                    "Erreur timeout, " "Check l'ip fournie !"
                ) from e
            raise UPC_SSH_CONNEXION_ERROR(str(e)) from e
        else:
            _log.info(f"Connexion SSH au switch {self._hostname} : Succes !")
            self.valid = True
            return False

    @classmethod
    def _remove_instance(cls, hostname: str, username: str, password: str):
        """
        Permet de delete l'instance de self._instance, et donc permet de
        créer une nouvelle instance avec le meme hostname (un autre jour
        par exemple sans relancer le script, utilisé pour --schedule).

        :param hostname: hostname de l'instance
        :param username: username de l'instance
        :param password: password de l'instance
        :return: None
        """
        _check: tuple[str, str, str] = (hostname, username, password)
        if _check in cls._instance:
            del cls._instance[_check]

    def _stop(self):
        """Permet de stopper l'instance en cours."""
        self._remove_instance(self._hostname, self._username, self._password)
        _log.debug(f"Suppression de l'instance pour l'host {self._hostname}")
