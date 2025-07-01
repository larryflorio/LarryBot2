import pytest
from larrybot.storage.client_repository import ClientRepository
from larrybot.storage.task_repository import TaskRepository


def test_add_and_get_client(test_session, db_client_factory):
    client_repo = ClientRepository(test_session)
    client = db_client_factory(name="AcmeCorp")
    client_id = client.id
    fetched = client_repo.get_client_by_name("AcmeCorp")
    assert fetched is not None
    assert fetched.name == "AcmeCorp"
    assert fetched.id == client_id

def test_list_all_clients(test_session, db_client_factory):
    client_repo = ClientRepository(test_session)
    db_client_factory(name="A")
    db_client_factory(name="B")
    names = [c.name for c in client_repo.list_all_clients()]
    assert set(names) == {"A", "B"}

def test_remove_client(test_session, db_client_factory):
    client_repo = ClientRepository(test_session)
    db_client_factory(name="A")
    removed = client_repo.remove_client("A")
    assert removed is not None
    assert client_repo.get_client_by_name("A") is None

def test_unique_client_name(test_session, db_client_factory):
    client_repo = ClientRepository(test_session)
    db_client_factory(name="A")
    with pytest.raises(Exception):
        db_client_factory(name="A")

def test_assign_and_unassign_task(test_session, db_client_factory, db_task_factory):
    client_repo = ClientRepository(test_session)
    task_repo = TaskRepository(test_session)
    client = db_client_factory(name="AcmeCorp")
    client_id = client.id
    task = db_task_factory(description="Test Task")
    task_id = task.id
    assigned = task_repo.assign_task_to_client(task_id, "AcmeCorp")
    assert assigned.client_id == client_id
    unassigned = task_repo.unassign_task(task_id)
    assert unassigned.client_id is None

def test_get_tasks_by_client(test_session, db_client_factory, db_task_factory):
    client_repo = ClientRepository(test_session)
    task_repo = TaskRepository(test_session)
    db_client_factory(name="AcmeCorp")
    task1 = db_task_factory(description="Task 1")
    task2 = db_task_factory(description="Task 2")
    task_repo.assign_task_to_client(task1.id, "AcmeCorp")
    task_repo.assign_task_to_client(task2.id, "AcmeCorp")
    tasks = task_repo.get_tasks_by_client("AcmeCorp")
    assert len(tasks) == 2
    assert set(t.description for t in tasks) == {"Task 1", "Task 2"}

def test_get_client_tasks(test_session, db_client_factory, db_task_factory):
    client_repo = ClientRepository(test_session)
    task_repo = TaskRepository(test_session)
    db_client_factory(name="BetaLLC")
    task = db_task_factory(description="Beta Task")
    task_repo.assign_task_to_client(task.id, "BetaLLC")
    tasks = client_repo.get_client_tasks("BetaLLC")
    assert len(tasks) == 1
    assert tasks[0].description == "Beta Task" 