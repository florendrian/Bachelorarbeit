from PyQt5.QtCore import QThread, pyqtSignal
import subprocess, sys
from datetime import datetime

from db.db_setup import SessionLocal, ModuleRun


class SingleModuleRunThread(QThread):
    # Signale, um Log-Meldungen, Fehler und Fertig-Status nach außen zu geben
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, step, input_data=None):
        super().__init__()
        self.step = step # Der WorkflowStep, der ausgeführt werden soll
        self.input_data = input_data  # Optionaler Input für das Modul
        self._stop = False # Flag, um Ausführung abzubrechen

    def run(self):
        mod = self.step.module
        if not mod.code_path:
            # Wenn kein Code hinterlegt ist -> abbrechen
            self.log_signal.emit(f"{mod.name}: Kein Code hinterlegt.\n")
            self.finished_signal.emit()
            return

        self.log_signal.emit(f"Running {mod.name}...\n")
        cmd = [sys.executable, "-u", mod.code_path] # Python-Script starten

        try:
            # Wenn Input gebraucht wird und vorhanden ist -> per stdin übergeben
            if mod.needs_input and self.input_data:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True
                )
                process.stdin.write(self.input_data)
                process.stdin.close()
            else:
                # Ohne Input starten
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True
                )

            # Echtzeit-Ausgabe lesen
            for line in iter(process.stdout.readline, ""):
                if self._stop:
                    self.log_signal.emit("Execution stopped by user.\n")
                    process.terminate()
                    break
                self.log_signal.emit(line.rstrip())

            process.stdout.close()
            process.wait()

        except Exception as e:
            self.error_signal.emit(str(e))

        # Immer melden, dass Modul durch ist
        self.finished_signal.emit()
        self.log_signal.emit(f"Finished {mod.name}\n")

    def stop(self):
        # Stop-Flag setzen, damit run() abbrechen kann
        self._stop = True


class ModuleRunThread(QThread):
    # Wie oben, nur für mehrere Module im Workflow
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, steps, workflow_instance_id, parent=None):
        super().__init__(parent)
        self.steps = steps # Liste von WorkflowSteps
        self._stop = False
        self.workflow_instance_id = workflow_instance_id # ID der Workflow-Instanz (für DB)

    def run(self):
        session = SessionLocal()
        try:
            for step in self.steps:
                if self._stop:
                    self.log_signal.emit("Execution stopped by user.\n")
                    break

                mod = step.module
                if not mod.code_path:
                    self.log_signal.emit(f"{mod.name}: Kein Code hinterlegt.\n")
                    
                    continue
                
                # DB-Eintrag für den Modul-Run anlegen
                module_run = ModuleRun(
                    workflow_instance_id=self.workflow_instance_id,
                    workflow_step_id=step.id,
                    status="running",
                    started_at=datetime.now(),
                    input_ref=getattr(step, "input_ref", None),
                    log=""
                )
                session.add(module_run)
                session.commit()

                self.log_signal.emit(f"Running {mod.name}...\n")
                cmd = [sys.executable, "-u", mod.code_path]
                logs = []

                try:
                    # Input falls nötig über stdin
                    if mod.needs_input and getattr(step, "input_data", None):
                        process = subprocess.Popen(
                            cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=1,
                            universal_newlines=True
                        )
                        process.stdin.write(step.input_data)
                        process.stdin.close()
                    else:
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=1,
                            universal_newlines=True
                        )

                    # Live-Ausgabe + direkt in DB speichern
                    for line in iter(process.stdout.readline, ""):
                        if self._stop:
                            self.log_signal.emit("Execution stopped by user.\n")
                            process.terminate()
                            break
                        self.log_signal.emit(line.rstrip())
                        logs.append(line)

                        # Zwischenstand ins Log in DB speichern
                        session.query(ModuleRun).filter_by(id=module_run.id).update(
                                {"log": "\n".join(logs)}
                            )
                        session.commit()

                    process.stdout.close()
                    return_code = process.wait()

                    # Status (finished/failed) in DB aktualisieren
                    session.query(ModuleRun).filter_by(id=module_run.id).update(
                            {
                                "status": "finished" if return_code == 0 else "failed",
                                "finished_at": datetime.now(),
                                "log": "\n".join(logs),
                            }
                        )
                    session.commit()

                except Exception as e:
                    # Falls Exception: ModulRun in DB auf failed setzen
                    session.query(ModuleRun).filter_by(id=module_run.id).update(
                            {"status": "failed", "finished_at": datetime.now(), "log": str(e)}
                        )
                    session.commit()
                    self.error_signal.emit(str(e))
                    logs.append(f"\nException: {str(e)}")

                # Meldung, dass Step fertig ist
                self.finished_signal.emit()
                self.log_signal.emit(f"Finished {mod.name}\n")
        finally:
            session.close()

    def stop(self):
        # Abbruch-Flag setzen
        self._stop = True