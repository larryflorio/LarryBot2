from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from larrybot.models.client import Client
from larrybot.models.task import Task

class ClientRepository:
    """Repository for client-related database operations with optimized queries."""

    def __init__(self, session: Session):
        self.session = session

    def add_client(self, name: str) -> Client:
        """Add a new client."""
        client = Client(name=name)
        self.session.add(client)
        self.session.commit()
        return client

    def list_clients(self) -> List[Client]:
        """List all clients with optimized task count loading."""
        return (self.session.query(Client)
                .options(selectinload(Client.tasks))
                .order_by(Client.name.asc())
                .all())

    def list_all_clients(self) -> List[Client]:
        """Legacy method name - delegates to list_clients for backward compatibility."""
        return self.list_clients()

    def get_client_by_name(self, name: str) -> Optional[Client]:
        """Get client by name with optimized task loading."""
        return (self.session.query(Client)
                .options(selectinload(Client.tasks))
                .filter_by(name=name)
                .first())

    def get_client_by_id(self, client_id: int) -> Optional[Client]:
        """Get client by ID with optimized task loading."""
        return (self.session.query(Client)
                .options(selectinload(Client.tasks))
                .filter_by(id=client_id)
                .first())

    def delete_client(self, name: str) -> bool:
        """Delete a client and handle task reassignment."""
        client = self.session.query(Client).filter_by(name=name).first()
        if client:
            # Unassign all tasks from this client (optimized bulk update)
            self.session.query(Task).filter_by(client_id=client.id).update(
                {Task.client_id: None}, synchronize_session=False
            )
            
            # Delete client
            self.session.delete(client)
            self.session.commit()
            return True
        return False

    def remove_client(self, name: str) -> Optional[Client]:
        """Legacy method name - wrapper around delete_client for backward compatibility."""
        client = self.session.query(Client).filter_by(name=name).first()
        if client:
            # Unassign all tasks from this client (optimized bulk update)
            self.session.query(Task).filter_by(client_id=client.id).update(
                {Task.client_id: None}, synchronize_session=False
            )
            
            # Delete client
            self.session.delete(client)
            self.session.commit()
            return client
        return None

    def get_clients_with_task_counts(self) -> List[dict]:
        """Get clients with their task counts using optimized aggregation."""
        result = (self.session.query(
                    Client.id,
                    Client.name,
                    Client.created_at,
                    func.count(Task.id).label('task_count'),
                    func.count(Task.id).filter(Task.done == False).label('active_task_count')
                )
                .outerjoin(Task, Client.id == Task.client_id)
                .group_by(Client.id, Client.name, Client.created_at)
                .order_by(Client.name.asc())
                .all())
        
        return [{
            'id': row.id,
            'name': row.name,
            'created_at': row.created_at,
            'task_count': row.task_count,
            'active_task_count': row.active_task_count
        } for row in result]

    def get_clients_by_ids(self, client_ids: List[int]) -> List[Client]:
        """Batch load clients by IDs with optimized relationships."""
        if not client_ids:
            return []
        
        return (self.session.query(Client)
                .options(selectinload(Client.tasks))
                .filter(Client.id.in_(client_ids))
                .order_by(Client.name.asc())
                .all())

    def search_clients_by_name(self, search_term: str, case_sensitive: bool = False) -> List[Client]:
        """Search clients by name with optimized query."""
        if not search_term.strip():
            return []

        if case_sensitive:
            search_filter = Client.name.contains(search_term)
        else:
            search_filter = func.lower(Client.name).contains(search_term.lower())

        return (self.session.query(Client)
                .options(selectinload(Client.tasks))
                .filter(search_filter)
                .order_by(Client.name.asc())
                .all())

    def get_client_tasks(self, client_name: str) -> List[Task]:
        client = self.get_client_by_name(client_name)
        if client:
            return client.tasks
        return [] 