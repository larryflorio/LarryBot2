from sqlalchemy.orm import Session
from larrybot.models.client import Client
from larrybot.models.task import Task
from typing import List, Optional

class ClientRepository:
    """
    Repository for CRUD operations on Client model.
    """
    def __init__(self, session: Session):
        self.session = session

    def add_client(self, name: str) -> Client:
        client = Client(name=name)
        self.session.add(client)
        self.session.commit()
        return client

    def remove_client(self, name: str) -> Optional[Client]:
        client = self.get_client_by_name(name)
        if client:
            self.session.delete(client)
            self.session.commit()
            return client
        return None

    def get_client_by_name(self, name: str) -> Optional[Client]:
        return self.session.query(Client).filter_by(name=name).first()

    def get_client_by_id(self, client_id: int) -> Optional[Client]:
        return self.session.query(Client).filter_by(id=client_id).first()

    def list_all_clients(self) -> List[Client]:
        return self.session.query(Client).order_by(Client.name).all()

    def get_client_tasks(self, client_name: str) -> List[Task]:
        client = self.get_client_by_name(client_name)
        if client:
            return client.tasks
        return [] 