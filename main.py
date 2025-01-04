# UTILISATION CLASSIQUE DU SCRIPT
# main.exe / main.py s'utilise avec les arguments --

import argparse
import logging
import sys
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Union

from Unused_Port.helper import (
    _exit,
    check_path,
    now,
    run_scheduler,
)
from Unused_Port.starter import start
from Unused_Port.static import (
    ADMIN_NETWORK,
    DAYS,
    DOSSIER_PARTAGE_SITE,
    HOSTS,
    INV_DAYS,
)

_log = logging.getLogger(__name__)

try:
    import schedule
except ImportError:
    import os

    _log.warning("Installation de schedule en cours ...")
    os.system("pip install schedule -q -q -q")
    import schedule

# TODO A FAIRE
# TODO: Voir comment integré le choix de la sortie dans l'input(ip) car on passe par un socket worker


def gen_parser():
    """
    Genère le parser pour les arguments (ex: main.py --auto --debug.

    --schedule Samedi),et renvoie les arguments sous la forme de classe ->
    attributs (args = gen_parser, args.auto -> bool).

    :return: Les arguments dans la classe 'Namespace'
    """
    parser = argparse.ArgumentParser("Switch Port Checker")
    parser.add_argument(
        "--auto",
        help="Prend automatiquement les ips du réseau France admin",
        action="store_true",
    )
    parser.add_argument("--debug", help="Affiche le debug", action="store_true")
    parser.add_argument(
        "--schedule",
        help="Permet lancer une plannification du lancement du script tous les X jours",
    )
    return parser.parse_args()


def get_ip_input() -> str:
    """
    Récupère l'ip en tant qu'input si l'utilisateur n'a pas séléctionner
    --auto, puis verifie si c'est une ip et si elle est bien dans le réseau
    France, sinon redemande une ip.

    :return: l'ip sous forme str()
    """
    ip = None

    while not ip:
        ip = str(input("Renseigner l'ip du switch : "))
        try:
            ip_address(ip)
        except ValueError:
            _log.warning(f"L'ip {ip} n'est pas une ip !")
            ip = None
        else:
            if not any(ip_address(ip) in network for network in ADMIN_NETWORK):
                _log.warning(f"L'ip {ip} n'est pas dans le subnet France")
                ip = None
    return ip


def get_real_schedule_type(t: Union[int, str]) -> Union[int, str]:
    """
    Cette fonction permet de savoir si la personne a mis --schedule.

    Exemple : --schedule 5 pour 5 jours ou --schedule Samedi pour tous les Samedi.
    il check si 't' peut être un int, sinon c'est un str.

    :param t: l'arg --schedule, 'samedi', 5 par ex
    :return: str si c'est un jour, int si c'est tous les X jours
    """
    try:
        t = int(t)
        return t
    except ValueError:
        assert type(t) is str
        return t.lower()


if __name__ == "__main__":
    try:
        if not (p := Path("logs")).exists():
            p.mkdir()
        args = gen_parser()
        if args.debug:  # Set le level a debug , --debug a été appliqué
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(f"logs/{now()}.log"),
                    logging.StreamHandler(sys.stdout),
                ],
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(f"logs/{now()}.log"),
                    logging.StreamHandler(sys.stdout),
                ],
            )
            _log.warning(
                "Il est fortement conseillé de run le script en mode debug '--debug', "
                "pour tout enregistrer dans le fichier de log"
            )

        exit_path: bool = check_path(DOSSIER_PARTAGE_SITE)
        if exit_path:
            _exit("Au moins 1 Path invalide detecté")

        ip: Any
        if args.auto:
            _log.debug("args --auto detecté, utilisation de la pool réseau France")
            ip = HOSTS
        else:
            ip = get_ip_input()

        if args.schedule:
            scheduled = get_real_schedule_type(args.schedule)
            if isinstance(scheduled, str):
                if not (day := INV_DAYS.get(scheduled)) and scheduled not in DAYS:
                    # Signifie que l'utilisateur n'a pas
                    # défini un jour en Francais ou en anglais
                    _exit(
                        f"Il faut que vous choississez soit un chiffre "
                        f"pour run le script tous les X jours, "
                        f"soit un jour parmi {list(INV_DAYS.keys())} ou"
                        f" {list(DAYS.keys())}, {scheduled} ne convient pas"
                    )

                getattr(schedule.every(), day or scheduled).at("18:00").do(
                    start, ip, False
                )
                # schedule.every(1).minutes.do(start, ip, False) debug
            elif isinstance(scheduled, int):
                schedule.every(scheduled).days.at("18:00").do(start, ip, False)

            fmt_day = "jours" if isinstance(scheduled, int) else ""
            fmt = "les ips du subnet France" if type(ip) is not str else f"l'ip {ip}"
            _log.info(
                f"Le script va s'executer automatiquement tous les "
                f"{scheduled}{fmt_day} à 18h00 sur {fmt}"
            )

            run_scheduler()

        else:
            start(ip)

    except KeyboardInterrupt:
        _exit("KeyboardInterrupt, ctrl C appuyé")

    except Exception as e:
        _exit(e)

#  pydocstringformatter -w .\port_checker.py
#  docformatter -i .\port_checker.py
#  pyinstaller -F -n Port_Unused ..\main.py
#  pyarmor gen --pack onefile -O exe service.py
