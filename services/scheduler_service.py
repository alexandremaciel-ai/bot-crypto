"""
Serviço para agendamento de tarefas periódicas.
"""

import asyncio
import time
import schedule
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Coroutine
import threading
import nest_asyncio

from config import DEFAULT_TIMEZONE, UPDATE_INTERVAL_MINUTES
from utils.logger import get_logger, log_exception

# Configuração do logger
logger = get_logger(__name__)

# Aplicar o patch do nest_asyncio para permitir loops aninhados
nest_asyncio.apply()


class SchedulerService:
    """Serviço para agendamento de tarefas periódicas."""
    
    def __init__(self):
        """Inicializa o serviço de agendamento."""
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.loop = asyncio.get_event_loop()
        self.tasks: Dict[str, Callable[[], Any]] = {}
        self.async_tasks: Dict[str, Callable[[], Coroutine[Any, Any, Any]]] = {}
    
    def add_task(self, name: str, task: Callable[[], Any], interval_minutes: int) -> None:
        """
        Adiciona uma tarefa síncrona ao agendador.
        
        Args:
            name: Nome da tarefa.
            task: Função a ser executada.
            interval_minutes: Intervalo em minutos.
        """
        self.tasks[name] = task
        
        # Agenda a tarefa
        schedule.every(interval_minutes).minutes.do(self._run_task, name=name)
        logger.info(f"Tarefa '{name}' agendada para execução a cada {interval_minutes} minutos")
    
    def add_async_task(self, name: str, task: Callable[[], Coroutine[Any, Any, Any]], interval_minutes: int) -> None:
        """
        Adiciona uma tarefa assíncrona ao agendador.
        
        Args:
            name: Nome da tarefa.
            task: Coroutine a ser executada.
            interval_minutes: Intervalo em minutos.
        """
        self.async_tasks[name] = task
        
        # Agenda a tarefa
        schedule.every(interval_minutes).minutes.do(self._run_async_task, name=name)
        logger.info(f"Tarefa assíncrona '{name}' agendada para execução a cada {interval_minutes} minutos")
    
    def _run_task(self, name: str) -> None:
        """
        Executa uma tarefa síncrona.
        
        Args:
            name: Nome da tarefa.
        """
        if name not in self.tasks:
            logger.warning(f"Tarefa '{name}' não encontrada")
            return
        
        try:
            logger.info(f"Executando tarefa '{name}'")
            start_time = time.time()
            self.tasks[name]()
            elapsed = time.time() - start_time
            logger.info(f"Tarefa '{name}' concluída em {elapsed:.2f} segundos")
        except Exception as e:
            log_exception(logger, e, f"Erro ao executar tarefa '{name}'")
    
    def _run_async_task(self, name: str) -> None:
        """
        Executa uma tarefa assíncrona.
        
        Args:
            name: Nome da tarefa.
        """
        if name not in self.async_tasks:
            logger.warning(f"Tarefa assíncrona '{name}' não encontrada")
            return
        
        try:
            logger.info(f"Executando tarefa assíncrona '{name}'")
            start_time = time.time()
            
            # Executa a tarefa assíncrona no loop de eventos
            future = asyncio.run_coroutine_threadsafe(self.async_tasks[name](), self.loop)
            future.result()  # Aguarda a conclusão
            
            elapsed = time.time() - start_time
            logger.info(f"Tarefa assíncrona '{name}' concluída em {elapsed:.2f} segundos")
        except Exception as e:
            log_exception(logger, e, f"Erro ao executar tarefa assíncrona '{name}'")
    
    def _run_scheduler(self) -> None:
        """Executa o agendador em um loop."""
        logger.info("Iniciando loop do agendador")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                log_exception(logger, e, "Erro no loop do agendador")
                time.sleep(5)  # Espera um pouco antes de tentar novamente
    
    def start(self) -> None:
        """Inicia o serviço de agendamento."""
        if self.running:
            logger.warning("Serviço de agendamento já está em execução")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Serviço de agendamento iniciado")
    
    def stop(self) -> None:
        """Para o serviço de agendamento."""
        if not self.running:
            logger.warning("Serviço de agendamento não está em execução")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        # Limpa todas as tarefas agendadas
        schedule.clear()
        
        logger.info("Serviço de agendamento parado")
    
    def add_job(self, job_func, interval_minutes: int, job_id: str) -> None:
        """
        Adiciona um trabalho ao agendador.
        
        Args:
            job_func: Função ou coroutine a ser executada.
            interval_minutes: Intervalo em minutos.
            job_id: Identificador único do trabalho.
        """
        if asyncio.iscoroutinefunction(job_func):
            self.add_async_task(job_id, job_func, interval_minutes)
        else:
            self.add_task(job_id, job_func, interval_minutes)

    def get_scheduled_tasks(self):
        """Returns a list of all scheduled tasks with their details.
        
        Returns:
            List of task objects containing name, next run time, and interval.
        """
        tasks = []
        for job in schedule.get_jobs():
            # Extract task name from job function arguments
            # The name is passed as a keyword argument to _run_task or _run_async_task
            task_name = 'Unknown'
            if hasattr(job.job_func, 'keywords') and 'name' in job.job_func.keywords:
                task_name = job.job_func.keywords['name']
            elif job.job_func.args and len(job.job_func.args) > 0:
                task_name = job.job_func.args[0]
            
            # Create a task object with required information
            task = type('Task', (), {
                'name': task_name,
                'next_run_time': job.next_run,
                'trigger': type('Trigger', (), {'interval': job.interval})
            })
            tasks.append(task)
        return tasks


class AlertChecker:
    """Classe para verificação de alertas de preço."""
    
    def __init__(self, crypto_service, telegram_service, alerts_dict):
        """
        Inicializa o verificador de alertas.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
            alerts_dict: Dicionário de alertas.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        self.alerts_dict = alerts_dict
        self.logger = get_logger(__name__)
    
    async def check_alerts(self) -> None:
        """Verifica todos os alertas configurados."""
        if not self.alerts_dict:
            return
        
        self.logger.info(f"Verificando {sum(len(alerts) for alerts in self.alerts_dict.values())} alertas")
        
        for symbol, alerts in list(self.alerts_dict.items()):
            # Filtra apenas alertas não disparados
            active_alerts = [alert for alert in alerts if not alert.is_triggered]
            
            if not active_alerts:
                continue
            
            try:
                # Obtém o preço atual e a variação
                price_change = await self.crypto_service.get_price_change(symbol)
                
                # Verifica cada alerta
                for alert in active_alerts:
                    triggered = False
                    
                    # Alerta de preço alvo
                    if alert.target_price is not None:
                        if (alert.target_price > 0 and price_change.current_price >= alert.target_price) or \
                           (alert.target_price < 0 and price_change.current_price <= abs(alert.target_price)):
                            triggered = True
                    
                    # Alerta de variação percentual
                    elif alert.percent_change is not None:
                        if (alert.percent_change > 0 and price_change.percent_change >= alert.percent_change) or \
                           (alert.percent_change < 0 and price_change.percent_change <= alert.percent_change):
                            triggered = True
                    
                    # Se o alerta foi disparado
                    if triggered:
                        alert.trigger(price_change.current_price)
                        await self.telegram_service.send_alert_notification(alert, price_change.current_price)
                        self.logger.info(f"Alerta disparado: {symbol} ({alert.alert_type})")
                
                # Atualiza a lista de alertas, removendo os disparados
                self.alerts_dict[symbol] = [alert for alert in alerts if not alert.is_triggered]
                
                # Remove o símbolo se não houver mais alertas
                if not self.alerts_dict[symbol]:
                    del self.alerts_dict[symbol]
            
            except Exception as e:
                log_exception(self.logger, e, f"Erro ao verificar alertas para {symbol}")


class PriceUpdater:
    """Classe para atualização de preços para usuários."""
    
    def __init__(self, crypto_service, telegram_service, user_manager):
        """
        Inicializa o atualizador de preços.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
            user_manager: Gerenciador de usuários.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        self.user_manager = user_manager
        self.logger = get_logger(__name__)
    
    async def update_prices(self) -> None:
        """Atualiza os preços para todos os usuários ativos."""
        # Obtém usuários ativos
        active_users = self.user_manager.get_active_users()
        
        if not active_users:
            return
        
        self.logger.info(f"Atualizando preços para {len(active_users)} usuários ativos")
        
        for user in active_users:
            # Pula usuários que não desejam atualizações
            if not user.preferences.alert_notifications:
                continue
            
            # Obtém a watchlist do usuário
            watchlist = user.preferences.watchlist
            
            if not watchlist:
                continue
            
            try:
                # Obtém os preços de todas as criptomoedas na watchlist
                prices = await self.crypto_service.get_prices(list(watchlist))
                
                # Envia atualizações para o usuário
                for symbol, price in prices.items():
                    await self.telegram_service.send_price_update(user.user_id, price)
                    
                    # Pequeno delay para evitar flood
                    await asyncio.sleep(0.1)
            
            except Exception as e:
                log_exception(self.logger, e, f"Erro ao atualizar preços para o usuário {user.user_id}")