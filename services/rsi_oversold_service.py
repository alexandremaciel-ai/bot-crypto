"""Serviço para detecção de RSI em condição de sobrevenda extrema."""

from typing import Dict, List, Optional
from config import DEFAULT_SYMBOLS
from utils.logger import get_logger, log_exception

class RSIOversoldChecker:
    """Classe para verificação de criptomoedas em condição de sobrevenda extrema pelo RSI."""
    
    def __init__(self, crypto_service, telegram_service):
        """
        Inicializa o verificador de RSI em sobrevenda.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        self.logger = get_logger(__name__)
        self.rsi_threshold = 22
        self.timeframe = '4h'
    
    async def check_oversold(self) -> None:
        """Verifica criptomoedas em sobrevenda extrema e envia notificações."""
        try:
            oversold_coins = await self._analyze_market()
            
            if oversold_coins:
                # Formata e envia a mensagem para o Telegram
                message = self._format_oversold_message(oversold_coins)
                await self.telegram_service.send_to_default_chat(message)
                self.logger.info(f"Encontradas {len(oversold_coins)} moedas em sobrevenda extrema")
            else:
                self.logger.info("Nenhuma moeda em sobrevenda extrema encontrada")
                
        except Exception as e:
            log_exception(self.logger, e, "Erro ao verificar moedas em sobrevenda")
    
    async def _analyze_market(self) -> List[Dict[str, float]]:
        """Analisa o mercado em busca de moedas em sobrevenda extrema."""
        oversold_coins = []
        
        for symbol in DEFAULT_SYMBOLS:
            try:
                # Obtém análise técnica no timeframe de 4 horas
                analysis = await self.crypto_service.get_technical_analysis(symbol, self.timeframe)
                price = await self.crypto_service.get_price(symbol)
                price_change = await self.crypto_service.get_price_change(symbol)
                
                # Verifica se o RSI está abaixo ou igual a 22
                if analysis.rsi <= self.rsi_threshold:
                    oversold_coins.append({
                        'symbol': symbol,
                        'price': price.price,
                        'change_24h': price_change.change_24h,
                        'rsi': analysis.rsi,
                        'timeframe': self.timeframe
                    })
                    
            except Exception as e:
                self.logger.warning(f"Erro ao analisar {symbol}: {str(e)}")
                continue
        
        return oversold_coins
    
    def _format_oversold_message(self, oversold_coins: List[Dict[str, float]]) -> str:
        """Formata a mensagem de moedas em sobrevenda extrema."""
        message = "🎯 <b>Oportunidade: Moedas com RSI em Sobrevenda Extrema!</b>\n\n"
        message += f"📊 Timeframe: {self.timeframe}\n\n"
        
        for coin in oversold_coins:
            message += f"💰 {coin['symbol']}: ${coin['price']:,.2f}\n"
            message += f"📉 RSI: {coin['rsi']:.2f}\n"
            message += f"📊 Variação 24h: {coin['change_24h']}%\n\n"
        
        message += "\n⚠️ <i>RSI abaixo de 22 indica condição de sobrevenda extrema. "
        message += "Esta não é uma recomendação de investimento. Faça sua própria análise antes de investir.</i>"
        return message