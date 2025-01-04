import logging
import os
from random import choices as _choices
from string import ascii_uppercase
from typing import ClassVar, Optional, Union

from Unused_Port.static import DIRS

_log = logging.getLogger(__name__)

try:
    from openpyxl import Workbook
except ImportError:
    _log.warning("Installation de openpyxl en cours ...")
    os.system("pip install openpyxl -q -q -q")
    from openpyxl import Workbook


class Stdout:
    """
    Cette classe permet d'obtenir toutes les sorties proposées par le
    programme, elle crée l'excel / crée le txt et l'enregistre / affiche
    tout dans la console.
    """

    choices: ClassVar[list[str]] = ["excel", "default", "txt", "console"]

    @staticmethod
    def to_xl(
        _output: list[tuple[str, str]],
        *,
        _hostname: str,
        _workbook: Workbook,
        _uptime: str,
    ) -> Union["Workbook", str]:
        """
        Cette fonction est utilisée pour crée l'excel.

        :param _output: Une liste de tuples(interface, last input), ex
            [(gi1/0/2, 12w), (gi1/0/3, never)]
        :param _hostname: l'hostname du switch et non son ip
        :param _workbook: le workbook où il faut ajouter la page excel
        :param _uptime: l'uptime du switch
        :return: str() si erreur sinon l'objet 'Workbook' rempli
        """
        ws = _workbook.create_sheet(_hostname)
        ws.append(("UP TIME", _uptime))
        if _output:
            ws.append(("Interface", "Last Input"))

        for item in _output:
            ws.append(item)
        _log.info(f"Création de la page excel pour l'host {_hostname}")

        try:
            return _workbook
        except Exception as e:
            return e.__class__.__name__

    @staticmethod
    def to_txt(
        _output: list[tuple[str, str]],
        *,
        _now: Optional[str] = None,
        _hostname: str,
        _uptime: str,
    ) -> Union[bool, str]:
        """
        Cette fonction crée simplement un fichier txt avec les infos de
        _output.

        :param _output: Une liste de tuples(interface, last input), ex
            [(gi1/0/2, 12w), (gi1/0/3, never)]
        :param _now: Le jour actuel en str avec un formattage
        :param _hostname: l'hostname du switch et non son ip
        :param _uptime: l'uptime du switch
        :return: False si aucune erreur sinon un str()
        """
        file_name: str = "{}_{}.txt".format(
            _hostname,
            "".join(_choices(ascii_uppercase, k=3)),
        )
        _log.info(
            f"Ecriture des interfaces de l'host {_hostname} "
            f"dans un fichier txt du nom : {file_name}"
        )
        try:
            with open(os.path.join(DIRS.get("txt_output"), file_name), "a") as f:
                f.write(f"UP TIME : {_uptime}")
                for item in _output:
                    f.write(f"Interface {item[0]}, Last input {item[1]}\n")
        except Exception as e:
            return e.__class__.__name__
        return False

    @staticmethod
    def to_prompt(_output: list[tuple[str, str]]) -> bool:
        """
        Cette fonction affiche tout simplement la sortie _output dans la
        console.

        :param _output: Une liste de tuples(interface, last input), ex
            [(gi1/0/2, 12w), (gi1/0/3, never)]
        :return: False
        """
        for item in _output:
            _log.info(f"Interface {item[0]}, Last input {item[1]}")
        return False


if __name__ == "__main__":
    pass
