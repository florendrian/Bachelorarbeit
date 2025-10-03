from PyQt5.QtWidgets import QMainWindow, QTabWidget
from .module_tab import ModuleTab
from .workflow_tab import UseCaseTab


class WorkflowWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        # Titel des Hauptfensters setzen
        self.setWindowTitle("Workflow Automation")

        self.tabs = QTabWidget()
        self.useCaseTab = UseCaseTab(self) 
        self.tabs.addTab(self.useCaseTab, "Workflows")
        self.setCentralWidget(self.tabs)