import logging
import os
import traceback
from pathlib import Path

import servicemanager  # type: ignore
import win32event  # type: ignore
import win32service  # type: ignore
import win32serviceutil  # type: ignore

from Unused_Port.helper import (
    _create_logging,
    _get_day,
    _service_log_both,
    check_path,
    run_scheduler,
)
from Unused_Port.starter import start
from Unused_Port.static import DIRS, DOSSIER_PARTAGE_SITE, HOSTS

_log = logging.getLogger(__name__)

try:
    import schedule
except ImportError:
    _log.warning("Installation de schedule en cours ...")
    os.system("pip install schedule -q -q -q")
    import schedule


def _exit(e):
    WindowsService.running = False
    raise Exception(e)


class WindowsService(win32serviceutil.ServiceFramework):
    """Classe créant le service Windows."""

    _svc_name_ = "Unused_Port_Service"
    _svc_display_name_ = "Unused Port Service"
    _svc_description_ = (
        "Récupération automatique tous les dimanches "
        "à 18H des ports inutilisés de tous les switchs en France"
    )
    running = True

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        DIRS.service = True
        WindowsService.running = True
        self._day = _get_day()

    def SvcStop(self):
        """
        Méthode appelée par la classe parente pour stopper le service.

        Stop le service en faisant un log et stoppant le scheduler (running -> False)
        """
        WindowsService.running = False
        _log.warning("Le service s'arrete")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """
        Méthode appelée par la classe parente pour lancer le service.

        Elle log au service manager, et start le service (et log en cas d'exception)
        """
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        try:
            self.start()

        except Exception:
            servicemanager.LogErrorMsg(traceback.format_exc())
            _service_log_both(traceback.format_exc())
        servicemanager.LogInfoMsg("normal exit")

    def start(self):
        """
        Entry point de la classe WindowsService.

        Elle permet de start le service, de créer le schedule et de run le scheduler
        """
        if not (p := Path(DIRS.get("logs"))).exists():
            p.mkdir(parents=True)

        _create_logging()

        _service_log_both(
            "Les paths sont : " + "\n-".join([f"{d}: {v}" for d, v in DIRS.items()])
        )

        exit_path: bool = check_path(DOSSIER_PARTAGE_SITE)
        if exit_path:
            _exit("Au moins 1 Path invalide detecté")

        ip = HOSTS

        schedule.every().sunday.at("18:00").do(start, ip, False)

        _service_log_both(
            "Le script va s'executer automatiquement "
            "tous les dimanches à 18h00 sur la pool France"
        )

        run_scheduler(delay=10, value_to_match=WindowsService.running)
