from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Enum, JSON, DateTime, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum
import datetime

Base = declarative_base()

# Status Enums
class StatusEnum(str, enum.Enum):
    pending = "pending"
    running = "running"
    failed = "failed"
    finished = "finished"

# Tabellen
class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    description = Column(Text)
    input_type = Column(Text)
    output_type = Column(Text)
    code_path = Column(Text, default="")
    needs_input = Column(Boolean, default=True)
    needs_output = Column(Boolean, default=True)

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    steps = relationship("WorkflowStep", back_populates="workflow", order_by="WorkflowStep.position")

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    module_id = Column(Integer, ForeignKey("modules.id"))
    position = Column(Integer)
    parameters = Column(JSON)
    
    workflow = relationship("Workflow", back_populates="steps")
    module = relationship("Module")

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)

class ModuleRun(Base):
    __tablename__ = "module_runs"
    id = Column(Integer, primary_key=True)
    workflow_instance_id = Column(Integer, ForeignKey("workflow_instances.id"))
    workflow_step_id = Column(Integer, ForeignKey("workflow_steps.id"))
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)
    input_ref = Column(String(255))
    output_ref = Column(String(255))
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    log = Column(JSON)


engine = create_engine("mysql+pymysql://user:@localhost:3306/workflows_db?charset=utf8mb4")
SessionLocal = sessionmaker(bind=engine)

def init_db():
    #Base.metadata.drop_all(engine) #zum löschen der aktuellen DB
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
    print("MariaDB-Datenbank und Tabellen erstellt!")
