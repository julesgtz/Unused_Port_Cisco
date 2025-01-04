import ipaddress
import logging
import os
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from time import sleep
from typing import Any, Callable, Optional, Union

import schedule
import servicemanager

from Unused_Port.errors import (
    UPC_RETRY_ERROR,
    UPC_SSH_CONNEXION_ERROR,
    UPC_VALIDATION_ERROR,
)
from Unused_Port.shared_folder import Shared_Folder
from Unused_Port.static import DELETE_AFTER, DIRS, DOSSIER_PARTAGE_SITE

_log = logging.getLogger(__name__)

try:
    from openpyxl import Workbook
except ImportError:
    _log.warning("Installation de openpyxl en cours ...")
    os.system("pip install openpyxl -q -q -q")
    from openpyxl import Workbook


def retry(max_retries, delay=0.5) -> Callable:
    """
    Décorateur permettant de retry une fonction X fois, tant que celle çi
    raise une erreur, sinon return son résultat.

    :param max_retries: Le nombre max d'essais avant de renvoyer
        l'erreur
    :param delay: le délai en seconde entre chaque essai
    :return: Le resultat de la fonction / sinon l'erreur
    """

    def decorator(func: Callable):
        def wrapper(*args, **kwargs) -> Any:
            result = None
            for _ in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                except (
                    UPC_RETRY_ERROR,
                    UPC_SSH_CONNEXION_ERROR,
                    UPC_VALIDATION_ERROR,
                ) as e:
                    _log.warning(f"{e}, RETRYING {func.__name__}({args}, {kwargs})")
                    sleep(delay)
                except Exception as e:
                    _log.warning(
                        f"{e.__class__.__name__}, RETRYING {func.__name__}"
                        f"({args}, {kwargs})"
                    )
                    sleep(delay)
                else:
                    return result
            _log.warning(f"Max Retry {func.__name__}({args}, {kwargs})")
            return result

        return wrapper

    return decorator


def recurse_folder_creator(
    path: Union[Path, str],
    checker=1,
    base=None,
    dossier_partage: Union[bool, str] = True,
):
    r"""
    Cette fonction est utilisée pour vérifier si tous les dossiers d'un
    path existe.

    Si un path n'existe pas, la fonction va crée tous les dossiers
    nécessaire jusqu'au path (ex: toto/bar/foo/tata, si seulement toto/
    existe, alors il créera respectivement /bar , /foo, /tata pour
    obtenir le path de base toto/bar/foo/tata) en utilisant la
    récurisivite.

    Note: Path(path).mkdir(parents=True) aurait fait pareil que toute cette fonction ...

    :param path: le full path d'un dossier (ex:
        '\\\\Network\\Tools\\toto\\tata\\toto\\tata')
    :param checker: L'index a partir duquel le script check si le path
        existe
    :param base: le path splité dans une liste
    :param dossier_partage: bool : permettant de savoir si il faut
        rajouter \\\\ devant
    :return: True si tout est bon sinon raise une Exception
    """
    if isinstance(path, Path):
        path = str(path)
    path = path.replace("/", "\\")
    if not path:
        return
    if not base:
        base = [folder for folder in path.split("\\") if folder]
    if dossier_partage:
        dossier_partage = "\\\\"
        if checker == 1:
            checker += 1
    else:
        dossier_partage = ""
    tester = dossier_partage + "\\".join(base[:checker])
    new_path = Path(tester)

    if tester == path and new_path.exists():
        return True

    if new_path.exists():
        return recurse_folder_creator(
            path,
            checker=checker + 1,
            base=base,
            dossier_partage=dossier_partage,
        )
    else:
        try:
            new_path.mkdir()
        except Exception as e:
            raise e
        return recurse_folder_creator(
            path,
            checker=checker + 1,
            base=base,
            dossier_partage=dossier_partage,
        )


def local_save(site: str, path=None) -> Optional[Path]:
    """
    Cette fonction est utilisé quand le save sur le dossier partagé ne
    marche pas (a cause des droits ou autres), il renvoie le path adéquat pour
    save sur la machine en local.

    :param site: le site 'France' ...
    :param path: de base '%localappdata%/local_save' mais peut être changé.
    Endroit où le dossier 'site' sera crée
    :return: le Path si celui ci est bien crée sinon None
    """
    try:
        if not path:
            path = DIRS.get("local_save")
        path = os.path.join(path, site)
        recurse_folder_creator(path, dossier_partage=False)
        return Path(path)
    except Exception as e:
        _log.error(f"{e} lors du local save, pass")
        return None


@lru_cache(maxsize=16)
@retry(max_retries=2, delay=0)
def site_folder_manager(site: str) -> Optional[Union[Path, list[Path]]]:
    """
    Cette fonction check pour un site, si un dossier partagé est fournis,
    check si les dossiers existent avec recurse_folder_creator(), sinon save en
    local.

    :param site: Le site 'France' ...
    :return: Le path pour permettre a la fonction qui appel de save un fichier
    """
    if path_partage := DOSSIER_PARTAGE_SITE.get(site.capitalize()):
        try:
            for path in path_partage:
                shared = Shared_Folder(path.parent)
                if e := shared.error:
                    return _exit(e)
                if shared.connect():
                    if not path.exists():
                        _log.info(
                            f"Création du dossier car {path} "
                            f"n'existe pas, site : {site}"
                        )
                        recurse_folder_creator(path)
                else:
                    return local_save(site=site)
            return path_partage
        except Exception as e:  # enregistre en local <- PermissionError
            _log.warning(
                f"Enregistrement local, erreur lors de la création "
                f"du dossier {path_partage} pour le site {site} {e}"
            )
            return local_save(site=site)
    else:
        _log.warning(
            f"Aucun dossier sur un serveur commun reférencer "
            f"pour le site {site}, enregistrement en local"
        )
        base = os.path.join(DIRS.get("excel_output"), site)
        path = Path(base)
        try:
            if not path.exists():
                _log.info(
                    f"Création du dossier car {path_partage} "
                    f"n'existe pas, site : {site}"
                )
                recurse_folder_creator(path, dossier_partage=False)
            return [path]
        except Exception:
            _log.warning(
                f"Enregistrement local, erreur lors de la "
                f"création du dossier local pour le site {site}"
            )
            return local_save(site=site)


def generate_base_folder():
    """
    Cette fonction est utilisée pour générer les dossiers de bases contenu
    dans static.DIRS.

    :return: exception si une exception est catch
    """
    try:
        for path in DIRS.values():
            if not (p := Path(path)).exists():
                p.mkdir()
                _log.info(f"Création du dossier {p}")
    except Exception as e:
        return e


def _exit(e):
    """
    Cette fonction est utilisée pour exit le programme.

    :param e: l'erreur
    :return:
    """
    _log.error(f"Erreur : {e} detectée, le script va s' arreter dans 10s")
    sleep(10)
    sys.exit(0)


def save_wb(
    _workbook: Workbook,
    *,
    _now: Optional[str] = None,
    site: Optional[str] = None,
    hostname: str = "error",
    new_name: bool = False,
) -> bool:
    """
    Cette fonction est utilisée pour save un fichier excel.

    :param _workbook: La classe Workbook permettant de save un excel
    :param _now: la date d'aujourd'hui formattée
    :param site: le site 'France' ...
    :param hostname: L'hostname du switch (et non son ip)
    :param new_name: le nouveau nom si cette fonction rencontre une erreur
    (le fichier ne peut pas etre ecrasé car qq l'a ouvert)
    :return: False si aucune erreur sinon récursion sur elle meme pour gerer l'erreur
    """
    if not _now:
        _now = now()
    try:
        from random import randint

        if not site:
            location = (
                os.path.join(DIRS.get("excel_output"), f"{hostname}_{_now}")
                if not new_name
                else os.path.join(
                    DIRS.get("excel_output"),
                    f"{hostname}_{_now}_{randint(100, 999)}",
                )
            )
            _workbook._sheets.sort(key=lambda ws: ipaddress.IPv4Address(ws.title))  # type: ignore
            _workbook.save(f"{location}.xlsx")
            _log.info(f"Excel bien enregisté sous le nom de : {location}.xlsx")
        else:
            l_path = site_folder_manager(site)
            if not l_path:
                return False

            location = (
                f"/{hostname}" if not new_name else f"/{hostname}_{randint(100, 999)}"
            )

            for path in l_path:
                path = str(path) + location + ".xlsx"
                _workbook.save(f"{path}")
                _log.info(f"Excel bien enregisté sous le nom de : {path}")
        sleep(5)
        return True
    except OSError as e:  # Ouvert par qq d'autre
        if e.winerror == 2:
            err = generate_base_folder()
            if err:
                _exit(err)
        _log.warning(
            f"{hostname}.xlsx est ouvert par quelqu'un d'autre, "
            f"enregistrement sous avec 3 chiffres random a la fin, {e}"
        )
        return save_wb(_workbook, site=site, hostname=hostname, new_name=True)
    except Exception as e:
        _log.error(e)
        return False


def now() -> str:
    """Cette fonction crée le formattage de la date d'aujourd'hui."""
    return datetime.now().strftime("%d-%m-%Y")


def remove_old_files(after: int = DELETE_AFTER) -> bool:
    """Cette fonction delete tous les logs qui date de 'after' jours."""
    path = DIRS.get("logs")
    files = [
        file
        for file in os.listdir(path)
        if os.path.isfile(os.path.join(path, file)) and file.endswith(".log")
    ]
    max_date = datetime.today() - timedelta(days=after)
    for file in files:
        suffix = file.index(".log")
        date_obj = datetime.strptime(file[:suffix], "%d-%m-%Y")
        if max_date > date_obj:
            try:
                os.remove(os.path.join(path, file))
                _log.debug(
                    f"Le fichier {file} a été supprimé avec succés "
                    f"(fichier datant de + de {after} jours)"
                )
            except Exception as e:
                _log.error(f"remove_old_files : {e}")
    return True


def check_path(paths: dict[str, list[Path]]) -> bool:
    """
    Cette fonction est utilisée quand l'arg --auto est mis.

    Il check pour chaque path de la variable paths existe, si le path
    n'existe pas, il essaye de le crée avec la fonction
    'site_folder_manager(site)', si cette fonction est un echec, alors
    il affiche un message d'erreur et le script s'arrete.

    :param paths: {'France': pathlib.Path('foo/bar')} , il va check si
        le path des valeurs du dict existent
    :return: bool, l'exit status, si le script doit s'arreter ou non
    """
    exit_status = False
    for site, l_path in paths.items():
        for path in l_path:
            if site_folder_manager(site):
                continue
            exit_status = True
            _log.info(f"Le path {path} pour le site {site} n'existe pas")
    err = generate_base_folder()
    if err:
        _exit(err)
    return exit_status


def run_scheduler(delay=5, value_to_match=True):
    """
    Cette fonction est la fonction qui check toutes les 5 secondes si un
    job.

    doit se lancer, avec le --schedule, des jobs sont crée, et son
    lancé depuis cette fonction.

    :return: None
    """
    _last_next: tuple[datetime | None, datetime | None] = (None, None)
    day = _get_day()

    while value_to_match:
        sleep(delay)
        if day != _get_day() and (
            (next_run := _last_next[1])
            and isinstance(next_run, datetime)
            and next_run.date() == datetime.today().date()
        ):
            day = _get_day()
            remove_old_files()
            _create_logging()

        jobs = schedule.get_jobs()
        for (
            job
        ) in jobs:  # Toujours un seul job, donc cette ligne pourrait etre job = jobs[0]
            if _last_next != (job.last_run, job.next_run):
                _last_next = (job.last_run, job.next_run)
                _service_log_both(
                    f"last run: {job.last_run}, "
                    f"next run: {job.next_run}, "
                    f"start day: {job.start_day}"
                )
        schedule.run_pending()


def _get_day() -> str:
    """Récupère le numéro du jour."""
    return datetime.today().strftime("%d")


def _create_logging():
    """Recréer une configuration en fonction du jour."""
    logger = logging.getLogger()
    if logger.hasHandlers():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    handler = logging.FileHandler(os.path.join(DIRS.get("logs"), f"{now()}.log"))
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def _service_log_both(msg):
    """Log le message dans la console ainsi que dans le service manager."""
    _log.debug(msg)
    servicemanager.LogInfoMsg(msg)


if __name__ == "__main__":
    pass
