"""
Módulo de configuração de logging para o Crypto Agent.
Fornece funções para configurar e obter loggers para diferentes partes da aplicação.
"""

import logging
import sys
from datetime import datetime
import os
from typing import Optional

# Importa a configuração do nível de log
from config import get_log_level

# Diretório para armazenar logs
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Formato do log
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configuração global de logging
def setup_logging() -> None:
    """
    Configura o sistema de logging global.
    
    Configura handlers para console e arquivo, com rotação diária de arquivos.
    Tanto o console quanto o arquivo de log registram apenas erros e níveis superiores.
    """
    # Configuração do logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.ERROR)  # Configura para registrar apenas ERROR e CRITICAL
    
    # Limpa handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Formatador para os logs
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # Handler para console - mostra apenas ERROR e CRITICAL
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Handler para arquivo - mostra apenas ERROR e CRITICAL
    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"crypto_agent_{datetime.now().strftime('%Y-%m-%d')}.log")
    )
    file_handler.setLevel(logging.ERROR)  # Apenas erros e críticos
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Reduzir verbosidade de bibliotecas de terceiros
    logging.getLogger("telegram").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    
    # Log inicial
    logging.error("Sistema de logging inicializado (console: ERROR, arquivo: ERROR)")

def get_logger(name: str) -> logging.Logger:
    """
    Obtém um logger configurado para um módulo específico.
    
    Args:
        name: Nome do módulo/componente para o logger.
        
    Returns:
        logging.Logger: Logger configurado.
    """
    return logging.getLogger(name)

# Função para log de exceções
def log_exception(logger: logging.Logger, e: Exception, context: Optional[str] = None) -> None:
    """
    Registra uma exceção com contexto adicional.
    
    Args:
        logger: Logger a ser usado.
        e: Exceção a ser registrada.
        context: Contexto adicional para o log.
    """
    message = f"Exceção: {type(e).__name__}: {str(e)}"
    if context:
        message = f"{context} - {message}"
    logger.exception(message)

# Função para log de erros de API
def log_api_error(logger: logging.Logger, service: str, endpoint: str, error: str) -> None:
    """
    Registra um erro de API.
    
    Args:
        logger: Logger a ser usado.
        service: Nome do serviço de API.
        endpoint: Endpoint da API.
        error: Mensagem de erro.
    """
    logger.error(f"Erro na API {service} (endpoint: {endpoint}): {error}")

# Função para log de ações do usuário
def log_user_action(logger: logging.Logger, user_id: int, action: str) -> None:
    """
    Registra uma ação do usuário.
    
    Args:
        logger: Logger a ser usado.
        user_id: ID do usuário do Telegram.
        action: Descrição da ação.
    """
    logger.info(f"Usuário {user_id}: {action}") 