# Unused_Port_Cisco

![Python](https://img.shields.io/badge/python-3.11-blue)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![License](https://img.shields.io/badge/license-MIT-orange)

**Unused_Port_Cisco** est un outil puissant conçu pour récupérer tous les ports inutilisés sur les switchs Cisco via SSH et générer automatiquement des fichiers Excel par switch sous la forme `{hostname}.xlsx`. Il peut être utilisé comme script ponctuel ou comme service Windows programmé pour exécutions périodiques.

---

## 📚 Table des matières
1. [🚀 Fonctionnalités principales](#-fonctionnalités-principales)
2. [🛠️ Installation](#️-installation)
3. [⚙️ Configuration](#️-configuration)
   - [🔧 Fichier `static.py`](#-staticpy)
   - [🔒 Fichier `secrets.py`](#-secretspy)
4. [🚀 Utilisation](#-utilisation)
   - [▶️ Exécution avec `main.py`](#️-exécution-directe-avec-mainpy)
   - [🖥️ Gestion du service Windows](#️-création-et-gestion-du-service-windows)
5. [🛡️ Contributions & Développement](#️-contributions--développement)
6. [📝 Licence](#-licence)

---

## 🚀 Fonctionnalités principales

- **🔍 Détection des ports inutilisés** :
  - Identifie les ports inactifs en se basant sur `last input` et l'état `notconnect`.
  - Paramétrage du nombre minimal de semaines d'inactivité (`UPTIME_MIN_WEEK`).

- **📊 Génération automatique de rapports** :
  - Création de fichiers Excel `{hostname}.xlsx` pour chaque switch.
  - Sauvegarde dans un ou plusieurs dossiers partagés.

- **🌐 Analyse réseau étendue** :
  - Scanne toutes les IP d'une plage définie et se connecte aux équipements via SSH (port 22).
  - Exclusion d'adresses IP spécifiques via des règles configurables.

- **🕒 Service Windows intégré** :
  - Planification automatique, par défaut tous les dimanches à 18h.
  - Fonctionnement autonome pour des analyses périodiques.

- **⚙️ Mode manuel avec `main.py`** :
  - Permet un scan immédiat d'une ou plusieurs IP.
  - Mode auto pour analyser toutes les IP définies dans `HOSTS`.

- **📁 Gestion des dossiers partagés** :
  - Connexion automatique à des dossiers partagés (avec credentials spécifiques).
  - Compatible avec plusieurs emplacements réseau.

---

## 🛠️ Installation

### 🔑 Prérequis
- **Python 3.11** : requis pour garantir la compatibilité avec le service Windows.
  - **⚠️ Python 3.12 non pris en charge** (problèmes avec `pywin32`).

### 📂 Installation des dépendances
```bash
pip install -r requirements.txt          # Pour l'utilisation de base
pip install -r requirements_service.txt  # Pour le service Windows
pip install -r requirements_dev.txt      # Pour le développement
```

---

## ⚙️ Configuration

### 🔧 `static.py`
Voici les lignes importantes à configurer selon vos besoins :  
> ⚠️ **Pensez à adapter les valeurs en fonction de votre infrastructure.**

#### Réseau d'administration
```python
ADMIN_NETWORK: tuple = (ip_network("192.168.1.0/24"),)
```

#### Exclusions IP
```python
EXCLUDE_IP_TEMP: list = [
    "192.168.1.1-192.168.1.10",
]
```

#### Hosts par région
```python
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
```

#### Dossiers partagés
```python
DOSSIER_PARTAGE_SITE: dict[str, list[Path]] = {
    "France": [Path(r"\\srv\Network\Tools\Port_Unused\France")],
    "US": [
        Path(r"\\srv\Network\Tools\Port_Unused\US"),
        Path(r"\\srv\Network\Tools\Port_Unused\US2"),
    ],
}
```

#### Durée minimale d'inactivité
```python
UPTIME_MIN_WEEK: int = 12
```

### 🔒 `secrets.py`
#### Credentials pour les switchs
```python
username = "User"
password = "password"
```

#### Credentials pour les dossiers partagés
```python
shared_folder_username = "User"
shared_folder_password = "password"
```

---

## 🚀 Utilisation

### ▶️ Exécution directe avec `main.py`
```bash
python main.py [OPTIONS]
```

#### Options principales
- `--auto` : Exécute le script sur toutes les IP définies dans `HOSTS`.
- `--debug` : Active le mode debug.
- `--schedule` : Permet de planifier une exécution périodique.
  - Exemples :
    - `--schedule dimanche` : Tous les dimanches.
    - `--schedule 3` : Tous les 3 jours.

#### Exemples de commande
- Exécution instantanée :
  ```bash
  python main.py --auto
  ```
- Planification tous les 3 jours :
  ```bash
  python main.py --schedule 3 --debug --auto
  ```

---

### 🖥️ Création et gestion du service Windows
1. Installer les dépendances nécessaires :
   ```bash
   pip install -r requirements_service.txt
   ```
2. Compiler le service :
   ```bash
   pyarmor gen --pack onefile -O exe service.py
   ```
3. Installer et démarrer le service :
   ```bash
   service.exe install
   service.exe start
   ```

---

## 🛡️ Contributions & Développement

### 🛠️ Installation des outils de développement
```bash
pip install -r requirements_dev.txt
```

### ✅ Bonnes pratiques
- Utiliser [Ruff](https://github.com/astral-sh/ruff) pour le linting et le formattage.
- Configurer [Pre-commit](https://pre-commit.com/) pour valider les changements.

---

## 📝 Licence

**Unused_Port_Cisco** est distribué sous licence [MIT](LICENSE).  
Contributions, idées et suggestions sont les bienvenues ! 😃
