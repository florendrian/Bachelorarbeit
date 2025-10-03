from PyQt5.QtWidgets import QVBoxLayout, QListWidget, QWidget, QLabel, QPushButton, QInputDialog, QLineEdit, QMessageBox, QHBoxLayout, QCheckBox, QFileDialog, QListWidgetItem, QTextEdit

from db.db_setup import Module, Workflow, WorkflowStep, SessionLocal
from .module_run import SingleModuleRunThread
from sqlalchemy.orm import joinedload


class ModuleTab(QWidget):
    def __init__(self, usecase_name, workflow_window, parent=None):
        super().__init__(parent)
        self.usecase_name = usecase_name
        self.workflow_window = workflow_window
        self.setLayout(QVBoxLayout())

        # Workflow aus der DB holen (inkl. aller Steps + Module)
        session = SessionLocal()
        self.workflow = (
            session.query(Workflow)
            .options(joinedload(Workflow.steps).joinedload(WorkflowStep.module))
            .filter_by(name=self.usecase_name)
            .first()
        )
        session.expunge_all() 
        session.close()

        # Liste der Steps im UI anzeigen
        self.step_list = WorkflowStepList(self.workflow, self)
        self.layout().addWidget(self.step_list)

        # Buttons zum Hinzufügen von Modulen
        self.addModuleBtn = QPushButton("Add New Module")
        self.layout().addWidget(self.addModuleBtn)
        self.addModuleBtn.clicked.connect(self.addModule)

        self.addExistingModuleBtn = QPushButton("Add Existing Module")
        self.layout().addWidget(self.addExistingModuleBtn)
        self.addExistingModuleBtn.clicked.connect(self.addExistingModule)

        # Logfenster unten
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        self.layout().addWidget(QLabel("Logs:"))
        self.layout().addWidget(self.log_text)

        self.run_thread = None
    
    def runModule(self, step):
        # Modul in eigenem Thread starten und Logs anzeigen
        self.status_label.setText(f"Status: Running {step.module.name}")
        self.run_thread = SingleModuleRunThread(step)
        self.run_thread.log_signal.connect(self.log_text.append)
        self.run_thread.error_signal.connect(lambda e: self.log_text.append(f"ERROR: {e}"))
        self.run_thread.finished_signal.connect(lambda: self.status_label.setText("Status: Idle"))
        self.run_thread.start()


    def addModule(self):
        # Neues Modul direkt anlegen (Name, Input, Output, Info)
        session = SessionLocal()

        name, ok = QInputDialog.getText(self, 'Add Module', 'Module Name:')
        if not ok or not name:
            return
        input_value, ok = QInputDialog.getText(self, 'Add Module', 'Input:')
        if not ok:
            return
        output_value, ok = QInputDialog.getText(self, 'Add Module', 'Output:')
        if not ok:
            return
        info, ok = QInputDialog.getMultiLineText(self, 'Add Module', 'Information:')
        if not ok:
            return

        # Modul in DB speichern
        module = Module(name=name, description=info.strip(),
                        input_type=input_value, output_type=output_value)
        session.add(module)
        session.commit()

        # Schritt in Workflow einfügen
        step = WorkflowStep(workflow_id=self.workflow.id, module_id=module.id,
                            position=len(self.workflow.steps) + 1, parameters={})
        session.add(step)
        session.commit()
        session.close()

        self.step_list.loadSteps()

    def addExistingModule(self):
        # Modul aus DB auswählen und anhängen
        session = SessionLocal()
        modules = session.query(Module).all()
        session.close()

        if not modules:
            QMessageBox.warning(self, "Keine Module", "Es sind keine Module in der Datenbank vorhanden.")
            return

        module_names = [m.name for m in modules]
        name, ok = QInputDialog.getItem(
            self, "Select Module", "Choose an existing module:",
            module_names, 0, False
        )
        if not ok or not name:
            return

        
        session = SessionLocal()
        module = session.query(Module).filter_by(name=name).first()

        
        step = WorkflowStep(
            workflow_id=self.workflow.id,
            module_id=module.id,
            position=len(self.workflow.steps) + 1,
            parameters={}
        )
        session.add(step)
        session.commit()
        session.close()

        self.step_list.loadSteps()


    def deleteModule(self, step):
        # Schritt + zugehöriges Modul löschen
        session = SessionLocal()
        step = session.query(WorkflowStep).filter_by(id=step.id).first()
        if step:
            module = session.query(Module).filter_by(id=step.module_id).first()
            session.delete(step)
            if module:
                session.delete(module)
            session.commit()
        session.close()
        self.step_list.loadSteps()

    def openEditTab(self, module):
        # Extra-Tab zum Bearbeiten des Moduls öffnen
        edit_tab = ModuleEditTab(module, self)
        self.workflow_window.tabs.addTab(edit_tab, f"Edit {module.name}")
        self.workflow_window.tabs.setCurrentWidget(edit_tab)


class WorkflowStepList(QWidget):
    def __init__(self, workflow, module_tab, parent=None):
        super().__init__(parent)
        self.workflow = workflow
        self.module_tab = module_tab

        self.setLayout(QVBoxLayout())

        # UI: Liste + Buttons
        self.listWidget = QListWidget()
        self.layout().addWidget(self.listWidget)
        btn_layout = QHBoxLayout()
        self.up_btn = QPushButton("↑")
        self.down_btn = QPushButton("↓")
        self.delete_btn = QPushButton("🗑️")

        btn_layout.addWidget(self.up_btn)
        btn_layout.addWidget(self.down_btn)
        btn_layout.addWidget(self.delete_btn)
        self.layout().addLayout(btn_layout)

        # Button-Events
        self.up_btn.clicked.connect(self.moveUp)
        self.down_btn.clicked.connect(self.moveDown)
        self.delete_btn.clicked.connect(self.deleteStep)
        self.listWidget.itemDoubleClicked.connect(self.editStepModule)


        self.loadSteps()

    def loadSteps(self):
        # Alle Steps aus DB laden und in Liste darstellen
        session = SessionLocal()
        self.steps = (
            session.query(WorkflowStep)
            .options(joinedload(WorkflowStep.module))
            .filter_by(workflow_id=self.workflow.id)
            .order_by(WorkflowStep.position)
            .all()
        )
        session.close()

        self.listWidget.clear()
        for step in self.steps:
            item_widget = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel(f"{step.position}. {step.module.name}")
            play_btn = QPushButton("▶")
            play_btn.setMaximumWidth(60)

            status_label = QLabel("Idle")
            status_label.setFixedWidth(60)

            # Start/Stopp-Logik für das Modul
            def toggle_run(step_obj, btn=play_btn, status=status_label):
                if hasattr(step_obj, "_thread") and step_obj._thread.isRunning():
                    step_obj._thread.stop()
                    status.setText("Stopping...")
                else:
                    thread = SingleModuleRunThread(step_obj)
                    step_obj._thread = thread
                    thread.log_signal.connect(self.module_tab.log_text.append)
                    thread.error_signal.connect(lambda e: self.module_tab.log_text.append(f"ERROR: {e}"))
                    
                    def finished():
                        status.setText("Finished")
                        btn.setText("▶")
                    thread.finished_signal.connect(finished)

                    thread.start()
                    status.setText("Running")
                    btn.setText("■")

            play_btn.clicked.connect(lambda checked, s=step, b=play_btn, st=status_label: toggle_run(s, b, st))

            layout.addWidget(label)
            layout.addWidget(status_label)
            layout.addWidget(play_btn)

            item_widget.setLayout(layout)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.listWidget.addItem(list_item)
            self.listWidget.setItemWidget(list_item, item_widget)


    def moduleFinished(self, step, btn, status_label):
        btn.setText("▶")
        status_label.setText("Idle")

    def moveUp(self):
        # Step eine Position nach oben verschieben
        current = self.listWidget.currentRow()
        if current > 0:
            session = SessionLocal()
            steps = session.query(WorkflowStep).filter_by(workflow_id=self.workflow.id).order_by(WorkflowStep.position).all()
            steps[current].position, steps[current-1].position = steps[current-1].position, steps[current].position
            session.commit()
            session.close()
            self.loadSteps()

    def moveDown(self):
        # Step eine Position nach unten verschieben
        current = self.listWidget.currentRow()
        if current < len(self.steps) - 1:
            session = SessionLocal()
            steps = session.query(WorkflowStep).filter_by(workflow_id=self.workflow.id).order_by(WorkflowStep.position).all()
            steps[current].position, steps[current + 1].position = steps[current + 1].position, steps[current].position
            session.commit()
            session.close()
            self.loadSteps()

    def deleteStep(self):
        # Step löschen + Positionen neu ordnen
        current = self.listWidget.currentRow()
        if current >= 0:
            session = SessionLocal()
            steps = session.query(WorkflowStep).filter_by(workflow_id=self.workflow.id).order_by(WorkflowStep.position).all()
            session.delete(steps[current])
            session.commit()

            # Positionen neu nummerieren
            for i, step in enumerate(session.query(WorkflowStep).filter_by(workflow_id=self.workflow.id).order_by(WorkflowStep.position).all(), start=1):
                step.position = i
            session.commit()
            session.close()
            self.loadSteps()

    def editStepModule(self, item):
        # Doppelklick → Modul im Edit-Tab öffnen
        index = self.listWidget.currentRow()
        if index < 0:
            return
        step = self.steps[index]
        self.module_tab.openEditTab(step.module)




class ModuleEditTab(QWidget):
    def __init__(self, module_data, module_tab, parent=None):
        super().__init__(parent)
        self.module_data = module_data
        self.module_tab = module_tab

        self.setLayout(QVBoxLayout())

        # Eingabefelder für alle Moduldaten
        # Name
        self.name_label = QLabel("Name:")
        self.name_edit = QLineEdit(module_data.name)
        self.layout().addWidget(self.name_label)
        self.layout().addWidget(self.name_edit)

        # Input
        self.input_label = QLabel("Input:")
        self.input_edit = QLineEdit(module_data.input_type or "")
        self.layout().addWidget(self.input_label)
        self.layout().addWidget(self.input_edit)

        # Output
        self.output_label = QLabel("Output:")
        self.output_edit = QLineEdit(module_data.output_type or "")
        self.layout().addWidget(self.output_label)
        self.layout().addWidget(self.output_edit)

        # Info
        self.info_label = QLabel("Info:")
        self.info_edit = QLineEdit(module_data.description or "")
        self.layout().addWidget(self.info_label)
        self.layout().addWidget(self.info_edit)

        # Code-Datei
        self.code_label = QLabel("Code-Datei / Verzeichnis:")
        self.code_edit = QLineEdit(module_data.code_path or "")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browseCode)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.code_edit)
        h_layout.addWidget(self.browse_btn)
        self.layout().addWidget(self.code_label)
        self.layout().addLayout(h_layout)

        # Input-Checkbox
        self.needs_input_checkbox = QCheckBox("Benötigt Input")
        self.needs_input_checkbox.setChecked(module_data.needs_input)
        self.layout().addWidget(self.needs_input_checkbox)

        # Output-Checkbox
        self.needs_output_checkbox = QCheckBox("Benötigt Output")
        self.needs_output_checkbox.setChecked(module_data.needs_output)
        self.layout().addWidget(self.needs_output_checkbox)

        # Save
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.saveChanges)
        self.layout().addWidget(self.save_btn)

    def browseCode(self):
        # Dateiauswahl für Modulcode
        path, _ = QFileDialog.getOpenFileName(self, "Select Code File")
        if path:
            self.code_edit.setText(path)

    def saveChanges(self):
        # Änderungen ins DB-Modul übernehmen
        session = SessionLocal()
        module = session.query(Module).filter_by(id=self.module_data.id).first()
        module.name = self.name_edit.text()
        module.input_type = self.input_edit.text()
        module.output_type = self.output_edit.text()
        module.description = self.info_edit.text()
        module.code_path = self.code_edit.text()
        module.needs_input = self.needs_input_checkbox.isChecked()
        module.needs_output = self.needs_output_checkbox.isChecked()
        session.commit()
        session.close()

        # UI aktualisieren
        self.module_tab.step_list.loadSteps()
        QMessageBox.information(self, "Gespeichert", "Änderungen wurden übernommen.")

        tabs = self.module_tab.workflow_window.tabs
        index = tabs.indexOf(self)
        if index != -1:
            tabs.removeTab(index)
        self.module_tab.step_list.loadSteps()

