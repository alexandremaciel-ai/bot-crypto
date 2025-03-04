"""
Módulo de configuração para o Crypto Agent.
Carrega variáveis de ambiente e fornece configurações para os diferentes serviços.
"""

import os
import logging
from typing import List, Optional
from dotenv import load_dotenv
import pytz

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Modo de desenvolvimento
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "").lower() == "true"

# Configurações do Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
TELEGRAM_ADMIN_USER_ID = int(os.getenv("TELEGRAM_ADMIN_USER_ID", "0"))

# Usuários autorizados
AUTHORIZED_USERS = [
    int(user_id.strip())
    for user_id in os.getenv("AUTHORIZED_USERS", "").split(",")
    if user_id.strip()
]

# Adiciona o TELEGRAM_CHAT_ID à lista de usuários autorizados, se configurado
if TELEGRAM_CHAT_ID != 0 and TELEGRAM_CHAT_ID not in AUTHORIZED_USERS:
    AUTHORIZED_USERS.append(TELEGRAM_CHAT_ID)

# Configurações de APIs de Criptomoedas
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

# Configurações de Monitoramento
DEFAULT_TIMEZONE = pytz.timezone(os.getenv("DEFAULT_TIMEZONE", "America/Sao_Paulo"))
UPDATE_INTERVAL_MINUTES = int(os.getenv("UPDATE_INTERVAL_MINUTES", "5"))
ALERT_THRESHOLD_PERCENT = float(os.getenv("ALERT_THRESHOLD_PERCENT", "5.0"))

# Configurações de Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Símbolos de criptomoedas padrão para monitoramento
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]

# Lista de criptomoedas monitoradas
MONITORED_CRYPTOS = os.getenv("MONITORED_CRYPTOS", "").split(",") if os.getenv("MONITORED_CRYPTOS") else DEFAULT_SYMBOLS

# Limiar para notificação de mudança de preço (em porcentagem)
PRICE_CHANGE_THRESHOLD_PERCENT = float(os.getenv("PRICE_CHANGE_THRESHOLD_PERCENT", "3.0"))

# Intervalos de tempo para análise técnica
TIMEFRAMES = ["1h", "4h", "1d"]

# Configurações de indicadores técnicos
TECHNICAL_INDICATORS = {
    "ema": {
        "short_period": 9,
        "medium_period": 21,
        "long_period": 50,
    },
    "rsi": {
        "period": 14,
        "overbought": 70,
        "oversold": 30,
    },
    "volume": {
        "period": 20,
    },
    "ichimoku": {
        "conversion_line_period": 9,
        "base_line_period": 26,
        "lagging_span_period": 52,
    },
    "vmc_cipher": {
        "wt_channel_length": 9,
        "wt_average_length": 12,
        "wt_ma_length": 3,
        "ob_level": 53,
        "os_level": -53,
        "ob_level2": 60,
        "os_level2": -60,
        "wt_div_ob_level": 45,
        "wt_div_os_level": -65,
        "rsi_length": 14,
        "rsi_overbought": 60,
        "rsi_oversold": 30,
        "timeframe": "4h",  # Timeframe recomendado para o VMC Cipher
    },
}

def get_log_level() -> int:
    """Retorna o nível de log configurado."""
    return LOG_LEVEL_MAP.get(LOG_LEVEL.upper(), logging.INFO)

def is_user_authorized(user_id: int) -> bool:
    """Verifica se um usuário está autorizado a usar o bot."""
    # Em modo de desenvolvimento, todos os usuários são autorizados
    if DEVELOPMENT_MODE:
        return True
    # Se não houver usuários autorizados configurados, todos são autorizados
    if not AUTHORIZED_USERS:
        return True
    # Caso contrário, verifica se o usuário está na lista
    return user_id in AUTHORIZED_USERS

def validate_config() -> List[str]:
    """
    Valida a configuração e retorna uma lista de erros, se houver.
    
    Returns:
        List[str]: Lista de mensagens de erro. Lista vazia se não houver erros.
    """
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        if not DEVELOPMENT_MODE:
            errors.append("TELEGRAM_BOT_TOKEN não está configurado")
        else:
            logging.warning("TELEGRAM_BOT_TOKEN não está configurado. Algumas funcionalidades podem não funcionar corretamente.")
    
    if not WEBHOOK_URL and not DEVELOPMENT_MODE:
        errors.append("WEBHOOK_URL não está configurado para modo de produção")
    
    if TELEGRAM_CHAT_ID == 0:
        logging.warning("TELEGRAM_CHAT_ID não está configurado. Mensagens para o chat padrão não serão enviadas.")
    
    return errors