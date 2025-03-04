"""
Modelos de dados para usuários e suas preferências.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
import pytz

from config import DEFAULT_TIMEZONE, DEFAULT_SYMBOLS


@dataclass
class UserPreferences:
    """Modelo para preferências do usuário."""
    timezone: pytz.timezone = DEFAULT_TIMEZONE
    watchlist: Set[str] = field(default_factory=lambda: set(DEFAULT_SYMBOLS))
    alert_notifications: bool = True
    price_update_interval: int = 5  # minutos
    
    def add_to_watchlist(self, symbol: str) -> None:
        """
        Adiciona um símbolo à watchlist.
        
        Args:
            symbol: Símbolo da criptomoeda.
        """
        self.watchlist.add(symbol.upper())
    
    def remove_from_watchlist(self, symbol: str) -> bool:
        """
        Remove um símbolo da watchlist.
        
        Args:
            symbol: Símbolo da criptomoeda.
            
        Returns:
            bool: True se o símbolo foi removido, False se não estava na watchlist.
        """
        symbol = symbol.upper()
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            return True
        return False


@dataclass
class UserSession:
    """Modelo para sessão do usuário."""
    user_id: int
    start_time: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    last_activity: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    command_count: int = 0
    
    def update_activity(self) -> None:
        """Atualiza o timestamp da última atividade."""
        self.last_activity = datetime.now(DEFAULT_TIMEZONE)
        self.command_count += 1
    
    @property
    def session_duration(self) -> float:
        """
        Retorna a duração da sessão em minutos.
        
        Returns:
            float: Duração da sessão em minutos.
        """
        delta = datetime.now(DEFAULT_TIMEZONE) - self.start_time
        return delta.total_seconds() / 60


@dataclass
class User:
    """Modelo para usuário."""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferences: UserPreferences = field(default_factory=UserPreferences)
    created_at: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    session: Optional[UserSession] = None
    
    def start_session(self) -> None:
        """Inicia uma nova sessão para o usuário."""
        self.session = UserSession(user_id=self.user_id)
    
    def update_activity(self) -> None:
        """Atualiza a atividade do usuário na sessão atual."""
        if self.session:
            self.session.update_activity()
        else:
            self.start_session()
    
    @property
    def full_name(self) -> str:
        """
        Retorna o nome completo do usuário.
        
        Returns:
            str: Nome completo do usuário ou ID se não houver nome.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.user_id}"
    
    @property
    def is_active(self) -> bool:
        """
        Verifica se o usuário está ativo (teve atividade nos últimos 30 minutos).
        
        Returns:
            bool: True se o usuário está ativo, False caso contrário.
        """
        if not self.session:
            return False
        
        delta = datetime.now(DEFAULT_TIMEZONE) - self.session.last_activity
        return delta.total_seconds() < 1800  # 30 minutos


class UserManager:
    """Gerenciador de usuários."""
    
    def __init__(self):
        """Inicializa o gerenciador de usuários."""
        self.users: Dict[int, User] = {}
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Obtém um usuário pelo ID.
        
        Args:
            user_id: ID do usuário.
            
        Returns:
            Optional[User]: Usuário se encontrado, None caso contrário.
        """
        return self.users.get(user_id)
    
    def create_user(self, user_id: int, username: Optional[str] = None,
                   first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
        """
        Cria um novo usuário.
        
        Args:
            user_id: ID do usuário.
            username: Nome de usuário (opcional).
            first_name: Primeiro nome (opcional).
            last_name: Sobrenome (opcional).
            
        Returns:
            User: Usuário criado.
        """
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        self.users[user_id] = user
        return user
    
    def get_or_create_user(self, user_id: int, username: Optional[str] = None,
                          first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
        """
        Obtém um usuário existente ou cria um novo.
        
        Args:
            user_id: ID do usuário.
            username: Nome de usuário (opcional).
            first_name: Primeiro nome (opcional).
            last_name: Sobrenome (opcional).
            
        Returns:
            User: Usuário obtido ou criado.
        """
        user = self.get_user(user_id)
        if not user:
            user = self.create_user(user_id, username, first_name, last_name)
        return user
    
    def get_active_users(self) -> List[User]:
        """
        Obtém a lista de usuários ativos.
        
        Returns:
            List[User]: Lista de usuários ativos.
        """
        return [user for user in self.users.values() if user.is_active] 