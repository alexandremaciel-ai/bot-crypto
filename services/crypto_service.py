"""
Serviço para obtenção e processamento de dados de criptomoedas.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator as TaRSIIndicator
from ta.trend import IchimokuIndicator

from config import BINANCE_API_KEY, BINANCE_API_SECRET, TECHNICAL_INDICATORS, DEFAULT_TIMEZONE
from models.crypto import (
    CryptoPrice, PriceChange, EMAIndicator as EMAModel,
    RSIIndicator as RSIModel, VolumeAnalysis, TechnicalAnalysis
)
from models.news import CryptoNews
from utils.logger import get_logger, log_api_error, log_exception

# Configuração do logger
logger = get_logger(__name__)

# URLs da API da Binance
BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_API_ENDPOINTS = {
    "ticker_price": "/api/v3/ticker/price",
    "klines": "/api/v3/klines",
    "ticker_24hr": "/api/v3/ticker/24hr",
}

# Mapeamento de intervalos de tempo para a API da Binance
TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}

# Cache para dados de preços
price_cache: Dict[str, CryptoPrice] = {}
# Cache para dados históricos
historical_data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
# Timestamp da última atualização do cache
last_cache_update: Dict[str, float] = {}


class CryptoService:
    """Serviço para obtenção e processamento de dados de criptomoedas."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Inicializa o serviço de criptomoedas.
        
        Args:
            session: Sessão HTTP opcional para reutilização.
        """
        self.session = session
        self.own_session = session is None
        self.cache_ttl = 60  # Tempo de vida do cache em segundos
    
    async def __aenter__(self):
        """Gerenciador de contexto para entrada."""
        if self.own_session:
            self.session = aiohttp.ClientSession(
                headers={"X-MBX-APIKEY": BINANCE_API_KEY} if BINANCE_API_KEY else {}
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Gerenciador de contexto para saída."""
        if self.own_session and self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Faz uma requisição para a API da Binance.
        
        Args:
            endpoint: Endpoint da API.
            params: Parâmetros da requisição.
            
        Returns:
            Dict[str, Any]: Resposta da API.
            
        Raises:
            Exception: Se ocorrer um erro na requisição.
        """
        if not self.session:
            raise RuntimeError("Sessão HTTP não inicializada. Use o gerenciador de contexto.")
        
        url = f"{BINANCE_BASE_URL}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_api_error(logger, "Binance", endpoint, f"Status {response.status}: {error_text}")
                    raise Exception(f"Erro na API da Binance: {error_text}")
                
                return await response.json()
        except aiohttp.ClientError as e:
            log_exception(logger, e, f"Erro ao fazer requisição para {url}")
            raise
    
    async def get_price(self, symbol: str) -> CryptoPrice:
        """
        Obtém o preço atual de uma criptomoeda.
        
        Args:
            symbol: Símbolo da criptomoeda.
            
        Returns:
            CryptoPrice: Modelo com o preço atual.
            
        Raises:
            Exception: Se ocorrer um erro na requisição.
        """
        symbol = symbol.upper()
        
        # Formata o símbolo para o padrão da Binance (adiciona USDT se necessário)
        api_symbol = f"{symbol}USDT" if not symbol.endswith("USDT") else symbol
        
        # Verifica se o preço está em cache e se ainda é válido
        if symbol in price_cache and time.time() - last_cache_update.get(symbol, 0) < self.cache_ttl:
            return price_cache[symbol]
        
        try:
            response = await self._make_request(
                BINANCE_API_ENDPOINTS["ticker_price"],
                {"symbol": api_symbol}
            )
            
            price = float(response["price"])
            crypto_price = CryptoPrice(symbol=symbol, price=price)
            
            # Atualiza o cache
            price_cache[symbol] = crypto_price
            last_cache_update[symbol] = time.time()
            
            return crypto_price
        except Exception as e:
            log_exception(logger, e, f"Erro ao obter preço para {symbol}")
            raise
    
    async def get_prices(self, symbols: List[str]) -> Dict[str, CryptoPrice]:
        """
        Obtém os preços atuais de múltiplas criptomoedas.
        
        Args:
            symbols: Lista de símbolos de criptomoedas.
            
        Returns:
            Dict[str, CryptoPrice]: Dicionário de símbolos para preços.
            
        Raises:
            Exception: Se ocorrer um erro na requisição.
        """
        symbols = [s.upper() for s in symbols]
        result: Dict[str, CryptoPrice] = {}
        
        # Filtra símbolos que não estão em cache ou cujo cache expirou
        symbols_to_fetch = [
            symbol for symbol in symbols
            if symbol not in price_cache or time.time() - last_cache_update.get(symbol, 0) >= self.cache_ttl
        ]
        
        # Adiciona símbolos que estão em cache
        for symbol in symbols:
            if symbol not in symbols_to_fetch and symbol in price_cache:
                result[symbol] = price_cache[symbol]
        
        if not symbols_to_fetch:
            return result
        
        try:
            # Obtém todos os preços da API
            response = await self._make_request(BINANCE_API_ENDPOINTS["ticker_price"])
            
            # Filtra apenas os símbolos solicitados
            price_map = {item["symbol"]: float(item["price"]) for item in response}
            
            for symbol in symbols_to_fetch:
                if symbol in price_map:
                    crypto_price = CryptoPrice(symbol=symbol, price=price_map[symbol])
                    result[symbol] = crypto_price
                    
                    # Atualiza o cache
                    price_cache[symbol] = crypto_price
                    last_cache_update[symbol] = time.time()
            
            return result
        except Exception as e:
            log_exception(logger, e, f"Erro ao obter preços para {symbols}")
            raise
    
    async def get_available_symbols(self, quote_asset: str = "USDT") -> List[str]:
        """
        Obtém a lista de símbolos disponíveis na API da Binance.
        
        Args:
            quote_asset: Ativo de cotação (ex: USDT, BTC, etc).
            
        Returns:
            List[str]: Lista de símbolos disponíveis.
            
        Raises:
            Exception: Se ocorrer um erro na requisição.
        """
        try:
            # Endpoint para obter informações de todos os pares de negociação
            exchange_info_endpoint = "/api/v3/exchangeInfo"
            
            # Faz a requisição para obter as informações
            response = await self._make_request(exchange_info_endpoint)
            
            # Filtra os símbolos que têm o quote_asset especificado
            symbols = []
            for symbol_info in response.get("symbols", []):
                if symbol_info.get("status") == "TRADING" and symbol_info.get("quoteAsset") == quote_asset:
                    base_asset = symbol_info.get("baseAsset")
                    symbols.append(base_asset)
            
            return symbols
        except Exception as e:
            log_exception(logger, e, "Erro ao obter símbolos disponíveis")
            raise
    
    async def get_price_change(self, symbol: str) -> PriceChange:
        """
        Obtém a variação de preço de uma criptomoeda nas últimas 24 horas.
        
        Args:
            symbol: Símbolo da criptomoeda.
            
        Returns:
            PriceChange: Modelo com a variação de preço.
            
        Raises:
            Exception: Se ocorrer um erro na requisição.
        """
        symbol = symbol.upper()
        
        # Formata o símbolo para o padrão da Binance (adiciona USDT se necessário)
        api_symbol = f"{symbol}USDT" if not symbol.endswith("USDT") else symbol
        
        try:
            response = await self._make_request(
                BINANCE_API_ENDPOINTS["ticker_24hr"],
                {"symbol": api_symbol}
            )
            
            current_price = float(response["lastPrice"])
            previous_price = float(response["openPrice"])
            percent_change = float(response["priceChangePercent"])
            
            return PriceChange(
                symbol=symbol,
                current_price=current_price,
                previous_price=previous_price,
                percent_change=percent_change
            )
        except Exception as e:
            log_exception(logger, e, f"Erro ao obter variação de preço para {symbol}")
            raise
    
    async def get_historical_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Obtém dados históricos de uma criptomoeda.
        
        Args:
            symbol: Símbolo da criptomoeda.
            timeframe: Intervalo de tempo.
            limit: Quantidade de candles.
            
        Returns:
            pd.DataFrame: DataFrame com os dados históricos.
            
        Raises:
            Exception: Se ocorrer um erro na requisição.
        """
        symbol = symbol.upper()
        
        # Formata o símbolo para o padrão da Binance (adiciona USDT se necessário)
        api_symbol = f"{symbol}USDT" if not symbol.endswith("USDT") else symbol
        
        # Cria uma chave para o cache
        cache_key = f"{symbol}_{timeframe}"
        
        # Verifica se os dados estão em cache e se ainda são válidos
        if (
            symbol in historical_data_cache and
            timeframe in historical_data_cache[symbol] and
            time.time() - last_cache_update.get(cache_key, 0) < self.cache_ttl
        ):
            return historical_data_cache.get(symbol, {}).get(timeframe, pd.DataFrame())
        
        try:
            # Verifica se o timeframe é válido
            if timeframe not in TIMEFRAME_MAP:
                raise ValueError(f"Timeframe inválido: {timeframe}")
            
            response = await self._make_request(
                BINANCE_API_ENDPOINTS["klines"],
                {
                    "symbol": api_symbol,
                    "interval": TIMEFRAME_MAP[timeframe],
                    "limit": limit
                }
            )
            
            # Converte a resposta para um DataFrame
            df = pd.DataFrame(response, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ])
            
            # Converte tipos de dados
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            
            # Define o timestamp como índice
            df.set_index("timestamp", inplace=True)
            
            # Atualiza o cache
            if symbol not in historical_data_cache:
                historical_data_cache[symbol] = {}
            historical_data_cache[symbol][timeframe] = df
            last_cache_update[cache_key] = time.time()
            
            return df
        except Exception as e:
            log_exception(logger, e, f"Erro ao obter dados históricos para {symbol} ({timeframe})")
            raise
    
    async def calculate_ema(self, symbol: str, timeframe: str) -> EMAModel:
        """
        Calcula o indicador EMA (Exponential Moving Average).
        
        Args:
            symbol: Símbolo da criptomoeda.
            timeframe: Intervalo de tempo.
            
        Returns:
            EMAModel: Modelo com os valores de EMA.
            
        Raises:
            Exception: Se ocorrer um erro no cálculo.
        """
        try:
            # Obtém dados históricos
            df = await self.get_historical_data(symbol, timeframe)
            
            # Obtém períodos da configuração
            short_period = TECHNICAL_INDICATORS["ema"]["short_period"]
            medium_period = TECHNICAL_INDICATORS["ema"]["medium_period"]
            long_period = TECHNICAL_INDICATORS["ema"]["long_period"]
            
            # Calcula EMAs
            short_ema = EMAIndicator(close=df["close"], window=short_period).ema_indicator().iloc[-1]
            medium_ema = EMAIndicator(close=df["close"], window=medium_period).ema_indicator().iloc[-1]
            long_ema = EMAIndicator(close=df["close"], window=long_period).ema_indicator().iloc[-1]
            
            return EMAModel(
                symbol=symbol,
                timeframe=timeframe,
                short_ema=short_ema,
                medium_ema=medium_ema,
                long_ema=long_ema
            )
        except Exception as e:
            log_exception(logger, e, f"Erro ao calcular EMA para {symbol} ({timeframe})")
            raise
    
    async def calculate_rsi(self, symbol: str, timeframe: str) -> RSIModel:
        """
        Calcula o indicador RSI (Relative Strength Index).
        
        Args:
            symbol: Símbolo da criptomoeda.
            timeframe: Intervalo de tempo.
            
        Returns:
            RSIModel: Modelo com o valor de RSI.
            
        Raises:
            Exception: Se ocorrer um erro no cálculo.
        """
        try:
            # Obtém dados históricos
            df = await self.get_historical_data(symbol, timeframe)
            
            # Obtém período da configuração
            period = TECHNICAL_INDICATORS["rsi"]["period"]
            
            # Calcula RSI
            rsi = TaRSIIndicator(close=df["close"], window=period).rsi().iloc[-1]
            
            return RSIModel(
                symbol=symbol,
                timeframe=timeframe,
                value=rsi,
                overbought_threshold=TECHNICAL_INDICATORS["rsi"]["overbought"],
                oversold_threshold=TECHNICAL_INDICATORS["rsi"]["oversold"]
            )
        except Exception as e:
            log_exception(logger, e, f"Erro ao calcular RSI para {symbol} ({timeframe})")
            raise
    
    async def analyze_volume(self, symbol: str, timeframe: str) -> VolumeAnalysis:
        """
        Analisa o volume de negociação.
        
        Args:
            symbol: Símbolo da criptomoeda.
            timeframe: Intervalo de tempo.
            
        Returns:
            VolumeAnalysis: Modelo com a análise de volume.
            
        Raises:
            Exception: Se ocorrer um erro na análise.
        """
        try:
            # Obtém dados históricos
            df = await self.get_historical_data(symbol, timeframe)
            
            # Obtém período da configuração
            period = TECHNICAL_INDICATORS["volume"]["period"]
            
            # Calcula volume atual e médio
            current_volume = df["volume"].iloc[-1]
            average_volume = df["volume"].rolling(window=period).mean().iloc[-1]
            
            # Verifica se o volume está aumentando (comparando com o volume anterior)
            volume_increasing = df["volume"].iloc[-1] > df["volume"].iloc[-2] if len(df) >= 2 else False
            
            return VolumeAnalysis(
                symbol=symbol,
                timeframe=timeframe,
                current_volume=current_volume,
                average_volume=average_volume,
                volume_increasing=volume_increasing
            )
        except Exception as e:
            log_exception(logger, e, f"Erro ao analisar volume para {symbol} ({timeframe})")
            raise
    
    async def get_technical_analysis(self, symbol: str, timeframes: List[str]) -> TechnicalAnalysis:
        """
        Obtém análise técnica completa para uma criptomoeda.
        
        Args:
            symbol: Símbolo da criptomoeda.
            timeframes: Lista de intervalos de tempo.
            
        Returns:
            TechnicalAnalysis: Modelo com a análise técnica completa.
            
        Raises:
            Exception: Se ocorrer um erro na análise.
        """
        try:
            # Obtém preço atual
            price = await self.get_price(symbol)
            
            # Inicializa dicionários para indicadores
            ema_dict = {}
            rsi_dict = {}
            volume_dict = {}
            
            # Calcula indicadores para cada timeframe
            for timeframe in timeframes:
                # Executa cálculos em paralelo
                ema, rsi, volume = await asyncio.gather(
                    self.calculate_ema(symbol, timeframe),
                    self.calculate_rsi(symbol, timeframe),
                    self.analyze_volume(symbol, timeframe)
                )
                
                ema_dict[timeframe] = ema
                rsi_dict[timeframe] = rsi
                volume_dict[timeframe] = volume
            
            return TechnicalAnalysis(
                symbol=symbol,
                price=price,
                ema=ema_dict,
                rsi=rsi_dict,
                volume=volume_dict
            )
        except Exception as e:
            log_exception(logger, e, f"Erro ao obter análise técnica para {symbol}")
            raise
    
    async def check_price_alerts(self, symbol: str, target_price: float) -> Tuple[bool, float]:
        """
        Verifica se o preço atingiu um alvo.
        
        Args:
            symbol: Símbolo da criptomoeda.
            target_price: Preço alvo.
            
        Returns:
            Tuple[bool, float]: Tupla com flag de alerta disparado e preço atual.
            
        Raises:
            Exception: Se ocorrer um erro na verificação.
        """
        try:
            price = await self.get_price(symbol)
            return price.price >= target_price, price.price
        except Exception as e:
            log_exception(logger, e, f"Erro ao verificar alerta de preço para {symbol}")
            raise
    
    async def check_percent_change_alerts(self, symbol: str, percent_threshold: float) -> Tuple[bool, float, float]:
        """
        Verifica se a variação percentual atingiu um limiar.
        
        Args:
            symbol: Símbolo da criptomoeda.
            percent_threshold: Limiar percentual.
            
        Returns:
            Tuple[bool, float, float]: Tupla com flag de alerta disparado, variação percentual e preço atual.
            
        Raises:
            Exception: Se ocorrer um erro na verificação.
        """
        try:
            price_change = await self.get_price_change(symbol)
            triggered = abs(price_change.percent_change) >= abs(percent_threshold)
            
            # Verifica se a direção da mudança corresponde à direção do limiar
            if percent_threshold > 0 and price_change.percent_change < 0:
                triggered = False
            elif percent_threshold < 0 and price_change.percent_change > 0:
                triggered = False
            
            return triggered, price_change.percent_change, price_change.current_price
        except Exception as e:
            log_exception(logger, e, f"Erro ao verificar alerta de variação para {symbol}")
            raise 
    
    async def get_crypto_news(self) -> List[CryptoNews]:
        """
        Obtém as últimas notícias sobre criptomoedas de fontes populares.
        
        Returns:
            List[CryptoNews]: Lista de notícias de criptomoedas.
        """
        if not self.session:
            raise RuntimeError("Sessão HTTP não inicializada. Use o gerenciador de contexto.")
        
        logger.info("Buscando notícias de criptomoedas")
        
        # Lista de fontes de notícias de criptomoedas
        news_sources = [
            {
                "name": "CoinDesk",
                "url": "https://api.coindesk.com/v1/currency/feed",
                "parser": self._parse_coindesk_news
            },
            {
                "name": "CryptoCompare",
                "url": "https://min-api.cryptocompare.com/data/v2/news/?lang=PT",
                "parser": self._parse_cryptocompare_news
            }
        ]
        
        all_news = []
        
        # Busca notícias de cada fonte
        for source in news_sources:
            try:
                news = await self._fetch_news_from_source(source)
                all_news.extend(news)
            except Exception as e:
                log_exception(logger, e, f"Erro ao buscar notícias de {source['name']}")
        
        # Ordena as notícias por data de publicação (mais recentes primeiro)
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        
        return all_news
    
    async def _fetch_news_from_source(self, source: Dict[str, Any]) -> List[CryptoNews]:
        """
        Busca notícias de uma fonte específica.
        
        Args:
            source: Informações da fonte de notícias.
            
        Returns:
            List[CryptoNews]: Lista de notícias da fonte.
        """
        try:
            async with self.session.get(source["url"]) as response:
                if response.status != 200:
                    logger.warning(f"Erro ao buscar notícias de {source['name']}: {response.status}")
                    return []
                
                data = await response.json()
                return source["parser"](data, source["name"])
        except Exception as e:
            log_exception(logger, e, f"Erro ao buscar notícias de {source['name']}")
            return []
    
    def _parse_coindesk_news(self, data: Dict[str, Any], source_name: str) -> List[CryptoNews]:
        """
        Processa dados de notícias do CoinDesk.
        
        Args:
            data: Dados da API do CoinDesk.
            source_name: Nome da fonte.
            
        Returns:
            List[CryptoNews]: Lista de notícias processadas.
        """
        news_list = []
        
        try:
            articles = data.get("channel", {}).get("item", [])
            
            for article in articles[:10]:  # Limita a 10 notícias
                try:
                    title = article.get("title", "")
                    url = article.get("link", "")
                    summary = article.get("description", "")
                    pub_date_str = article.get("pubDate", "")
                    
                    # Converte a string de data para objeto datetime
                    try:
                        from email.utils import parsedate_to_datetime
                        published_at = parsedate_to_datetime(pub_date_str)
                    except Exception:
                        published_at = datetime.now(DEFAULT_TIMEZONE)
                    
                    news = CryptoNews(
                        title=title,
                        url=url,
                        source=source_name,
                        summary=summary,
                        published_at=published_at
                    )
                    
                    news_list.append(news)
                except Exception as e:
                    logger.warning(f"Erro ao processar notícia do CoinDesk: {str(e)}")
        except Exception as e:
            logger.warning(f"Erro ao processar dados do CoinDesk: {str(e)}")
        
        return news_list
    
    def _parse_cryptocompare_news(self, data: Dict[str, Any], source_name: str) -> List[CryptoNews]:
        """
        Processa dados de notícias do CryptoCompare.
        
        Args:
            data: Dados da API do CryptoCompare.
            source_name: Nome da fonte.
            
        Returns:
            List[CryptoNews]: Lista de notícias processadas.
        """
        news_list = []
        
        try:
            articles = data.get("Data", [])
            
            for article in articles[:10]:  # Limita a 10 notícias
                try:
                    title = article.get("title", "")
                    url = article.get("url", "")
                    summary = article.get("body", "")
                    source = article.get("source", source_name)
                    pub_time = article.get("published_on", 0)
                    
                    # Converte o timestamp para objeto datetime
                    try:
                        published_at = datetime.fromtimestamp(pub_time, DEFAULT_TIMEZONE)
                    except Exception:
                        published_at = datetime.now(DEFAULT_TIMEZONE)
                    
                    news = CryptoNews(
                        title=title,
                        url=url,
                        source=source,
                        summary=summary[:100] + "..." if summary and len(summary) > 100 else summary,
                        published_at=published_at
                    )
                    
                    news_list.append(news)
                except Exception as e:
                    logger.warning(f"Erro ao processar notícia do CryptoCompare: {str(e)}")
        except Exception as e:
            logger.warning(f"Erro ao processar dados do CryptoCompare: {str(e)}")
        
        return news_list