"""
Utilitários para validação de entrada de dados.
"""

import re
from typing import Optional, Tuple, List


def validate_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Valida um símbolo de criptomoeda.
    
    Args:
        symbol: Símbolo a ser validado.
        
    Returns:
        Tuple[bool, Optional[str]]: Tupla com flag de validade e mensagem de erro (se houver).
    """
    # Converte para maiúsculas e remove espaços
    symbol = symbol.upper().strip()
    
    # Verifica se o símbolo está vazio
    if not symbol:
        return False, "O símbolo não pode estar vazio."
    
    # Verifica se o símbolo tem um formato válido
    if not re.match(r'^[A-Z0-9]{2,10}$', symbol):
        return False, "O símbolo deve conter apenas letras e números, com 2 a 10 caracteres."
    
    return True, None


def validate_timeframe(timeframe: str, valid_timeframes: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Valida um intervalo de tempo.
    
    Args:
        timeframe: Intervalo a ser validado.
        valid_timeframes: Lista de intervalos válidos.
        
    Returns:
        Tuple[bool, Optional[str]]: Tupla com flag de validade e mensagem de erro (se houver).
    """
    # Converte para minúsculas e remove espaços
    timeframe = timeframe.lower().strip()
    
    # Verifica se o intervalo está vazio
    if not timeframe:
        return False, "O intervalo de tempo não pode estar vazio."
    
    # Verifica se o intervalo é válido
    if timeframe not in valid_timeframes:
        return False, f"Intervalo de tempo inválido. Valores válidos: {', '.join(valid_timeframes)}."
    
    return True, None


def validate_percentage(percentage_str: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Valida e converte um percentual.
    
    Args:
        percentage_str: String com o percentual a ser validado.
        
    Returns:
        Tuple[bool, Optional[float], Optional[str]]: Tupla com flag de validade, 
        valor convertido e mensagem de erro (se houver).
    """
    # Remove espaços e o símbolo de percentual, se houver
    percentage_str = percentage_str.strip().replace('%', '')
    
    # Verifica se o percentual está vazio
    if not percentage_str:
        return False, None, "O percentual não pode estar vazio."
    
    try:
        # Converte para float
        percentage = float(percentage_str)
        
        # Verifica se o percentual está dentro de um intervalo razoável
        if abs(percentage) > 100:
            return False, None, "O percentual deve estar entre -100% e 100%."
        
        return True, percentage, None
    
    except ValueError:
        return False, None, "Percentual inválido. Use um número, por exemplo: 5.5"


def validate_price(price_str: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Valida e converte um preço.
    
    Args:
        price_str: String com o preço a ser validado.
        
    Returns:
        Tuple[bool, Optional[float], Optional[str]]: Tupla com flag de validade, 
        valor convertido e mensagem de erro (se houver).
    """
    # Remove espaços
    price_str = price_str.strip()
    
    # Verifica se o preço está vazio
    if not price_str:
        return False, None, "O preço não pode estar vazio."
    
    try:
        # Converte para float
        price = float(price_str)
        
        # Verifica se o preço é positivo
        if price <= 0:
            return False, None, "O preço deve ser maior que zero."
        
        return True, price, None
    
    except ValueError:
        return False, None, "Preço inválido. Use um número, por exemplo: 50000.5"


def validate_user_id(user_id_str: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Valida e converte um ID de usuário.
    
    Args:
        user_id_str: String com o ID a ser validado.
        
    Returns:
        Tuple[bool, Optional[int], Optional[str]]: Tupla com flag de validade, 
        valor convertido e mensagem de erro (se houver).
    """
    # Remove espaços
    user_id_str = user_id_str.strip()
    
    # Verifica se o ID está vazio
    if not user_id_str:
        return False, None, "O ID de usuário não pode estar vazio."
    
    # Verifica se o ID tem um formato válido
    if not re.match(r'^\d+$', user_id_str):
        return False, None, "O ID de usuário deve conter apenas números."
    
    try:
        # Converte para int
        user_id = int(user_id_str)
        return True, user_id, None
    
    except ValueError:
        return False, None, "ID de usuário inválido." 