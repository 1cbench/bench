from pydantic import BaseModel


class TaskModel(BaseModel):
    code: str | None = None
    task_id: str
    env: str
    func_name: str | None = None
    validation_code: str | None = None
    run_context: str | None = None
