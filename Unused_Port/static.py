import os
from ipaddress import IPv4Address, ip_network
from pathlib import Path
from typing import ClassVar, FrozenSet, LiteralString, Union


def ip_split(ip: str) -> list[str]:
    """
    Cette fonction prend une range d'ip (192.168.1.1-192.168.1.254) et renvoie la liste
    d'ips.

    contenu dans la range [192.168.1.1,192.168.1.2,...,192.168.1.254]
    :param ip: Une range d'ip (192.168.1.1-192.168.1.254)
    :return: liste d'ips
    """
    start_ip, end_ip = ip.split("-")
    start = IPv4Address(start_ip)
    end = IPv4Address(end_ip)
    return [str(IPv4Address(ip)) for ip in range(int(start), int(end) + 1)]


def get_ip(ips: list):
    """
    Recupere toutes les ips d'une listes, et les combinent dans une seule
    liste, les ranges d'ips défaites.

    :param ips: une liste d'ips
    :return: une liste d'ips
    """
    result = []
    for ip in ips:
        if "-" in ip:
            result += ip_split(ip)
        else:
            result.append(ip)
    return result


ADMIN_NETWORK: tuple = (ip_network("192.168.1.0/24"),)

EXCLUDE_IP_TEMP: list = [
    "192.168.1.1-192.168.1.10",
]

EXCLUDE_IP: list = get_ip(EXCLUDE_IP_TEMP)

HOSTS: dict[str, FrozenSet] = {
    "France": frozenset(
        host
        for host in ip_network("192.168.1.0/24").hosts()
        if str(host) not in EXCLUDE_IP
    ),
    "US": frozenset(
        host
        for host in ip_network("192.168.100.0/24").hosts()
        if str(host) not in EXCLUDE_IP
    ),
}

DOSSIER_PARTAGE_SITE: dict[str, list[Path]] = {
    "France": [Path(r"\\srv\Network\Tools\Port_Unused\France")],
    "US": [
        Path(r"\\srv\Network\Tools\Port_Unused\US"),
        Path(r"\\srv\Network\Tools\Port_Unused\US2"),
    ],
}

UPTIME_MIN_WEEK: int = 12

DAYS: dict = {
    "monday": "lundi",
    "tuesday": "mardi",
    "wednesday": "mercredi",
    "thursday": "jeudi",
    "friday": "vendredi",
    "saturday": "samedi",
    "sunday": "dimanche",
}

INV_DAYS: dict = {k: v for v, k in DAYS.items()}

FULL_PATH = os.path.join(os.environ["ALLUSERSPROFILE"], "Unused_Port")
_DIRS = ["txt_output", "excel_output", "local_save", "logs"]


class DIRS:
    """
    Classe pour la gestion des paths des directory utilisés par le script en local.

    Si c'est un service, alors il génère les paths, dans un endroit commun
    a tous les users, sinon il crée là où le script est exécuté.
    """

    service = False

    # service = True
    _values: ClassVar[dict[str, Union[LiteralString, str]]] = {}

    @classmethod
    def _gen_values(cls):
        """Méthode pour générer les valeurs pour DIRS._values."""
        if cls.service:
            cls._values = {d: os.path.join(FULL_PATH, d) for d in _DIRS}
        else:
            cls._values = {d: os.path.join(os.getcwd(), d) for d in _DIRS}

    @classmethod
    def get(cls, item):
        """Methode dict.get mais génère les valeurs si elles n'existent pas."""
        if not cls._values:
            cls._gen_values()
        return cls._values.get(item)

    @classmethod
    def values(cls):
        """Methode dict.values mais génère les valeurs si elles n'existent pas."""
        if not cls._values:
            cls._gen_values()
        return cls._values.values()

    @classmethod
    def items(cls):
        """Methode dict.items mais génère les valeurs si elles n'existent pas."""
        if not cls._values:
            cls._gen_values()
        return cls._values.items()


DELETE_AFTER: int = 30  # days

if __name__ == "__main__":
    pass
