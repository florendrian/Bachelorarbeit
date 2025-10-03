from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QListWidget, QInputDialog, QLabel, QTextEdit, QHBoxLayout, QListWidgetItem
from PyQt5.QtCore import Qt

from db.db_setup import Workflow, SessionLocal, WorkflowInstance
from .module_run import ModuleRunThread
from .module_tab import WorkflowStep, ModuleTab
from sqlalchemy.orm import joinedload
from datetime import datetime

class UseCaseTab(QWidget):
    def __init__(self, workflow_window, parent=None):
        super().__init__(parent)
        self.workflow_window = workflow_window
        self.setLayout(QVBoxLayout())

        # Liste mit allen Workflows
        self.useCaseList = QListWidget()
        self.layout().addWidget(self.useCaseList)

        # Button zum neuen Workflow anlegen
        self.addUseCaseBtn = QPushButton("Add Workflow")
        self.layout().addWidget(self.addUseCaseBtn)
        self.addUseCaseBtn.clicked.connect(self.addUseCase)

        # Logs (Ausgaben beim Ausführen)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        h_layout = QHBoxLayout()

        self.layout().addLayout(h_layout)
        self.layout().addWidget(QLabel("Logs:"))
        self.layout().addWidget(self.log_text)

        # Thread-Handle für laufende Workflows
        self.run_thread = None
        self.current_workflow = None

        # Workflows beim Start laden
        self.loadUseCases()
        self.useCaseList.itemClicked.connect(self.selectUseCase)

    def get_or_create_workflow_instance(self, workflow_id):
        #Sorgt dafür, dass es eine Workflow-Instanz in der DB gibt (neu oder reaktiviert)
        session = SessionLocal()
        instance = (
            session.query(WorkflowInstance)
            .filter_by(workflow_id=workflow_id)
            .order_by(WorkflowInstance.started_at.desc())
            .first()
        )
        if instance:
            # Falls schon vorhanden → neu starten
            instance.status = "running"
            instance.started_at = datetime.now()
            instance.finished_at = None
            session.commit()
        else:
            # Neue Instanz anlegen
            instance = WorkflowInstance(
                workflow_id=workflow_id,
                status="running",
                started_at=datetime.now()
            )
            session.add(instance)
            session.commit()
        workflow_instance_id = instance.id
        session.expunge(instance) # DB-Objekt vom Session-Kontext lösen
        session.close()
        return workflow_instance_id

    
    def loadUseCases(self):
        #Alle Workflows aus der DB laden und in die Liste eintragen
        self.useCaseList.clear()
        session = SessionLocal()
        workflows = (
            session.query(Workflow)
            .options(joinedload(Workflow.steps).joinedload(WorkflowStep.module))
            .all()
        )
        session.expunge_all()
        session.close()

        for wf in workflows:
            item_widget = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)

            # Name + Status-Label
            label = QLabel(wf.name)
            status_label = QLabel("Idle")
            status_label.setFixedWidth(80)

            # Run/Stop-Button
            run_btn = QPushButton("▶")
            run_btn.setMaximumWidth(60)

            def toggle_run(checked=False, workflow=wf, btn=run_btn, status=status_label):
                
                # Wenn Workflow schon läuft → abbrechen
                if hasattr(workflow, "_thread") and workflow._thread.isRunning():
                    workflow._thread.stop()
                    status.setText("Stopping...")
                    return

                # Neue Workflow-Instanz besorgen
                workflow_instance_id = self.get_or_create_workflow_instance(workflow.id)

                # Steps sortieren
                steps = sorted(workflow.steps, key=lambda s: s.position)

                # Thread starten
                thread = ModuleRunThread(steps, workflow_instance_id)
                workflow._thread = thread
                thread.log_signal.connect(self.log_text.append)
                thread.error_signal.connect(lambda e: self.log_text.append(f"ERROR: {e}"))

                def finished():
                    # Status aktualisieren, DB-Eintrag fertigstellen
                    status.setText("Finished")
                    btn.setText("▶")
                    session = SessionLocal()
                    inst = session.get(WorkflowInstance, workflow_instance_id)
                    inst.status = "finished"
                    inst.finished_at = datetime.now()
                    session.commit()
                    session.close()
                thread.finished_signal.connect(finished)

                # Workflow starten
                thread.start()
                status.setText("Running")
                btn.setText("■")

            run_btn.clicked.connect(toggle_run)

            layout.addWidget(label)
            layout.addWidget(status_label)
            layout.addWidget(run_btn)

            item_widget.setLayout(layout)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.UserRole, wf) # Workflow-Objekt ins Item hängen
            self.useCaseList.addItem(list_item)
            self.useCaseList.setItemWidget(list_item, item_widget)
        

    def addUseCase(self):
        #Dialog öffnen, neuen Workflow-Namen abfragen und in DB speichern
        usecase_name, ok = QInputDialog.getText(self, 'New Workflow', 'Workflow Name:')
        if ok and usecase_name:
            session = SessionLocal()
            new_workflow = Workflow(name=usecase_name)
            session.add(new_workflow)
            session.commit()
            session.close()
            self.loadUseCases()
    
    def selectUseCase(self, item):
        #Wenn Workflow in der Liste angeklickt wird → im neuen Tab öffnen
        workflow = item.data(Qt.UserRole)  # Direkt aus dem Item holen

        if not workflow:
            print("Kein Workflow gefunden!")
            return

        self.current_workflow = workflow
        self.log_text.clear()

        # ModuleTab für diesen Workflow öffnen
        module_tab = ModuleTab(workflow.name, self.workflow_window)
        self.workflow_window.tabs.addTab(module_tab, f"Modules: {workflow.name}")
        self.workflow_window.tabs.setCurrentWidget(module_tab)

    

