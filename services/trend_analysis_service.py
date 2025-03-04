"""Serviço para análise de tendência de criptomoedas."""

from typing import Dict, List, Optional
from config import DEFAULT_SYMBOLS
from utils.logger import get_logger, log_exception

class TrendAnalysisChecker:
    """Classe para verificação de tendências de alta em criptomoedas."""
    
    def __init__(self, crypto_service, telegram_service):
        """
        Inicializa o verificador de tendências.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        self.logger = get_logger(__name__)
        self.timeframes = ['1h', '4h']
        self.ema_periods = [8, 14]
        self.rsi_threshold = 50
    
    async def check_trends(self) -> None:
        """Verifica tendências de alta e envia notificações."""
        try:
            trending_coins = await self._analyze_trends()
            
            if trending_coins:
                # Formata e envia a mensagem para o Telegram
                message = self._format_trends_message(trending_coins)
                await self.telegram_service.send_to_default_chat(message)
                self.logger.info(f"Encontradas {len(trending_coins)} moedas em tendência de alta")
            else:
                self.logger.info("Nenhuma moeda em tendência de alta encontrada")
                
        except Exception as e:
            log_exception(self.logger, e, "Erro ao verificar tendências de alta")
    
    async def _analyze_trends(self) -> List[Dict[str, any]]:
        """Analisa o mercado em busca de tendências de alta."""
        trending_coins = []
        
        for symbol in DEFAULT_SYMBOLS:
            try:
                is_trending = True
                trend_data = {
                    'symbol': symbol,
                    'timeframes': {}
                }
                
                # Verifica cada timeframe
                for timeframe in self.timeframes:
                    analysis = await self.crypto_service.get_technical_analysis(symbol, timeframe)
                    price = await self.crypto_service.get_price(symbol)
                    
                    # Verifica se o preço está acima das EMAs e RSI > 50
                    if not self._is_uptrend(analysis):
                        is_trending = False
                        break
                    
                    trend_data['timeframes'][timeframe] = {
                        'rsi': analysis.rsi,
                        'ema_status': analysis.ema_trend
                    }
                
                if is_trending:
                    trend_data['price'] = price.price
                    trending_coins.append(trend_data)
                    
            except Exception as e:
                self.logger.warning(f"Erro ao analisar {symbol}: {str(e)}")
                continue
        
        return trending_coins
    
    def _is_uptrend(self, analysis) -> bool:
        """Verifica se está em tendência de alta."""
        # Verifica se o RSI está acima de 50
        is_strong_momentum = analysis.rsi >= self.rsi_threshold
        
        # Verifica se o preço está acima das EMAs
        is_above_emas = analysis.ema_trend == 'UP'
        
        return is_strong_momentum and is_above_emas
    
    def _format_trends_message(self, trending_coins: List[Dict[str, any]]) -> str:
        """Formata a mensagem de moedas em tendência de alta."""
        message = "🚀 <b>Moedas em Tendência de Alta</b>\n\n"
        
        for coin in trending_coins:
            message += f"💰 {coin['symbol']}: ${coin['price']:,.2f}\n"
            
            for timeframe, data in coin['timeframes'].items():
                message += f"📊 {timeframe} - RSI: {data['rsi']:.2f} | EMAs: {data['ema_status']}\n"
            
            message += "\n"
        
        message += "\n⚠️ <i>Esta é uma análise técnica automatizada. Faça sua própria análise antes de investir.</i>"
        return message