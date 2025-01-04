import logging
import os
from pathlib import Path, PurePath
from typing import ClassVar, Optional, Union

from Unused_Port.secrets import shared_folder_password, shared_folder_username

_log = logging.getLogger(__name__)

try:
    import win32wnet
except ImportError:
    _log.warning("Installation de win32wnet en cours ...")
    os.system("pip install pywin32 -q -q -q")
    import win32wnet  # type: ignore


# TODO: Fix le bug décris en dessous


class Status:
    """Liste des status possibles pour les classes Shared.*."""

    FAILED = 0
    SUCCES = 1
    UNCHECKED = None


class Shared_Folder_Conn:
    """Gère la connexion et la déconnexion vers un répertoire partagé."""

    def __init__(self, path: Union[str, PurePath]):
        r"""
        Instancie la classe Shared_Folder_Conn.

        :param path: le path sous forme str r'path' ou
            '\\\\france\\srv', sans le site, seulement le dossier sans
            access
        """
        if hasattr(self, "_created"):
            return
        self._created = True

        self.error = None
        if not (shared_folder_username and shared_folder_password):
            self.error = (
                "shared_folder_username et shared_folder_password "
                "sont nécessaires, check secrets.py"
            )

        self.path: Union[str, PurePath] = path

        self._net_ressource = win32wnet.NETRESOURCE()
        self._net_ressource.lpRemoteName = str(self.path)

        self.status: Optional[int] = Status.UNCHECKED

    def _try_conn(self) -> Optional[bool]:
        r"""
        Cette fonction check si le parent du path existe, s'il existe, une
        connexion est deja présente.

        Le path doit etre '\\\\france\\srv\\{site}' ou r'path', le
        dossier du site n'étant pas forcement crée, il faut check si le
        parent existe, le parent doit lui etre crée préalablement
        :return: True / (False/None) si le path existe / existe pas
        """
        try:
            _log.debug("Check si la connexion existe deja et que le path est établi")
            return Path(self.path).exists()
        except PermissionError as e:
            _log.error(
                f"Permission erreur pour check si le path existe, "
                f"aucune connexion existante {e} {self.path=}"
            )
            return None
        except Exception as e:
            _log.error(f"{e} {self.path=}")
            return None

    def _cancel_conn(self) -> Optional[bool]:
        """
        Cette fonction est utilisée pour cancel la connexion vers le
        dossier partagé.

        :return: None / True si cela n'a pas fonctionné / fonctionné
        """
        try:
            win32wnet.WNetCancelConnection2(self.path, 0, 0)
            return True
        except Exception as e:
            _log.error(f"{e} {self.path=}")
            return None

    def _create(self) -> Optional[str]:
        """
        Cette fonction est utilisée pour créer la connexion vers le dossier
        commun, si celle ci echoue, peut etre une mauvaise connexion est
        déja etablie, il va alors essayer de la supprimer.

        :return:
        """
        _log.debug(f"Crée une connexion vers le path {self.path}")
        try:
            win32wnet.WNetAddConnection2(
                self._net_ressource,
                shared_folder_password,
                shared_folder_username,
                0,
            )
        except Exception as e:
            e_nb, *_ = e.args
            _log.error(f"{e} {self.path=}")
            if e_nb == 1219:
                _log.debug("Essaie de cancel de connexion")
                res = self._cancel_conn()
                if res:
                    return self._create()
            # if e_nb == 53:
            #     self._ppath = self._ppath[:-1]
            # return self._create()
        return None

    def _try(self) -> bool:
        _log.debug(f"Création de la connexion vers {self.path}")
        if self._try_conn():
            self.status = Status.SUCCES
            return True
        self._create()
        if self._try_conn():
            self.status = Status.SUCCES
            return True
        self.status = Status.FAILED
        return False

    def _create_conn(self) -> bool:
        """
        C'est cette fonction qui gere l'appel aux autres fonction, c'est le
        point d'entrée des classes enfants.

        :return: True / False si réussi ou non
        """
        if self._try():
            return True

        self.path = str(Path(self.path).parent)
        if self.path.endswith("\\"):
            self.path = self.path[:-1]
        self._net_ressource.lpRemoteName = self.path

        return self._try()


class Shared_Folder_Manager(Shared_Folder_Conn):
    """Gestion des instances de la classe parente, une instance par path max."""

    _instance: ClassVar[dict[str, "Shared_Folder_Manager"]] = {}

    def __new__(cls, path: Union[str, PurePath]):
        r"""
        Crée une nouvelle instance de classe 'Shared_Folder_Manager'.

        :param path: le path sous forme str r'path' ou
            '\\\\france\\srv', sans le site, seulement le dossier sans
            access
        :return: Instance de classe
        """
        if not isinstance(path, str):
            path = str(path)
        if _instance := cls._instance.get(path, None):
            return _instance
        instance = super().__new__(cls)
        cls._instance[path] = instance
        return instance

    @classmethod
    def _delete_instance(
        cls, inst: "Shared_Folder_Manager", *, path: Optional[str] = None
    ):
        r"""
        Cette fonction delete l'instance du dictionnaire cls._instance.

        :param inst: instance de classe 'Shared_Folder'
        :param path: le path sous forme str r'path' ou
            '\\\\france\\srv', sans le site, seulement le dossier sans
            access
        :return:
        """
        if not path:
            for p, instances in cls._instance.items():
                if instances == inst:
                    path = p
        if path:
            del cls._instance[path]

    def _clean(self):
        """
        Cette fonction supprime toutes les instances de classe.

        'Shared_Folder' du dictionnaire cls._instance.

        :return:
        """
        for path, inst in self._instance.items():
            self._delete_instance(inst, path=path)

    def clean_all(self):
        """
        Cette fonction est le point d'entrée pour supprimer toutes les
        instances de classe 'Shared_Folder' du dictionnaire
        cls._instance.

        :return:
        """
        self._clean()


class Shared_Folder(Shared_Folder_Manager):
    """Entry point des classes parentes."""

    def delete(self):
        """
        Cette fonction est utilisée pour delete l'instance.

        :return:
        """
        return self._delete_instance(self)

    def connect(self):
        """
        Cette fonction est utilisée pour crée la connexion au fichier.

        partagé.

        :return:
        """
        if self.status:
            _log.warning(f"Le status déja check pour ce path {self.path}")
            return self.status == Status.SUCCES
        return self._create_conn()


if __name__ == "__main__":
    pass
