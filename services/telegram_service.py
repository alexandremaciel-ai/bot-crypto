"""Serviço de integração com o Telegram."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from models.user import User, UserManager
from models.crypto import CryptoPrice, PriceChange, TechnicalAnalysis
from services.crypto_service import CryptoService
from services.buy_opportunity_service import BuyOpportunityChecker
from utils.formatters import (
    format_price_message,
    format_price_change_message,
    format_technical_analysis_message
)
from utils.logger import get_logger
from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN, AUTHORIZED_USERS
from services.scheduler_service import SchedulerService

logger = get_logger(__name__)

# Gerenciador de usuários
user_manager = UserManager()

# Serviço de criptomoedas
crypto_service = CryptoService()

# Dicionário de alertas de preço por usuário
alerts: Dict[int, Dict[str, float]] = {}

class TelegramService:
    """Serviço para interação com o Telegram."""
    
    def __init__(self, token: str, crypto_service: Optional[CryptoService] = None, 
                 scheduler_service: Optional[SchedulerService] = None):
        """Inicializa o serviço do Telegram.
        
        Args:
            token: Token do bot do Telegram.
            crypto_service: Serviço de criptomoedas.
            scheduler_service: Serviço de agendamento.
        """
        if not scheduler_service:
            raise ValueError("scheduler_service é obrigatório")
            
        self.app = Application.builder().token(token).build()
        self.crypto_service = crypto_service
        self.scheduler_service = scheduler_service
        self.logger = logging.getLogger(__name__)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura os handlers de comandos."""
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CommandHandler("preco", self._price_command))
        self.app.add_handler(CommandHandler("variacao", self._change_command))
        self.app.add_handler(CommandHandler("analise", self._analysis_command))
        self.app.add_handler(CommandHandler("alerta", self._alert_command))
        self.app.add_handler(CommandHandler("compras", self._buy_opportunities_command))
        self.app.add_handler(CommandHandler("agendamentos", self._schedule_command))
        
        # Handler para mensagens não reconhecidas
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
    
    async def _schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista todos os agendamentos ativos"""
        scheduler = self.scheduler_service
        tasks = scheduler.get_scheduled_tasks()
        
        if not tasks:
            await update.message.reply_text("Não há agendamentos ativos.")
            return
        
        message = "📅 Agendamentos ativos:\n\n"
        for task in tasks:
            next_run = task.next_run_time.strftime("%d/%m/%Y %H:%M:%S")
            message += f"• {task.name}\n"
            message += f"  ⏰ Próxima execução: {next_run}\n"
            message += f"  🔄 Intervalo: {task.trigger.interval} segundos\n\n"
        
        await update.message.reply_text(message)
    
    async def setup(self) -> None:
        """Inicializa o serviço do Telegram."""
        self.logger.info("Inicializando serviço do Telegram...")
        await self.app.initialize()
        self.logger.info("Serviço do Telegram inicializado com sucesso.")
    
    async def start(self) -> None:
        """Inicia o bot do Telegram."""
        await self.app.initialize()
        await self.app.start()
        await self.app.run_polling()
    
    async def start_polling(self) -> None:
        """Inicia o bot do Telegram em modo polling."""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
    async def start_webhook(self) -> None:
        """Inicia o bot do Telegram em modo webhook."""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_webhook()
    
    async def stop(self) -> None:
        """Para o bot do Telegram."""
        await self.app.stop()
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa o comando /start."""
        if not update.effective_chat:
            return
            
        user_id = update.effective_chat.id
        username = update.effective_chat.username or "Unknown"
        
        # Registra o usuário
        user = user_manager.get_or_create_user(user_id=user_id, username=username)
        
        welcome_message = (
            f"Olá {username}! 👋\n\n"
            "Bem-vindo ao Crypto Agent! Estou aqui para ajudar você a monitorar criptomoedas.\n\n"
            "Comandos disponíveis:\n"
            "/start - Inicia a interação com o bot\n"
            "/preco [symbol] - Consulta o preço atual\n"
            "/variacao [symbol] - Consulta a variação em 24h\n"
            "/analise [symbol] - Análise técnica completa\n"
            "/alerta [symbol] [percentual] - Define alerta de variação de preço\n"
            "/compras - Lista oportunidades de compra"
        )
        
        await context.bot.send_message(
            chat_id=user_id,
            text=welcome_message,
            parse_mode="HTML"
        )
    
    async def _buy_opportunities_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa o comando /compras."""
        if not update.effective_chat:
            return
            
        # Verifica se o serviço de criptomoedas está disponível
        if not self.crypto_service:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Serviço de criptomoedas não disponível no momento.",
                parse_mode="HTML"
            )
            return
            
        # Informa ao usuário que a análise está em andamento
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏳ Analisando o mercado em busca de oportunidades de compra...",
            parse_mode="HTML"
        )
        
        try:
            # Cria uma instância temporária do verificador de oportunidades
            checker = BuyOpportunityChecker(
                crypto_service=self.crypto_service,
                telegram_service=self
            )
            
            # Realiza a análise do mercado
            opportunities = await checker._analyze_market()
            
            if opportunities:
                # Formata e envia a mensagem com as oportunidades
                message = checker._format_opportunities_message(opportunities)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Nenhuma oportunidade de compra encontrada no momento.\nTente novamente mais tarde.",
                    parse_mode="HTML"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao processar comando /compras: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Erro ao analisar oportunidades de compra: {str(e)}",
                parse_mode="HTML"
            )
    
    async def _price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa o comando /preco."""
        if not update.effective_chat:
            return
            
        if not context.args or len(context.args) != 1:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Por favor, forneça o símbolo da criptomoeda. Exemplo: /preco BTC",
                parse_mode=None
            )
            return
            
        symbol = context.args[0].upper()
        
        try:
            # Remove o sufixo USDT se estiver presente
            base_symbol = symbol.replace("USDT", "") if symbol.endswith("USDT") else symbol
            
            # Tenta obter o preço
            crypto_price = await self.crypto_service.get_price(base_symbol)
            message = format_price_message(crypto_price)
        except Exception as e:
            message = f"❌ Erro ao consultar preço do {symbol}: {str(e)}"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode="HTML"
        )
    
    async def _change_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa o comando /variacao."""
        if not update.effective_chat:
            return
            
        if not context.args or len(context.args) != 1:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Por favor, forneça o símbolo da criptomoeda. Exemplo: /variacao BTC",
                parse_mode=None
            )
            return
            
        symbol = context.args[0].upper()
        
        try:
            price_change = await self.crypto_service.get_price_change(symbol)
            message = format_price_change_message(price_change)
        except Exception as e:
            message = f"❌ Erro ao consultar variação do {symbol}: {str(e)}"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode="HTML"
        )
    
    async def _analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa o comando /analise."""
        if not update.effective_chat:
            return
            
        if not context.args or len(context.args) != 1:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Por favor, forneça o símbolo da criptomoeda. Exemplo: /analise BTC",
                parse_mode=None
            )
            return
            
        # Obtém o símbolo e remove o sufixo USDT se já estiver presente
        symbol = context.args[0].upper()
        symbol = symbol.replace("USDT", "") if symbol.endswith("USDT") else symbol
        
        try:
            # Adicionando os timeframes padrão para a análise
            analysis = await self.crypto_service.get_technical_analysis(symbol, ['1h', '4h', '1d'])
            message = format_technical_analysis_message(analysis)
        except Exception as e:
            message = f"❌ Erro ao realizar análise técnica do {symbol}: {str(e)}"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode="HTML"
        )
    
    async def _alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa o comando /alerta."""
        if not update.effective_chat:
            return
            
        if not context.args or len(context.args) != 2:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Por favor, forneça o símbolo e o percentual. Exemplo: /alerta BTC 5",
                parse_mode=None
            )
            return
            
        symbol = context.args[0].upper()
        try:
            percentage = float(context.args[1])
        except ValueError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ O percentual deve ser um número válido",
                parse_mode="HTML"
            )
            return
        
        user_id = update.effective_chat.id
        if user_id not in alerts:
            alerts[user_id] = {}
        
        alerts[user_id][symbol] = percentage
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Alerta configurado: {symbol} com variação de {percentage}%",
            parse_mode="HTML"
        )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa mensagens de texto que não são comandos."""
        if not update.effective_chat or not update.message or not update.message.text:
            return
            
        user_id = update.effective_chat.id
        message_text = update.message.text
        
        # Resposta simples para mensagens que não são comandos
        await context.bot.send_message(
            chat_id=user_id,
            text="Para interagir com o bot, utilize um dos comandos disponíveis:\n"
                 "/start - Inicia a interação com o bot\n"
                 "/preco [symbol] - Consulta o preço atual\n"
                 "/variacao [symbol] - Consulta a variação em 24h\n"
                 "/analise [symbol] - Análise técnica completa\n"
                 "/alerta [symbol] [percentual] - Define alerta de variação de preço\n"
                 "/compras - Lista oportunidades de compra",
            parse_mode=None
        )
    
    async def send_to_default_chat(self, message: str) -> None:
        """Envia uma mensagem para o chat padrão configurado.

        Args:
            message: Mensagem a ser enviada.
        """
        if not TELEGRAM_CHAT_ID:
            logger.warning("TELEGRAM_CHAT_ID não configurado. Mensagem não enviada.")
            return

        await self.app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="HTML"
        )

    def add_command_handler(self, command: str, handler) -> None:
        """
        Adiciona um manipulador de comando ao bot.
        
        Args:
            command: O comando a ser manipulado (sem a barra)
            handler: A função que irá manipular o comando
        """
        self.logger.info(f"Adicionando manipulador para o comando /{command}")
        self.app.add_handler(CommandHandler(command, handler))
    
    async def send_message_to_all_users(self, message: str) -> None:
        """
        Envia uma mensagem para todos os usuários registrados.
        
        Args:
            message: A mensagem a ser enviada
        """
        try:
            # Obtém a lista de usuários registrados
            for user_id in AUTHORIZED_USERS:
                try:
                    await self.app.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='HTML'
                    )
                    self.logger.debug(f"Mensagem enviada para o usuário {user_id}")
                except Exception as e:
                    self.logger.error(f"Erro ao enviar mensagem para o usuário {user_id}: {str(e)}")
            
            self.logger.info("Mensagem enviada para todos os usuários")
        except Exception as e:
            self.logger.error(f"Erro ao enviar mensagem para todos os usuários: {str(e)}")