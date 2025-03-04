"""
Modelos de dados para criptomoedas e análise técnica.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import pytz

from config import DEFAULT_TIMEZONE


@dataclass
class CryptoPrice:
    """Modelo para preço de criptomoeda."""
    symbol: str
    price: float
    timestamp: float = None
    
    def __post_init__(self):
        """Inicializa campos adicionais após a criação."""
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
        self.formatted_price = f"{self.price:.8f}".rstrip('0').rstrip('.')
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "timestamp": self.timestamp,
            "formatted_price": self.formatted_price
        }


@dataclass
class PriceChange:
    """Modelo para mudança de preço."""
    symbol: str
    current_price: float
    previous_price: float
    percent_change: float
    timestamp: float = None
    
    def __post_init__(self):
        """Inicializa campos adicionais após a criação."""
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
        
        # Formata a variação de preço
        sign = "+" if self.percent_change >= 0 else ""
        self.formatted_change = f"{sign}{self.percent_change:.2f}%"
        
        # Define a cor da variação
        self.color = "green" if self.percent_change >= 0 else "red"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "previous_price": self.previous_price,
            "percent_change": self.percent_change,
            "timestamp": self.timestamp,
            "formatted_change": self.formatted_change,
            "color": self.color
        }


@dataclass
class TechnicalIndicator:
    """Modelo base para indicadores técnicos."""
    symbol: str
    timeframe: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    
    @property
    def formatted_time(self) -> str:
        """Retorna o timestamp formatado."""
        return self.timestamp.strftime("%d/%m/%Y %H:%M:%S")


@dataclass
class EMAIndicator:
    """Modelo para indicador EMA (Exponential Moving Average)."""
    symbol: str
    timeframe: str
    short_ema: float
    medium_ema: float
    long_ema: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    
    @property
    def formatted_time(self) -> str:
        """Retorna o timestamp formatado."""
        return self.timestamp.strftime("%d/%m/%Y %H:%M:%S")
    
    @property
    def trend(self) -> str:
        """Determina a tendência com base nos EMAs."""
        if self.short_ema > self.medium_ema > self.long_ema:
            return "Alta"
        elif self.short_ema < self.medium_ema < self.long_ema:
            return "Baixa"
        else:
            return "Lateral"


@dataclass
class RSIIndicator:
    """Modelo para indicador RSI (Relative Strength Index)."""
    symbol: str
    timeframe: str
    value: float
    overbought_threshold: float = 70.0
    oversold_threshold: float = 30.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    
    @property
    def formatted_time(self) -> str:
        """Retorna o timestamp formatado."""
        return self.timestamp.strftime("%d/%m/%Y %H:%M:%S")
    
    @property
    def condition(self) -> str:
        """Determina a condição com base no valor do RSI."""
        if self.value >= self.overbought_threshold:
            return "Sobrecomprado"
        elif self.value <= self.oversold_threshold:
            return "Sobrevendido"
        else:
            return "Neutro"


@dataclass
class VolumeAnalysis:
    """Modelo para análise de volume."""
    symbol: str
    timeframe: str
    current_volume: float
    average_volume: float
    volume_increasing: bool
    timestamp: float = None
    
    def __post_init__(self):
        """Inicializa campos adicionais após a criação."""
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "current_volume": self.current_volume,
            "average_volume": self.average_volume,
            "volume_increasing": self.volume_increasing,
            "timestamp": self.timestamp
        }
    
    @property
    def volume_ratio(self) -> float:
        """Calcula a razão entre o volume atual e a média."""
        return self.current_volume / self.average_volume if self.average_volume > 0 else 0
    
    @property
    def is_high_volume(self) -> bool:
        """Verifica se o volume está acima da média."""
        return self.volume_ratio > 1.5
    
    @property
    def is_low_volume(self) -> bool:
        """Verifica se o volume está abaixo da média."""
        return self.volume_ratio < 0.5
    
    @property
    def volume_description(self) -> str:
        """Retorna uma descrição do volume."""
        if self.is_high_volume:
            return "Volume alto"
        elif self.is_low_volume:
            return "Volume baixo"
        else:
            return "Volume normal"


@dataclass
class TechnicalAnalysis:
    """Modelo para análise técnica completa."""
    symbol: str
    price: CryptoPrice
    ema: Dict[str, EMAIndicator] = field(default_factory=dict)
    rsi: Dict[str, RSIIndicator] = field(default_factory=dict)
    volume: Dict[str, VolumeAnalysis] = field(default_factory=dict)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna um resumo da análise técnica.
        
        Returns:
            Dict[str, Any]: Resumo da análise técnica.
        """
        summary = {
            "symbol": self.symbol,
            "price": self.price.price,
            "timestamp": self.price.timestamp,
            "indicators": {}
        }
        
        # Adiciona EMAs
        for timeframe, ema in self.ema.items():
            summary["indicators"][f"ema_{timeframe}"] = {
                "trend": ema.trend,
                "short": ema.short_ema,
                "medium": ema.medium_ema,
                "long": ema.long_ema,
            }
        
        # Adiciona RSIs
        for timeframe, rsi in self.rsi.items():
            summary["indicators"][f"rsi_{timeframe}"] = {
                "value": rsi.value,
                "condition": rsi.condition,
            }
        
        # Adiciona análise de volume
        for timeframe, vol in self.volume.items():
            summary["indicators"][f"volume_{timeframe}"] = {
                "current": vol.current_volume,
                "average": vol.average_volume,
                "ratio": vol.volume_ratio,
                "description": vol.volume_description,
            }
        
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "price": self.price.to_dict(),
            "ema": {k: v.to_dict() for k, v in self.ema.items()},
            "rsi": {k: v.to_dict() for k, v in self.rsi.items()},
            "volume": {k: v.to_dict() for k, v in self.volume.items()}
        }


@dataclass
class Alert:
    """Modelo para alertas de preço."""
    symbol: str
    user_id: int
    target_price: Optional[float] = None
    percent_change: Optional[float] = None
    is_triggered: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    triggered_at: Optional[datetime] = None
    
    def trigger(self, current_price: float) -> None:
        """
        Marca o alerta como disparado.
        
        Args:
            current_price: Preço atual que disparou o alerta.
        """
        self.is_triggered = True
        self.triggered_at = datetime.now(DEFAULT_TIMEZONE)
    
    @property
    def alert_type(self) -> str:
        """Retorna o tipo de alerta."""
        if self.target_price is not None:
            return "Preço alvo"
        elif self.percent_change is not None:
            return "Variação percentual"
        else:
            return "Desconhecido"
    
    @property
    def description(self) -> str:
        """Retorna uma descrição do alerta."""
        if self.target_price is not None:
            return f"Preço alvo: {self.target_price:.8f}".rstrip('0').rstrip('.')
        elif self.percent_change is not None:
            sign = "+" if self.percent_change > 0 else ""
            return f"Variação: {sign}{self.percent_change:.2f}%"
        else:
            return "Alerta sem condição definida"


@dataclass
class EMAModel:
    """Modelo para representar os valores de EMA."""
    symbol: str
    timeframe: str
    ema_short: float
    ema_medium: float
    ema_long: float
    price_above_ema_short: bool
    price_above_ema_medium: bool
    price_above_ema_long: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "ema_short": self.ema_short,
            "ema_medium": self.ema_medium,
            "ema_long": self.ema_long,
            "price_above_ema_short": self.price_above_ema_short,
            "price_above_ema_medium": self.price_above_ema_medium,
            "price_above_ema_long": self.price_above_ema_long
        }


@dataclass
class RSIModel:
    """Modelo para representar o valor de RSI."""
    symbol: str
    timeframe: str
    value: float
    is_oversold: bool
    is_overbought: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "value": self.value,
            "is_oversold": self.is_oversold,
            "is_overbought": self.is_overbought
        }


@dataclass
class CryptoNews:
    """Modelo para representar uma notícia de criptomoeda."""
    title: str
    url: str
    source: str
    published_at: str
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
            "image_url": self.image_url
        }


@dataclass
class VMCAnalysisResult:
    """Modelo para representar o resultado da análise do VMC Cipher Divergency."""
    symbol: str
    timeframe: str
    has_green_circle: bool
    has_gold_circle: bool
    has_red_circle: bool
    has_purple_triangle: bool
    timestamp: float = None
    
    def __post_init__(self):
        """Inicializa campos adicionais após a criação."""
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "has_green_circle": self.has_green_circle,
            "has_gold_circle": self.has_gold_circle,
            "has_red_circle": self.has_red_circle,
            "has_purple_triangle": self.has_purple_triangle,
            "timestamp": self.timestamp
        }


@dataclass
class PerfectBuyOpportunity:
    """Modelo para representar uma oportunidade perfeita de compra (círculo verde no timeframe de 1 semana)."""
    symbol: str
    price: float
    timestamp: float = None
    
    def __post_init__(self):
        """Inicializa campos adicionais após a criação."""
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "timestamp": self.timestamp
        }


@dataclass
class GreatBuyOpportunity:
    """Modelo para representar uma ótima oportunidade de compra (círculo verde nos timeframes de 3h, 4h e 12h)."""
    symbol: str
    price: float
    timeframes: List[str]
    timestamp: float = None
    
    def __post_init__(self):
        """Inicializa campos adicionais após a criação."""
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "timeframes": self.timeframes,
            "timestamp": self.timestamp
        }


@dataclass
class VMCCipherIndicator:
    """Modelo para o indicador VMC Cipher."""
    symbol: str
    timeframe: str
    wt1: float
    wt2: float
    rsi: float
    is_overbought: bool
    is_oversold: bool
    has_green_circle: bool
    has_gold_circle: bool
    has_red_circle: bool
    has_purple_triangle: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(DEFAULT_TIMEZONE))
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "wt1": self.wt1,
            "wt2": self.wt2,
            "rsi": self.rsi,
            "is_overbought": self.is_overbought,
            "is_oversold": self.is_oversold,
            "has_green_circle": self.has_green_circle,
            "has_gold_circle": self.has_gold_circle,
            "has_red_circle": self.has_red_circle,
            "has_purple_triangle": self.has_purple_triangle,
            "timestamp": self.timestamp.timestamp()
        }
    
    @property
    def formatted_time(self) -> str:
        """Retorna o timestamp formatado."""
        return self.timestamp.strftime("%d/%m/%Y %H:%M:%S")
    
    @property
    def signal(self) -> str:
        """Retorna o sinal de trading com base nos indicadores."""
        if self.has_green_circle:
            return "Compra (Círculo Verde)"
        elif self.has_gold_circle:
            return "Compra (Círculo Dourado)"
        elif self.has_red_circle:
            return "Venda (Círculo Vermelho)"
        elif self.has_purple_triangle:
            return "Alerta de Divergência (Triângulo Roxo)"
        elif self.is_overbought:
            return "Sobrecomprado"
        elif self.is_oversold:
            return "Sobrevendido"
        else:
            return "Neutro" 