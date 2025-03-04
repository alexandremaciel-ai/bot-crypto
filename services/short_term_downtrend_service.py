"""Serviço para detecção de criptomoedas com tendência de baixa de curto prazo."""

from typing import Dict, List, Optional, Any
import asyncio
from config import DEFAULT_SYMBOLS
from utils.logger import get_logger, log_exception
from models.crypto import EMAIndicator, RSIIndicator

class ShortTermDowntrendChecker:
    """Classe para verificação de criptomoedas com tendência de baixa de curto prazo."""
    
    def __init__(self, crypto_service, telegram_service, vmc_cipher_service):
        """
        Inicializa o verificador de tendência de baixa de curto prazo.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
            vmc_cipher_service: Serviço do VMC Cipher.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        self.vmc_cipher_service = vmc_cipher_service
        self.logger = get_logger(__name__)
        self.max_coins = 20  # Limite máximo de moedas a serem exibidas
    
    async def check_downtrend(self) -> None:
        """Verifica criptomoedas com tendência de baixa de curto prazo e envia notificações."""
        try:
            self.logger.info("Verificando criptomoedas com tendência de baixa de curto prazo...")
            downtrend_coins = await self._analyze_market()
            
            if downtrend_coins:
                # Formata e envia a mensagem para o Telegram
                message = self._format_downtrend_message(downtrend_coins)
                await self.telegram_service.send_to_default_chat(message)
                self.logger.info(f"Encontradas {len(downtrend_coins)} moedas com tendência de baixa de curto prazo")
            else:
                self.logger.info("Nenhuma moeda com tendência de baixa de curto prazo encontrada")
                
        except Exception as e:
            log_exception(self.logger, e, "Erro ao verificar moedas com tendência de baixa de curto prazo")
    
    async def _analyze_market(self) -> List[Dict[str, Any]]:
        """Analisa o mercado em busca de moedas com tendência de baixa de curto prazo."""
        downtrend_coins = []
        
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
                    # Verifica as condições para tendência de baixa de curto prazo
                    is_downtrend = await self._check_downtrend_conditions(symbol)
                    
                    if is_downtrend:
                        # Obtém o preço atual
                        price = await self.crypto_service.get_price(symbol)
                        
                        # Adiciona à lista de moedas em tendência de baixa
                        downtrend_coins.append({
                            "symbol": symbol,
                            "price": price.price,
                            "formatted_price": price.formatted_price
                        })
                        
                        # Limita a quantidade de moedas
                        if len(downtrend_coins) >= self.max_coins:
                            break
                            
                except Exception as e:
                    log_exception(self.logger, e, f"Erro ao analisar {symbol} para tendência de baixa de curto prazo")
        
        except Exception as e:
            log_exception(self.logger, e, "Erro ao obter símbolos disponíveis")
            # Fallback para a lista padrão de símbolos
            self.logger.info("Usando lista padrão de símbolos como fallback")
            
            for symbol in DEFAULT_SYMBOLS:
                try:
                    # Verifica as condições para tendência de baixa de curto prazo
                    is_downtrend = await self._check_downtrend_conditions(symbol)
                    
                    if is_downtrend:
                        # Obtém o preço atual
                        price = await self.crypto_service.get_price(symbol)
                        
                        # Adiciona à lista de moedas em tendência de baixa
                        downtrend_coins.append({
                            "symbol": symbol,
                            "price": price.price,
                            "formatted_price": price.formatted_price
                        })
                        
                except Exception as e:
                    log_exception(self.logger, e, f"Erro ao analisar {symbol} para tendência de baixa de curto prazo")
        
        return downtrend_coins
    
    async def _check_downtrend_conditions(self, symbol: str) -> bool:
        """
        Verifica se uma criptomoeda atende às condições para tendência de baixa de curto prazo.
        
        Condições:
        1. RSI abaixo de 45 no timeframe de 4 horas
        2. VMC Cipher com círculo vermelho no timeframe de 1 hora
        
        Args:
            symbol: Símbolo da criptomoeda.
            
        Returns:
            bool: True se atender às condições, False caso contrário.
        """
        try:
            # Condição 1: RSI abaixo de 45 no timeframe de 4 horas
            df_4h = await self.crypto_service.get_historical_data(symbol, "4h")
            
            # Calcula RSI para 4 horas
            delta = df_4h["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            current_rsi = rsi.iloc[-1]
            
            # Verifica se o RSI está abaixo de 45
            condition_1 = current_rsi < 45
            
            if not condition_1:
                return False
            
            # Condição 2: VMC Cipher com círculo vermelho no timeframe de 1 hora
            vmc_result = await self.vmc_cipher_service.analyze_symbol(symbol, "1h")
            condition_2 = vmc_result.red_circle
            
            return condition_2
            
        except Exception as e:
            log_exception(self.logger, e, f"Erro ao verificar condições de tendência de baixa para {symbol}")
            return False
    
    def _format_downtrend_message(self, downtrend_coins: List[Dict[str, Any]]) -> str:
        """
        Formata a mensagem com as criptomoedas em tendência de baixa de curto prazo.
        
        Args:
            downtrend_coins: Lista de criptomoedas em tendência de baixa.
            
        Returns:
            str: Mensagem formatada.
        """
        message = "📉 <b>TENDÊNCIA DE BAIXA DE CURTO PRAZO</b> 📉\n\n"
        message += "Criptomoedas que atendem aos seguintes critérios:\n"
        message += "• RSI abaixo de 45 (4h)\n"
        message += "• VMC Cipher com círculo vermelho (1h)\n\n"
        
        for coin in downtrend_coins:
            message += f"💰 <b>{coin['symbol']}</b>: {coin['formatted_price']} USDT\n"
        
        return message 