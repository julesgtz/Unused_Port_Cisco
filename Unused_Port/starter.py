import logging
import sys
from time import sleep
from typing import FrozenSet, Generator, Union

from Unused_Port.secrets import password, username
from Unused_Port.socket_worker import SocketWorker
from Unused_Port.ssh_worker import SSHWorker

_log = logging.getLogger(__name__)


def start_ssh_worker(ip: list[str], site=None):
    """
    Cette fonction lance la classe SSHWorker.

    :param ip: liste d'une ou plusieurs ips
    :param site: le site ('France' / 'US' ...)
    si il est fournis ( arg --auto utilisé)
    :return: None
    """
    worker = SSHWorker(ip_l=ip, username=username, password=password, site=site)
    worker.start()


def start(ip: Union[str, dict[str, FrozenSet], FrozenSet], exit=True, site=None):
    """
    Cette fonction est utilisée plusieurs fois si le --schedule est activé,.

    sinon seulement lors du lancement du script. Cette fonction permet de vider
    le cache du créateur des dossiers (si entre les X jours du schedule,
    quelqu'un a supprimer les dossiers sur le commun, le script les recréera).
    Il check si 'ip' est un dictionnaire, ce qui signifie qu'il faut l'unpack
    (site: list[ip]), puis utilise la récursion avec la liste d'ip unpack du
    dictionnaire. Il valide ensuite les ips, recupère seulement celles qui sont
    valides, puis lance le main. Si aucune ip n'est valide, le script est exit.

    :param ip: Un dictionnaire avec le site et l'ip a unpack, ou une liste d'une
    ou plusieurs ips contenu dans un Generator/ liste/ set, ou une ip seule
    :param exit: Si le script doit exit, False si --schedule, sinon True
    :param site: 'France' ... non obligatoire si la personne utilise pas --auto
    :return: None
    """
    if isinstance(ip, dict):
        for site, ips in ip.items():
            start(ips, exit, site)
        return
    _log.info(
        "Validation de(s) ip(s) donnée(s) {}...".format(
            f"pour le site {site}" if site else ""
        )
    )
    valid = validate_ip(ip)

    if not valid:
        _log.error("Host not available ... Exiting")

    if exit and not valid:
        _exit("Exit aucun host valide")

    _log.debug(f"Les ips valides sont {valid}, start du Worker SSH sur ces ips")
    start_ssh_worker(valid, site)  # type: ignore


def validate_ip(ip: Union[list, set, Generator, FrozenSet, str]) -> Union[bool, list]:
    """
    Cette fonction crée une instance de la classe SockerWorker avec une.

    liste d'ip en arguments, et lance la classe avec worker.start.

    :param ip: une ip seule / une liste d'ip dans une structure parmis
        'list , set, Generator et Frozenset'
    :return: False si l(es) ip(s) est(sont) invalide(s), sinon la liste
        de(s) ip(s) valide(s)
    """
    if isinstance(ip, str):
        ip = [ip]
    worker = SocketWorker(ip)
    return worker.start()


def _exit(e):
    """
    Cette fonction est utilisée pour exit le programme.

    :param e: l'erreur
    :return:
    """
    _log.error(f"Erreur : {e} detectée, le script va s' arreter dans 10s")
    sleep(10)
    sys.exit(0)
