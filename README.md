# Workflow Automation GUI

Dieses Projekt ist eine GUI-Anwendung zur Automatisierung und Ausführung von Workflows.
Es verwendet **PyQt5** für die grafische Oberfläche und **SQLAlchemy** für die Datenbankinteraktion.
Workflows bestehen aus Modulen, die nacheinander ausgeführt werden können.

---

## Voraussetzungen / Installation

Stellen Sie sicher, dass Sie **Python 3.x** installiert haben.

Installieren Sie die benötigten Pakete:

```bash
pip install PyQt5 sqlalchemy
```

**Hinweis:**
Die folgenden Standard-Python-Module werden ebenfalls verwendet, müssen jedoch nicht separat installiert werden, da sie bereits in der Python-Standardbibliothek enthalten sind:

* `subprocess`
* `sys`
* `datetime`
* `enum`

---

## Projektstruktur

```
project_root/
│
├── gui/
│   ├── workflow_window.py   # Hauptfenster
│   ├── workflow_tab.py      # UseCaseTab für Workflows
│   ├── module_tab.py        # ModuleTab für Module
│   ├── module_run.py        # Thread-Logik zum Ausführen von Modulen
│
├── db/
│   ├── db_setup.py          # SQLAlchemy-Datenbankmodelle & Setup
│
├── main.py                  # Startpunkt der Anwendung
```

---

## Funktionsweise

### Workflows

* Workflows können über den `Workflows`-Tab hinzugefügt werden.
* Jeder Workflow besteht aus mehreren Modulen.
* Workflows werden in der Datenbank gespeichert und können wiederverwendet werden.

### Module

* Module sind einzelne Python-Skripte, die vom Workflow ausgeführt werden.
* Jedes Modul kann Eingabedaten benötigen.
* Module werden in einem separaten Thread ausgeführt, damit die GUI nicht blockiert wird.
* Live-Logs werden während der Ausführung angezeigt.

### Steuerung

* **▶ Button**: Startet den Workflow.
* **■ Button**: Stoppt die Ausführung eines laufenden Workflows.
* Der Status wird live neben dem Workflow angezeigt.
* Nach Abschluss eines Workflows wird der Status in der Datenbank aktualisiert.

---

## Anwendung starten

```bash
python main.py
```

Die Anwendung öffnet ein Fenster mit Tabs für Workflows und Module.

---

## Hinweise

* Stellen Sie sicher, dass die Module einen gültigen Python-Codepfad haben.
* Module, die Eingaben benötigen, können über die Workflow-Definition gesteuert werden.
* Logs werden während der Ausführung live angezeigt und in der Datenbank gespeichert.
