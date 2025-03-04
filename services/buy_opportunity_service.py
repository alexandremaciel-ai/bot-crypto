"""Serviço para verificação de oportunidades de compra."""

from typing import Dict, List, Optional
from config import DEFAULT_SYMBOLS, TECHNICAL_INDICATORS
from utils.logger import get_logger, log_exception

class BuyOpportunityChecker:
    """Classe para verificação de oportunidades de compra de criptomoedas."""
    
    def __init__(self, crypto_service, telegram_service):
        """
        Inicializa o verificador de oportunidades.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        self.logger = get_logger(__name__)
    
    async def check_opportunities(self) -> None:
        """Verifica oportunidades de compra e envia notificações."""
        try:
            opportunities = await self._analyze_market()
            
            if opportunities:
                # Formata e envia a mensagem para o Telegram
                message = self._format_opportunities_message(opportunities)
                await self.telegram_service.send_to_default_chat(message)
                self.logger.info(f"Encontradas {len(opportunities)} oportunidades de compra")
            else:
                self.logger.info("Nenhuma oportunidade de compra encontrada")
                
        except Exception as e:
            log_exception(self.logger, e, "Erro ao verificar oportunidades de compra")
    
    async def _analyze_market(self) -> List[Dict[str, float]]:
        """Analisa o mercado em busca de oportunidades."""
        opportunities = []
        
        for symbol in DEFAULT_SYMBOLS:
            try:
                # Obtém análise técnica com timeframes padrão
                analysis = await self.crypto_service.get_technical_analysis(symbol, ['1h', '4h', '1d'])
                price = await self.crypto_service.get_price(symbol)
                price_change = await self.crypto_service.get_price_change(symbol)
                
                # Verifica condições de compra
                if self._is_buy_opportunity(analysis):
                    opportunities.append({
                        'symbol': symbol,
                        'price': price.price,
                        'change_24h': price_change.percent_change,
                        'rsi': analysis.rsi['4h'].value,
                        'ema_status': analysis.ema['4h'].trend
                    })
                    
            except Exception as e:
                self.logger.warning(f"Erro ao analisar {symbol}: {str(e)}")
                continue
        
        return opportunities
    
    def _is_buy_opportunity(self, analysis) -> bool:
        """Verifica se há uma oportunidade de compra baseada na análise técnica."""
        # Configurações dos indicadores
        rsi_config = TECHNICAL_INDICATORS['rsi']
        
        # Verifica RSI em condição de sobrevenda usando o RSI do timeframe de 4h
        is_oversold = analysis.rsi['4h'].value <= rsi_config['oversold']
        
        # Verifica tendência das EMAs
        is_uptrend = analysis.ema['4h'].trend == 'Alta'
        
        # Verifica se há dados de Ichimoku Cloud
        # Como não vemos Ichimoku no modelo, vamos remover essa verificação
        # e usar apenas RSI e EMA para determinar oportunidades
        
        # Uma oportunidade de compra é identificada quando:
        # 1. RSI está em sobrevenda (≤ 30)
        # 2. EMAs indicam tendência de alta
        return is_oversold and is_uptrend
    
    def _format_opportunities_message(self, opportunities: List[Dict[str, float]]) -> str:
        """Formata a mensagem de oportunidades de compra."""
        message = "🚨 <b>Oportunidades de Compra Detectadas!</b>\n\n"
        
        for opp in opportunities:
            message += f"💰 {opp['symbol']}: ${opp['price']:,.2f}\n"
            message += f"📊 Variação 24h: {opp['change_24h']}%\n"
            message += f"📈 RSI: {opp['rsi']:.2f}\n"
            message += f"🔄 Tendência EMA: {opp['ema_status']}\n\n"
        
        message += "\n⚠️ <i>Esta não é uma recomendação de investimento. Faça sua própria análise antes de investir.</i>"
        return message