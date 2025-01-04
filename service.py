# PYTHON 3.11 UNIQUEMENT

# UTILISATION DU SCRIPT EN TANT QUE SERVICE
# service.exe s'utilise avec
# cmd> service.exe install
# cmd> service.exe start

# Ou alors depuis services.msc une fois installé

# cmd> sc delete "Unused Port Service"
# cmd> service.exe delete

import logging
import os
import sys

import servicemanager
import win32serviceutil

sys.path.extend(os.path.dirname(os.path.abspath(__file__)))

from Unused_Port.service import WindowsService

_log = logging.getLogger(__name__)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(WindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(WindowsService)

#  pydocstringformatter -w .\port_checker.py
#  docformatter -i .\port_checker.py
#  pyinstaller -F -n Port_Unused ..\main.py
#  pyarmor gen --pack onefile -O exe service.py
