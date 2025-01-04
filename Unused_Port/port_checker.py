import logging
import os
import re
from time import sleep
from typing import ClassVar, Optional, Union

from Unused_Port.base import BaseConnexion
from Unused_Port.errors import (
    UPC_SSH_CONNEXION_ERROR,
    UPC_UNKNOWN_ERROR,
    UPC_UP_TIME_ERROR,
    UPC_VALIDATION_ERROR,
)
from Unused_Port.helper import now, retry
from Unused_Port.static import UPTIME_MIN_WEEK
from Unused_Port.stdout import Stdout

_log = logging.getLogger(__name__)

try:
    from paramiko import AutoAddPolicy
except ImportError:
    _log.warning("Installation de paramiko en cours ...")
    os.system("pip install paramiko -q -q -q")
    from paramiko import AutoAddPolicy

try:
    from openpyxl import Workbook
except ImportError:
    _log.warning("Installation de openpyxl en cours ...")
    os.system("pip install openpyxl -q -q -q")
    from openpyxl import Workbook


# Ne pas utiliser les | include car cela ne marche pas (dans les commandes)


class UPC_Commands:
    """Liste des commandes utilisées par UPC, 'Unused Port Checker'."""

    # SH_INT = "show int status | i notconnect"
    # SH_LAST_INT = "show int {} | i Last input"
    SH_INT = "show int status"
    SH_LAST_INT = "show int {}"
    SH_VERSION = "show version"


class UPC_Regex:
    """Liste des regex utilisés par UPC, 'Unused Port Checker'."""

    INT_REGEX = (
        r"^([a-zA-Z]{1,4}[0-9]/[0-9]{1,2}(?:/[0-9]{1,2})"
        r"?)\s+\S*\s+(connected|notconnect|disabled)"
    )
    LAST_REGEX = r"Last input (\S+),"
    UPTIME_REGEX = r"uptime is(?: (\d+) year(?:s)?,)?(?: (\d+) week(?:s)?)?(?:$|,)"
    HOSTNAME_ON_UPTIME_REGEX = r"(\S+)?\s?uptime is"
    VALIDATOR_UPTIME = r"uptime is"


class UnusedPortChecker(BaseConnexion):
    """
    Classe héritante de la classe BaseConnexion.

    C'est cette classe qui va faire les commandes sur le
    switch depuis la connexion ssh crée par 'BaseConnexion'.
    """

    _excel_stdout: ClassVar[list[str]] = ["excel", "default"]
    _txt_stdout: ClassVar[list[str]] = ["txt", "default"]
    _console_stdout: ClassVar[list[str]] = ["console", "default"]

    def __init__(
        self,
        workbook: Optional["Workbook"] = None,
        stdout: str = "default",
        **kwargs,
    ):
        """
        Instancie la classe UnusedPortChecker (UPC).

        :param stdout: Choix entre "default", "excel", "txt", "console".
        "default" va essayer la premiere sortie "excel" et si elle
        ne marche pas, essayerai la deuxieme ...

        :param workbook: Choix ou non de mettre un Workbook,
        ceci permet de mettre tous les switch dans un meme fichier excel

        :param kwargs: Permet de remplir les requirements
        de la methode __new__ de la classe parent
        """
        if stdout not in Stdout.choices:
            _log.warning(f"stdout '{stdout}' n'existe pas, utilisation de 'default'")
            self.stdout = "default"

        if not workbook:
            workbook = Workbook()

        self.workbook = workbook

        self._comp = re.compile(UPC_Regex.LAST_REGEX)
        self._upcompile = re.compile(UPC_Regex.UPTIME_REGEX)
        self._valicompile = re.compile(UPC_Regex.VALIDATOR_UPTIME)
        self._hostcompile = re.compile(UPC_Regex.HOSTNAME_ON_UPTIME_REGEX)

        self.stdout = stdout
        self._output: list[tuple[str, str]] = []
        self._uptime = "(surement appareil non cisco)"
        self.real_hostname = ""
        self._now = now()

        super().__init__(**kwargs)

    def check(self) -> bool:
        """
        Cette fonction est le point d'entrée lorsque la classe est instanciée.

        Elle gere la connexion au switch en appelant la
        methode _connect() de la classe parente, puis en appelant la
        methode _check().

        Cette fonction gere aussi les erreurs
        :return: False/ Une exception si une erreur sinon True
        """
        self.set_missing_host_key_policy(AutoAddPolicy)
        exc = self._connect()
        if exc is None:
            raise UPC_SSH_CONNEXION_ERROR(
                f"Erreur lors de la connexion SSH au switch : {self._hostname}"
            )

        try:
            self._check()
            return True
        except UPC_UP_TIME_ERROR as e:
            _log.warning(f"{e}")
            self._uptime = f"Uptime insuffisant, {self._uptime}"
            self.valid = True
            return False
        except UPC_VALIDATION_ERROR as e:
            _log.warning(f"{e}")
            self.valid = True
            self._uptime = (
                f"L'équipement n'a aucune "
                f"interface non utilisée, uptime :"
                f" {self._uptime}"
            )
            return False
        except Exception as e:
            _log.error(f"Erreur lors de la vérification des ports non utilisés : {e}")
            self.valid = False
            return False
        finally:
            self.stop()

    @retry(max_retries=3, delay=0.3)
    def _get_int(self) -> Optional[list]:
        """
        Cette fonction permet de recuperer la liste des interfaces
        'notconnect' sur un switch.

        :return: None si aucune interface n'est trouvé, sinon une list
            d'interfaces
        """
        _log.debug(
            f"Récuperation des interfaces pour l'host : "
            f"(ip: {self._hostname}, hostname: {self.real_hostname})"
        )
        raw_int = self._exec_command(UPC_Commands.SH_INT)
        ints = self._list_int(raw_int)
        return ints

    def _check(self):
        """
        Cette fonction est utilisée par le point d'entrée check().

        C'est cette fonction qui va faire le lien entre toutes les
        methodes de classes nécessaire pour recuperer les interfaces
        non utilisées sur le switch.

        :return: raise une erreur si un probleme est trouvé
        """
        self._shell = self.invoke_shell(width=1000, height=1000)
        self._shell.set_combine_stderr(True)

        valid = self._uptime_checker()
        if not valid:
            raise UPC_UP_TIME_ERROR(
                f"Uptime minimum est de {UPTIME_MIN_WEEK} weeks, "
                f"uptime de (ip: {self._hostname}, hostname: "
                f"{self.real_hostname}), est {self._uptime}"
            )

        _log.info(
            f"Uptime de (ip: {self._hostname}, hostname: "
            f"{self.real_hostname}) est {self._uptime}, continuons ..."
        )

        ints = self._get_int()
        if not ints:
            raise UPC_VALIDATION_ERROR(
                f"L'équipement n'a aucune interface non utilisée, "
                f"(ip: {self._hostname}, hostname: {self.real_hostname})"
            )

        _log.info(
            f"La liste des interfaces pour (ip: {self._hostname}, "
            f"hostname: {self.real_hostname}) est de {len(ints)} "
            f"interfaces, check du last input de chaque interface ..."
        )
        _log.debug(
            f"ints {ints} pour (ip: {self._hostname}, hostname: {self.real_hostname})"
        )

        for _int in ints:
            if not self._int_value_pass(_int=_int):
                continue
            last_input = self._int_checker(_int=_int)
            if last_input:
                self._output.append((_int, last_input))
                _log.debug(
                    f"int {_int} last_input {last_input} (ip: {self._hostname}, hostname: {self.real_hostname})"
                )

        _log.info(
            f"{len(self._output)} interfaces non utilisées depuis "
            f"plus de 3 mois trouvées pour l'host (ip: "
            f"{self._hostname}, hostname: {self.real_hostname})"
        )

    def _uptime_validator(self, data: str) -> Optional[bool]:
        """
        Cette fonction recupere la data d'une commande.

        Retourne True si l'uptime du switch concorde avec
        les attentes de 'UPTIME_MIN_WEEK' dans static.py,
        en week sinon False.

        :param data: Résultat d'une commande
        :return: True si l'uptime est bon, False sinon
        """
        _log.debug(
            f"Validation de l'uptime pour l'host : "
            f"{self._hostname} et recupération de l'hostname"
        )
        match = self._valicompile.search(data)
        if not match:  # Signifie que la data que l'on recoit n'est pas bonne / pas un appareil cisco (palo ne comprend pas 'sh ver')
            raise UPC_VALIDATION_ERROR("_uptime_validator(), data incomplete")

        match = self._hostcompile.search(data)
        if not match:
            return False
        hostname = match.group(1)
        if hostname and not self.real_hostname:
            self.real_hostname = hostname

        match = self._upcompile.search(data)
        self._uptime = "< 1 week"
        if not match:
            return False
        year, week = match.groups()
        self._uptime = f"{year} year, {week} week(s)" if year else f"{week} week(s)"
        if not week:
            return False
        if int(week) < UPTIME_MIN_WEEK and not year:
            return False
        else:
            return True

    @retry(max_retries=5, delay=0.5)
    def _uptime_checker(self) -> Optional[bool]:
        """
        Cette fonction gere la vérification de l'uptime, avec un retry si
        la data n'est pas entiere.

        :return: True / False si l'uptime est bon , None si aucun uptime
            trouvé
        """
        _log.debug(f"Verification de l'uptime pour l'host : {self._hostname}")
        uptime_raw = self._exec_command(UPC_Commands.SH_VERSION, delay=0.5)
        valid = self._uptime_validator(uptime_raw)
        return valid

    def _int_value_pass(self, _int: str):
        """
        Cette fonction check pour chaque interface si celle ci est 'bonne'.

        Les interfaces gi1/0/x avec x>48 et gi1/x/y avec x != 0 ne sont
        pas 'bonnes'.

        :param _int: l'interface (ex : gi1/0/2)
        :return: True si c'est bon, False sinon
        """
        try:
            _i = _int.split("/")
            if not len(_i) == 3:
                return True
            if int(_i[1]) > 0 or int(_i[2]) > 48:
                return False
            return True
        except Exception as e:
            raise UPC_UNKNOWN_ERROR(str(e)) from e

    @retry(max_retries=5, delay=0.3)
    def _int_checker(self, _int: str) -> Optional[Union[str, bool]]:
        """
        Cette fonction gere le check du last input de l'interface '_int'.

        :param _int: l'interface (ex : gi1/0/2)
        :return: retourne le last input si celui ci est bon, sinon False
            / None
        """
        _log.debug(
            f"Verification de l'uptime de l'interface "
            f"{_int} de l'host : (ip: {self._hostname}, "
            f"hostname: {self.real_hostname})"
        )
        last_input_raw = self._exec_command(UPC_Commands.SH_LAST_INT.format(_int))
        last_input = self._last_input_checker(last_input_raw)
        return last_input

    def stop(self) -> None:
        """
        Cette fonction est utilisée pour stopper l'instance en cours, en.

        appelant la fonction 'close()' de SSHClient et '_stop()' de
        base.py.

        :return:
        """
        self.close()
        self._stop()
        _log.debug("UnusedPortChecker arrêté.")

    def _exec_command(self, cmd, *, delay: float = 0.2) -> str:
        """
        Cette fonction est utilisée pour executer les commandes.

        Elle attend 'delay' en secondes, puis lit la data dans son buffer,
        la decode puis la return.

        :param cmd: la commande a envoyer
        :param delay: le delais en seconde
        :return: Le resultat de la commande
        """
        _log.debug(
            f"Exécution de la commande : {cmd} sur "
            f"(ip: {self._hostname}, hostname: {self.real_hostname})"
        )
        self._shell.sendall(cmd + "\r\n")
        while not self._shell.recv_ready():
            sleep(0.1)
        sleep(delay)
        # Sans ce délai , le shell renvoie son buffer meme si il n'a pas encore tout recu -> perte de data
        stdout = self._shell.recv(65535).decode("utf-8")
        return stdout

    def _list_int(self, raw_int: str) -> Optional[list]:
        """
        Cette fonction check si la data reçu est bonne et entiere,
        sinon raise une erreur.

        Puis check pour chaque interface si celle çi
        est 'notconnect', si c'est le cas, elle l'ajoute a la liste
        retournée.

        :param raw_int: La data de la commande 'sh int status'
        :return: une liste d'interfaces 'notconnect'
        """
        _log.debug(
            f"Récuperation des interfaces 'notconnect' "
            f"pour l'host : (ip: {self._hostname}, hostname: {self.real_hostname})"
        )
        result: list[str] = []
        if not re.search(UPC_Regex.INT_REGEX, raw_int, re.MULTILINE):
            raise UPC_VALIDATION_ERROR(
                f"_list_int(), data incomplete "
                f"(ip: {self._hostname}, hostname: {self.real_hostname})"
            )
        for match in re.finditer(UPC_Regex.INT_REGEX, raw_int, re.MULTILINE):
            interface, status = match.groups()
            if status == "notconnect":
                result.append(interface)
        return result

    def _last_input_checker(self, _input: str) -> Optional[Union[bool, str]]:
        """
        Cette fonction est utilisée pour sortir le last input du résultat
        de la commande 'sh int X'.

        :param _input: La data de la commande 'sh int X'
        :return: False si le last input convient pas, le last input si
            c'est bon, sinon raise une erreur si data incomplete
        """
        raw_last_input = self._comp.search(_input)
        try:
            assert raw_last_input
            last_input = raw_last_input.group(1)
        except (AttributeError, AssertionError) as e:
            raise UPC_VALIDATION_ERROR(
                f"_last_input_checker(), data incomplete "
                f"(ip: {self._hostname}, hostname: {self.real_hostname})"
            ) from e
        except Exception as e:
            raise UPC_VALIDATION_ERROR(
                f"_last_input_checker(), {e} (ip: "
                f"{self._hostname}, hostname: {self.real_hostname})"
            ) from e
        if last_input == "never":
            return last_input

        if "w" not in last_input:
            return False
        try:
            tps = int(last_input.split("w")[0])
        except TypeError:
            return False
        except Exception as e:
            raise UPC_UNKNOWN_ERROR(
                f"{e!s} (ip: {self._hostname}, hostname: {self.real_hostname})"
            ) from e

        return last_input if tps > UPTIME_MIN_WEEK else False

    def get_stdout(self) -> Optional["Workbook"]:
        """
        Cette fonction permet de recevoir la sortie standard de l'instance.

        Si self.stdout est 'excel', cette fonction crée
        la page excel adéquate et renvoie l'objet ...

        :return: 'Workbook' si excel, None si erreur
        """
        if not self.valid:
            raise UPC_VALIDATION_ERROR(
                f"Pour avoir la sortie, il faut que l'host (ip: "
                f"{self._hostname}, hostname: {self.real_hostname}) soit valide"
            )

        if self.stdout in self._excel_stdout:
            wb = Stdout.to_xl(
                self._output,
                _hostname=self._hostname,
                _workbook=self.workbook,
                _uptime=self._uptime,
            )
            if not isinstance(wb, str):
                return wb  # Retourne le workbook

            _log.error(f"Erreur pendant la création du fichier excel : {wb}")
            return None

        if self.stdout in self._txt_stdout:
            err = Stdout.to_txt(
                self._output,
                _hostname=self._hostname,
                _now=self._now,
                _uptime=self._uptime,
            )
            if not err:
                return None

            _log.error(f"Erreur pendant la création du fichier txt : {err}")

        if self.stdout in self._console_stdout:
            Stdout.to_prompt(self._output)
            return None
        return None

    def __repr__(self):
        """Affichage de la classe."""
        return f"UnusedPortChecker({self._hostname=}, {self._username=}, {self.stdout=}"


if __name__ == "__main__":
    pass
