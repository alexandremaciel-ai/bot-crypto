"""
Ponto de entrada principal para o Crypto Agent.
"""

import asyncio
import os
import signal
import sys
from typing import Dict, List, Optional

from config import (
    TELEGRAM_BOT_TOKEN, WEBHOOK_URL, UPDATE_INTERVAL_MINUTES,
    TIMEFRAMES, validate_config, DEVELOPMENT_MODE, TELEGRAM_CHAT_ID,
    TECHNICAL_INDICATORS, is_user_authorized
)
from services.telegram_service import TelegramService, alerts, user_manager
from services.crypto_service import CryptoService
from services.scheduler_service import (
    SchedulerService, AlertChecker, PriceUpdater
)
from services.buy_opportunity_service import BuyOpportunityChecker
from services.trend_analysis_service import TrendAnalysisChecker
from services.rsi_oversold_service import RSIOversoldChecker
from services.vmc_cipher_service import VMCCipherService
from services.short_term_uptrend_service import ShortTermUptrendChecker
from utils.logger import setup_logging, get_logger
from utils.lock import BotLock

# Configuração do logger
setup_logging()
logger = get_logger(__name__)


class CryptoAgent:
    """Classe principal que integra todos os serviços."""
    
    def __init__(self):
        """Inicializa o Crypto Agent."""
        self.logger = get_logger(__name__)
        
        self.logger.info("Inicializando Crypto Agent")
        
        self.scheduler_service = SchedulerService()
        self.telegram_service = TelegramService(token=TELEGRAM_BOT_TOKEN, scheduler_service=self.scheduler_service)
        self.crypto_service: Optional[CryptoService] = None
        self.alert_checker: Optional[AlertChecker] = None
        self.price_updater: Optional[PriceUpdater] = None
        self.buy_opportunity_checker: Optional[BuyOpportunityChecker] = None
        self.trend_analysis_checker: Optional[TrendAnalysisChecker] = None
        self.rsi_oversold_checker: Optional[RSIOversoldChecker] = None
        self.vmc_cipher_service: Optional[VMCCipherService] = None
        self.short_term_uptrend_checker: Optional[ShortTermUptrendChecker] = None
        self.running = False
        self.lock = BotLock()
        
        # Inicializa o dicionário de últimos preços
        self.last_prices = {}
    
    async def setup(self) -> None:
        """Configura os serviços e inicializa o agente."""
        try:
            # O serviço de Telegram já foi inicializado no construtor
            await self.telegram_service.setup()
            
            # Inicializa o serviço de criptomoedas com gerenciador de contexto
            self.crypto_service = CryptoService()
            await self.crypto_service.__aenter__()
            
            # Atualiza o crypto_service no TelegramService
            self.telegram_service.crypto_service = self.crypto_service
            
            # Inicializa o serviço de análise de tendência
            self.analysis_service = TrendAnalysisChecker(self.crypto_service, self.telegram_service)
            
            # Inicializa o serviço de agendamento
            self.scheduler_service = SchedulerService()
            
            # Inicializa o serviço VMC Cipher
            self.vmc_cipher_service = VMCCipherService(self.crypto_service, self.telegram_service)
            
            # Inicializa o serviço de tendência de alta de curto prazo
            self.short_term_uptrend_checker = ShortTermUptrendChecker(self.crypto_service, self.telegram_service)
            
            # Adiciona o handler para o comando /vmc
            self.telegram_service.add_command_handler("vmc", self.handle_vmc)
            
            # Adiciona o handler para o comando /moedas
            self.telegram_service.add_command_handler("moedas", self.handle_coins)
            
            # Configura os agendamentos
            self._setup_schedules()
            
            self.logger.info("Configuração concluída com sucesso")
        except Exception as e:
            self.logger.error(f"Erro durante a configuração do agente: {str(e)}")
            raise
    
    def _setup_schedules(self) -> None:
        """Configura os agendamentos de tarefas."""
        self.logger.info("Configurando agendamentos...")
        
        # Agendamento para atualização de preços
        self.scheduler_service.add_job(
            self._update_prices,
            interval_minutes=UPDATE_INTERVAL_MINUTES,
            job_id="update_prices"
        )
        
        # Agendamento para verificação de oportunidades VMC Cipher
        if self.vmc_cipher_service:
            check_interval = TECHNICAL_INDICATORS.get('vmc_cipher', {}).get('check_interval_minutes', 60)
            self.scheduler_service.add_job(
                self.vmc_cipher_service.check_opportunities,
                interval_minutes=check_interval,
                job_id="check_vmc_opportunities"
            )
        
        # Agendamento para verificação de tendência de alta de curto prazo
        if self.short_term_uptrend_checker:
            self.scheduler_service.add_job(
                self.short_term_uptrend_checker.check_uptrend,
                interval_minutes=10,  # Executa a cada 10 minutos
                job_id="check_short_term_uptrend"
            )
        
        self.logger.info("Agendamentos configurados com sucesso")
    
    async def _update_prices(self) -> None:
        """Atualiza os preços das criptomoedas e notifica sobre mudanças significativas."""
        try:
            self.logger.info("Atualizando preços das criptomoedas...")
            
            # Obtém a lista de criptomoedas monitoradas
            from config import MONITORED_CRYPTOS
            
            for symbol in MONITORED_CRYPTOS:
                # Obtém o preço atual
                crypto_price = await self.crypto_service.get_price(symbol)
                current_price = crypto_price.price
                
                # Verifica se houve mudança significativa no preço
                if self._is_significant_price_change(symbol, current_price):
                    # Notifica os usuários sobre a mudança de preço
                    message = f"⚠️ Mudança significativa no preço de {symbol}: ${current_price:.2f}"
                    await self.telegram_service.send_message_to_all_users(message)
                
                # Atualiza o preço armazenado
                self._update_stored_price(symbol, current_price)
            
            self.logger.info("Preços atualizados com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao atualizar preços: {str(e)}")
    
    def _is_significant_price_change(self, symbol: str, current_price: float) -> bool:
        """
        Verifica se houve uma mudança significativa no preço.
        
        Args:
            symbol: Símbolo da criptomoeda
            current_price: Preço atual
            
        Returns:
            True se a mudança for significativa, False caso contrário
        """
        # Obtém o último preço armazenado
        last_price = self.last_prices.get(symbol)
        
        # Se não houver preço anterior, não é uma mudança significativa
        if last_price is None:
            return False
        
        # Calcula a variação percentual
        from config import PRICE_CHANGE_THRESHOLD_PERCENT
        percent_change = abs((current_price - last_price) / last_price * 100)
        
        # Verifica se a variação é significativa
        return percent_change >= PRICE_CHANGE_THRESHOLD_PERCENT
    
    def _update_stored_price(self, symbol: str, price: float) -> None:
        """
        Atualiza o preço armazenado para uma criptomoeda.
        
        Args:
            symbol: Símbolo da criptomoeda
            price: Preço atual
        """
        # Atualiza o preço
        self.last_prices[symbol] = price
    
    async def start(self) -> None:
        """Inicia o Crypto Agent."""
        if self.running:
            logger.warning("Crypto Agent já está em execução")
            return
        
        # Verifica se já existe uma instância do bot em execução
        if not self.lock.acquire():
            logger.error("Outra instância do Crypto Agent já está em execução. Encerrando...")
            return
        
        # Valida a configuração
        errors = validate_config()
        if errors:
            for error in errors:
                logger.error(f"Erro de configuração: {error}")
            logger.error("Corrigindo os erros de configuração antes de iniciar")
            self.lock.release()  # Libera o lock se houver erros de configuração
            return
        
        logger.info("Iniciando Crypto Agent")
        
        # Configura os serviços
        await self.setup()
        
        # Inicia o agendador
        self.scheduler_service.start()
        
        # Inicia o bot do Telegram
        # Em modo de desenvolvimento ou se não houver URL de webhook configurada, usa polling
        if DEVELOPMENT_MODE or not WEBHOOK_URL:
            await self.telegram_service.start_polling()
        else:
            # Em produção, usa webhook
            await self.telegram_service.start_webhook()
        
        self.running = True
        logger.info("Crypto Agent iniciado com sucesso")
        
        # Envia mensagem para o chat padrão informando que o bot foi iniciado
        await self.telegram_service.send_to_default_chat(
            "🤖 <b>Crypto Agent iniciado com sucesso!</b>\n\n"
            "O bot está pronto para monitorar criptomoedas e enviar alertas."
        )
    
    async def stop(self) -> None:
        """Para o Crypto Agent."""
        if not self.running:
            logger.warning("Crypto Agent não está em execução")
            return
        
        logger.info("Parando Crypto Agent")
        
        # Envia mensagem para o chat padrão informando que o bot será parado
        try:
            await self.telegram_service.send_to_default_chat(
                "🔴 <b>Crypto Agent está sendo desligado...</b>\n\n"
                "O monitoramento de criptomoedas será interrompido temporariamente."
            )
        except Exception as e:
            logger.warning(f"Não foi possível enviar mensagem de desligamento: {str(e)}")
        
        # Para o bot do Telegram
        await self.telegram_service.stop()
        
        # Para o agendador
        self.scheduler_service.stop()
        
        # Fecha o serviço de criptomoedas
        if self.crypto_service:
            await self.crypto_service.__aexit__(None, None, None)
        
        self.running = False
        
        # Libera o lock ao parar o bot
        self.lock.release()
        
        logger.info("Crypto Agent parado com sucesso")

    async def handle_analysis_pt(self, update, context):
        """Manipula o comando /analise."""
        await self.handle_analysis(update, context)
        
    async def handle_vmc(self, update, context):
        """Manipula o comando /vmc para análise do VMC Cipher."""
        try:
            # Verifica se o usuário está autorizado
            user_id = update.effective_user.id
            if not is_user_authorized(user_id):
                await update.message.reply_text("Você não está autorizado a usar este comando.")
                return
            
            # Verifica se o símbolo foi fornecido
            if not context.args or len(context.args) < 1:
                await update.message.reply_text(
                    "Por favor, forneça um símbolo. Exemplo: /vmc BTC"
                )
                return
            
            # Obtém o símbolo e o timeframe (opcional)
            symbol = context.args[0].upper()
            # Adiciona USDT se não estiver presente
            if not symbol.endswith("USDT"):
                symbol = f"{symbol}USDT"
                
            timeframe = context.args[1] if len(context.args) > 1 else TECHNICAL_INDICATORS['vmc_cipher']['timeframe']
            
            # Envia mensagem de processamento
            await update.message.reply_text(f"Analisando {symbol} com VMC Cipher no timeframe {timeframe}...")
            
            # Realiza a análise
            result = await self.vmc_cipher_service.analyze_symbol(symbol, timeframe)
            
            # Prepara a mensagem de resposta
            message = f"📊 *Análise VMC Cipher para {symbol} ({timeframe})*\n\n"
            
            if result.has_green_circle:
                message += "🟢 *Círculo Verde* detectado - Possível oportunidade de compra!\n"
            
            if result.has_gold_circle:
                message += "🟡 *Círculo Dourado* detectado - Possível oportunidade de compra (confirmação adicional)!\n"
            
            if result.has_red_circle:
                message += "🔴 *Círculo Vermelho* detectado - Possível oportunidade de venda!\n"
            
            if result.has_purple_triangle:
                message += "🟣 *Triângulo Roxo* detectado - Alerta de divergência!\n"
            
            if not any([result.has_green_circle, result.has_gold_circle, result.has_red_circle, result.has_purple_triangle]):
                message += "⚪ Nenhum sinal significativo detectado no momento.\n"
            
            # Envia a resposta
            await update.message.reply_text(message, parse_mode='Markdown')
            
            # Gera e envia o gráfico
            chart_path = await self.vmc_cipher_service.generate_vmc_chart(symbol, timeframe)
            if chart_path:
                await update.message.reply_photo(open(chart_path, 'rb'), caption=f"Gráfico VMC Cipher para {symbol} ({timeframe})")
                # Remove o arquivo após enviar
                os.remove(chart_path)
            
        except Exception as e:
            self.logger.error(f"Erro ao processar comando /vmc: {str(e)}")
            await update.message.reply_text(f"Ocorreu um erro ao analisar: {str(e)}")

    async def handle_help(self, update, context):
        """Processa o comando /ajuda."""
        help_text = (
            "🤖 <b>Comandos disponíveis:</b>\n\n"
            "/preco <símbolo> - Consulta o preço atual de uma criptomoeda\n"
            "/variacao <símbolo> - Consulta a variação de preço nas últimas 24h\n"
            "/analise <símbolo> - Realiza análise técnica de uma criptomoeda\n"
            "/compras - Lista oportunidades de compra\n"
            "/vmc <símbolo> - Análise VMC Cipher\n"
            "/moedas - Lista as criptomoedas disponíveis\n"
            "/ajuda - Exibe esta mensagem de ajuda"
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text,
            parse_mode="HTML"
        )
    
    async def handle_coins(self, update, context):
        """Processa o comando /moedas."""
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔍 Buscando criptomoedas disponíveis...",
                parse_mode="HTML"
            )
            
            # Obtém a lista de símbolos disponíveis
            symbols = await self.crypto_service.get_available_symbols()
            
            # Limita a quantidade de símbolos para exibição
            max_symbols = 50
            symbols = symbols[:max_symbols]
            
            # Formata a mensagem
            message = f"🪙 <b>Criptomoedas Disponíveis ({len(symbols)} de {max_symbols}):</b>\n\n"
            
            # Organiza em colunas
            columns = 5
            rows = (len(symbols) + columns - 1) // columns
            
            for i in range(rows):
                for j in range(columns):
                    idx = i + j * rows
                    if idx < len(symbols):
                        message += f"{symbols[idx]}"
                        # Adiciona espaço ou quebra de linha
                        if j < columns - 1:
                            message += " | "
                        else:
                            message += "\n"
            
            message += "\n<i>Use /preco SÍMBOLO para consultar o preço.</i>"
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            self.logger.error(f"Erro ao listar criptomoedas: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Erro ao listar criptomoedas: {str(e)}",
                parse_mode="HTML"
            )


async def main() -> None:
    """Função principal."""
    # Cria e inicia o Crypto Agent
    agent = CryptoAgent()
    
    # Configura handlers para sinais de término
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(agent.stop()))
    
    try:
        await agent.start()
        
        # Mantém o programa em execução
        while agent.running:
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.exception(f"Erro fatal: {str(e)}")
    
    finally:
        # Garante que o agente seja parado corretamente
        if agent.running:
            await agent.stop()


if __name__ == "__main__":
    try:
        if DEVELOPMENT_MODE:
            logger.info("Iniciando em modo de desenvolvimento")
        
        # Executa o loop principal
        asyncio.run(main())
    
    except KeyboardInterrupt:
        logger.info("Programa interrompido pelo usuário")
    
    except Exception as e:
        logger.exception(f"Erro não tratado: {str(e)}")
        sys.exit(1)
    
    sys.exit(0)