import logging
import socket
from threading import Lock, Thread
from typing import FrozenSet, Generator, Union

_log = logging.getLogger(__name__)


class SocketWorker:
    """
    Threaded Socket Worker.

    Cette classe ouvre un socket avec tous les hosts d'une liste, sur le
    port 22, pour verifier si celui ci est up
    """

    def __init__(self, l_hosts: Union[list, set, Generator, FrozenSet]):
        """
        Instancie la classe 'SocketWorker' et crée un generateur avec les.

        ips, si 'l_hosts' n'en est pas un, et crée une Lock pour les
        threads.

        :param l_hosts: Une 'liste' d'une ou plusieurs ipv4
        """
        if not isinstance(l_hosts, Generator):
            l_hosts = self._create_gen(l_hosts)

        self._hosts: Generator = l_hosts
        self.lock: Lock = Lock()
        self.threads: list[Thread] = []
        self.valid: list[str] = []

    def _create_gen(self, iterable: Union[list, set, FrozenSet]) -> Generator:
        """
        Cette fonction permet de crée le generateur d'ips, permettant une
        execution plus rapide pour un grand nombre d'ips comparé a une
        liste classique.

        :param iterable: la 'liste' d'ip(s)
        :return: Generateur
        """
        yield from iterable

    def _get_new_socket(self) -> socket.socket:
        """
        Cette fonction permet de crée un nouveau socket avec un timeout de
        1s.

        :return: socket.socket
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        _log.debug("Created a new socket.")
        return s

    def start(self) -> Union[bool, list]:
        """
        Point d'entrée pour chaque instance de classe 'SocketWorker', cette
        fonction crée les threads et les lance.

        :return: une liste d'ips valides si aucune erreur
        """
        try:
            _log.info("Debut du check des ips")
            for _i in range(0, 50):
                t = Thread(target=self._check, args=())
                self.threads.append(t)
            for thread in self.threads:
                thread.start()
            for thread in self.threads:
                thread.join()
            alive_thread = []
            for thread in self.threads:
                if thread.is_alive():
                    _log.debug(f"{thread} is alive")
                    alive_thread.append(thread)
            _log.debug(f"{alive_thread=}")
            self.threads = alive_thread
            _log.info("Check des ips fini")
            _log.info(f"{len(self.valid)} Hosts détectés")
            return self.valid
        except Exception as e:
            _log.error(e)
            return False

    def _check(self) -> None:
        """
        Cette fonction est utilisé dans chaque thread, pour recuperer la
        prochaine valeur du generateur crée préalablement, check si cet
        host est 'up' puis ajoute l'host dans une liste d'hosts valides.

        :return: None
        """
        host = None
        running = True
        while running:
            with self.lock:
                try:
                    if self._hosts:
                        host = str(next(self._hosts)).strip()
                except StopIteration:
                    running = False
                    host = None
                except OSError as e:
                    if e.winerror == 10056:  # socket deja connecté
                        pass
                except Exception as e:
                    _log.error(e)

            if host:
                valid = self._check_host(host)

                if not valid:
                    continue

                with self.lock:
                    self.valid.append(host)

    def _check_host(self, host: str) -> bool:
        """
        Cette fonction essaye de connecter le socket creé vers l'host
        donné, si un timeout ou une erreur ce produit, l'host est down,
        sinon il est up.

        :param host: ipv4
        :return: True si l'host est up, sinon False
        """
        try:
            s = self._get_new_socket()
            _log.debug(f"Essai de connexion vers l'host {host}.")
            s.connect((host, 22))
        except TimeoutError:
            _log.debug(f"Connexion vers l'host {host} timed out.")
            return False
        except Exception as e:
            _log.debug(f"Erreur lors de la connexion vers l'host {host}: {e}")
            return False
        else:
            _log.debug(f"Succes lors de la connexion vers l'host {host}.")
            s.close()
            return True
