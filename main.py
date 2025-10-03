import sys
from PyQt5.QtWidgets import QApplication
from gui.workflow_window import WorkflowWindow




def main():
    """
    Startet die Workflow-Automation GUI.
    """
    app = QApplication(sys.argv)
    window = WorkflowWindow()
    window.showMaximized()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

 