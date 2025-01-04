import logging
from threading import Lock, Thread

from Unused_Port.helper import _exit, save_wb
from Unused_Port.port_checker import UnusedPortChecker

_log = logging.getLogger(__name__)


def _check(**kwargs) -> UnusedPortChecker:
    """
    Cette fonction crée une instance de la classe 'UnusedPortChecker'
    avec les kwargs emit dans cette fonction, appelle la methode .check()
    de cette instance et retourne l'instance.

    :param kwargs: hostname, username, password et la stdout
    :return: instance de classe 'UnusedPortChecker'
    """
    upc = UnusedPortChecker(**kwargs)
    upc.check()
    return upc


class SSHWorker:
    """
    Threaded SSH Worker, cette classe utilise les threads pour instancier
    simultanément 'Unused Port Checker' avec des ips différentes, et s'occupe
    de crée l'excel si l'host est valide.
    """

    def __init__(
        self,
        ip_l: list[str],
        *,
        username: str,
        password: str,
        stdout: str = "default",
        site=None,
    ):
        """
        Instancie la classe 'SSHWorker' et crée une Lock pour les threads.

        :param ip_l: une liste d'ip
        :param username: l'username du compte
        :param password: le password du compte
        :param stdout: la sortie voulu 'excel', 'console', 'txt'
        :param site: le site 'France', 'Paris' ...
        """
        self._ip_l: list[str] = ip_l
        self._username: str = username
        self._password: str = password
        self._stdout: str = stdout
        self._site = site
        self.lock: Lock = Lock()
        self.threads: list[Thread] = []

    def start(self) -> None:
        """
        Point d'entrée pour les instances de cette classe, crée les threads
        et les starts.

        :return: None
        """
        try:
            _log.info("Debut du processus, generation des workers SSH")
            for _i in range(0, 50):
                t = Thread(target=self._start, args=())
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
        except Exception as e:
            _exit(e)

    def _start(self) -> None:
        """
        Pour chaque ip dans self._ip_l, cette fonction va recuperer la
        premiere valeur de la liste (une ip) et va appeler la fonction
        _validate_ip(ip).

        :return: None
        """
        ip = None
        running = True
        while running:
            with self.lock:
                try:
                    if self._ip_l:
                        ip = self._ip_l.pop()
                    else:
                        running = False
                        ip = None
                except Exception as e:
                    _log.error(e)

            if ip:
                try:
                    self._validate(ip)
                except Exception as e:
                    _log.error(e)

    def _validate(self, ip: str) -> None:
        """
        Cette fonction est utilisée pour valider une ip, elle prend une ipv4
        en parametre, crée recupere une instance d'upc avec la fonction
        _check(), verifie que upc.valid est True (ce qui signifie qu'une sortie
        standard est disponible) puis genere le fichier excel en supprimant la
        premiere page de l'excel (c'est une page non nécessaire, uniquement la
        pour que l'excel soit généré avec forcement une page).

        Cette fonction ensuite stop l'instance de classe avec upc.stop()
        :param ip: une ipv4
        :return: None
        """
        _log.debug(f"SSHWorker check l'ip {ip}")
        self.hostname = ip
        upc = _check(
            hostname=ip,
            username=self._username,
            password=self._password,
            stdout=self._stdout,
        )
        if upc.valid:
            wb = upc.get_stdout()
            if wb:
                del wb[wb.sheetnames[0]]
                if wb.worksheets:
                    save_wb(wb, site=self._site, hostname=upc.real_hostname or ip)
                else:
                    _log.warning(
                        f"Attention, l'excel est vide pour la liste "
                        f"d'ip(s) : {self._ip_l} "
                        f"(sans doute que les/l' ip(s) données ont toutes un uptime "
                        f"inférieur a 3 mois / Equipement non Cisco),"
                        f"aucun enregistrement sera effectué"
                    )


if __name__ == "__main__":
    pass
