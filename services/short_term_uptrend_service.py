"""Serviço para detecção de criptomoedas com tendência de alta de curto prazo."""

from typing import Dict, List, Optional, Any
import asyncio
from config import DEFAULT_SYMBOLS
from utils.logger import get_logger, log_exception
from models.crypto import EMAIndicator, RSIIndicator

class ShortTermUptrendChecker:
    """Classe para verificação de criptomoedas com tendência de alta de curto prazo."""
    
    def __init__(self, crypto_service, telegram_service):
        """
        Inicializa o verificador de tendência de alta de curto prazo.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        self.logger = get_logger(__name__)
        self.max_coins = 20  # Limite máximo de moedas a serem exibidas
    
    async def check_uptrend(self) -> None:
        """Verifica criptomoedas com tendência de alta de curto prazo e envia notificações."""
        try:
            self.logger.info("Verificando criptomoedas com tendência de alta de curto prazo...")
            uptrend_coins = await self._analyze_market()
            
            if uptrend_coins:
                # Formata e envia a mensagem para o Telegram
                message = self._format_uptrend_message(uptrend_coins)
                await self.telegram_service.send_to_default_chat(message)
                self.logger.info(f"Encontradas {len(uptrend_coins)} moedas com tendência de alta de curto prazo")
            else:
                self.logger.info("Nenhuma moeda com tendência de alta de curto prazo encontrada")
                
        except Exception as e:
            log_exception(self.logger, e, "Erro ao verificar moedas com tendência de alta de curto prazo")
    
    async def _analyze_market(self) -> List[Dict[str, Any]]:
        """Analisa o mercado em busca de moedas com tendência de alta de curto prazo."""
        uptrend_coins = []
        
        try:
            # Obtém a lista de símbolos disponíveis na API
            available_symbols = await self.crypto_service.get_available_symbols()
            self.logger.info(f"Analisando {len(available_symbols)} criptomoedas disponíveis na API")
            
            # Limita a quantidade de símbolos para análise (para evitar sobrecarga)
            max_symbols_to_analyze = 100
            symbols_to_analyze = available_symbols[:max_symbols_to_analyze]
            
            # Analisa cada símbolo
            for symbol in symbols_to_analyze:
                try:
                    # Verifica as condições para tendência de alta de curto prazo
                    is_uptrend = await self._check_uptrend_conditions(symbol)
                    
                    if is_uptrend:
                        # Obtém o preço atual
                        price = await self.crypto_service.get_price(symbol)
                        
                        # Adiciona à lista de moedas em tendência de alta
                        uptrend_coins.append({
                            "symbol": symbol,
                            "price": price.price,
                            "formatted_price": price.formatted_price
                        })
                        
                        # Limita a quantidade de moedas
                        if len(uptrend_coins) >= self.max_coins:
                            break
                            
                except Exception as e:
                    log_exception(self.logger, e, f"Erro ao analisar {symbol} para tendência de alta de curto prazo")
        
        except Exception as e:
            log_exception(self.logger, e, "Erro ao obter símbolos disponíveis")
            # Fallback para a lista padrão de símbolos
            self.logger.info("Usando lista padrão de símbolos como fallback")
            
            for symbol in DEFAULT_SYMBOLS:
                try:
                    # Verifica as condições para tendência de alta de curto prazo
                    is_uptrend = await self._check_uptrend_conditions(symbol)
                    
                    if is_uptrend:
                        # Obtém o preço atual
                        price = await self.crypto_service.get_price(symbol)
                        
                        # Adiciona à lista de moedas em tendência de alta
                        uptrend_coins.append({
                            "symbol": symbol,
                            "price": price.price,
                            "formatted_price": price.formatted_price
                        })
                        
                except Exception as e:
                    log_exception(self.logger, e, f"Erro ao analisar {symbol} para tendência de alta de curto prazo")
        
        return uptrend_coins
    
    async def _check_uptrend_conditions(self, symbol: str) -> bool:
        """
        Verifica se uma criptomoeda atende às condições para tendência de alta de curto prazo.
        
        Condições:
        1. Preço acima das EMAs 8 e 14 no timeframe de 4 horas
        2. EMA 8 acima da EMA 14 no timeframe de 30 minutos
        3. RSI acima do RSI Based MA no timeframe de 1 hora
        
        Args:
            symbol: Símbolo da criptomoeda.
            
        Returns:
            bool: True se atender às condições, False caso contrário.
        """
        try:
            # Obtém dados para o timeframe de 4 horas
            df_4h = await self.crypto_service.get_historical_data(symbol, "4h")
            
            # Calcula EMAs para 4 horas
            ema_8_4h = df_4h["close"].ewm(span=8, adjust=False).mean().iloc[-1]
            ema_14_4h = df_4h["close"].ewm(span=14, adjust=False).mean().iloc[-1]
            current_price_4h = df_4h["close"].iloc[-1]
            
            # Verifica condição 1: Preço acima das EMAs 8 e 14 no timeframe de 4 horas
            condition_1 = current_price_4h > ema_8_4h and current_price_4h > ema_14_4h
            
            if not condition_1:
                return False
            
            # Obtém dados para o timeframe de 30 minutos
            df_30m = await self.crypto_service.get_historical_data(symbol, "30m")
            
            # Calcula EMAs para 30 minutos
            ema_8_30m = df_30m["close"].ewm(span=8, adjust=False).mean().iloc[-1]
            ema_14_30m = df_30m["close"].ewm(span=14, adjust=False).mean().iloc[-1]
            
            # Verifica condição 2: EMA 8 acima da EMA 14 no timeframe de 30 minutos
            condition_2 = ema_8_30m > ema_14_30m
            
            if not condition_2:
                return False
            
            # Obtém dados para o timeframe de 1 hora
            df_1h = await self.crypto_service.get_historical_data(symbol, "1h")
            
            # Calcula RSI para 1 hora
            delta = df_1h["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Calcula RSI Based MA (média móvel do RSI)
            rsi_ma = rsi.rolling(window=9).mean()
            
            # Verifica condição 3: RSI acima do RSI Based MA no timeframe de 1 hora
            condition_3 = rsi.iloc[-1] > rsi_ma.iloc[-1]
            
            return condition_3
            
        except Exception as e:
            log_exception(self.logger, e, f"Erro ao verificar condições de tendência de alta para {symbol}")
            return False
    
    def _format_uptrend_message(self, uptrend_coins: List[Dict[str, Any]]) -> str:
        """
        Formata a mensagem com as criptomoedas em tendência de alta de curto prazo.
        
        Args:
            uptrend_coins: Lista de criptomoedas em tendência de alta.
            
        Returns:
            str: Mensagem formatada.
        """
        message = "🚀 <b>TENDÊNCIA DE ALTA DE CURTO PRAZO</b> 🚀\n\n"
        message += "Criptomoedas que atendem aos seguintes critérios:\n"
        message += "• Preço acima das EMAs 8 e 14 (4h)\n"
        message += "• EMA 8 acima da EMA 14 (30m)\n"
        message += "• RSI acima do RSI Based MA (1h)\n\n"
        
        for coin in uptrend_coins:
            message += f"💰 <b>{coin['symbol']}</b>: {coin['formatted_price']} USDT\n"
        
        return message 