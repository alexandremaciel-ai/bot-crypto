"""Modelos de dados para notícias de criptomoedas."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from config import DEFAULT_TIMEZONE

@dataclass
class CryptoNews:
    """Modelo para notícias de criptomoedas."""
    title: str
    url: str
    source: str
    summary: Optional[str] = None
    published_at: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    
    @property
    def formatted_date(self) -> str:
        """Retorna a data formatada."""
        return self.published_at.strftime("%d/%m/%Y %H:%M")
    
    @property
    def short_source(self) -> str:
        """Retorna uma versão curta da fonte."""
        return self.source.split('.')[0].capitalize()