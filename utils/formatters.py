"""
Utilitários para formatação de mensagens e dados.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pytz

from models.crypto import CryptoPrice, PriceChange, TechnicalAnalysis
from config import DEFAULT_TIMEZONE


def format_price(price: float, decimals: int = 8) -> str:
    """
    Formata um preço com o número especificado de casas decimais.
    
    Args:
        price: Preço a ser formatado.
        decimals: Número de casas decimais.
        
    Returns:
        str: Preço formatado.
    """
    formatted = f"{price:.{decimals}f}"
    return formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted


def format_percent(percent: float) -> str:
    """
    Formata um percentual.
    
    Args:
        percent: Percentual a ser formatado.
        
    Returns:
        str: Percentual formatado.
    """
    sign = "+" if percent > 0 else ""
    return f"{sign}{percent:.2f}%"


def format_volume(volume: float) -> str:
    """
    Formata um volume para exibição mais legível.
    
    Args:
        volume: Volume a ser formatado.
        
    Returns:
        str: Volume formatado.
    """
    if volume >= 1_000_000_000:
        return f"{volume / 1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        return f"{volume / 1_000_000:.2f}M"
    elif volume >= 1_000:
        return f"{volume / 1_000:.2f}K"
    else:
        return f"{volume:.2f}"


def format_timestamp(timestamp, timezone: Optional[pytz.timezone] = None) -> str:
    """
    Formata um timestamp.
    
    Args:
        timestamp: Timestamp a ser formatado (pode ser datetime ou float).
        timezone: Fuso horário (opcional).
        
    Returns:
        str: Timestamp formatado.
    """
    tz = timezone or DEFAULT_TIMEZONE
    
    # Converte float para datetime se necessário
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp)
    
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=pytz.UTC)
    localized = timestamp.astimezone(tz)
    return localized.strftime("%d/%m/%Y %H:%M:%S")


def format_price_message(price: CryptoPrice) -> str:
    """
    Formata uma mensagem com o preço de uma criptomoeda.
    
    Args:
        price: Modelo com o preço.
        
    Returns:
        str: Mensagem formatada.
    """
    return (
        f"💰 <b>{price.symbol}</b>\n"
        f"Preço: {price.formatted_price} USDT\n"
        f"Atualizado em: {format_timestamp(price.timestamp)}"
    )


def format_price_change_message(price_change: PriceChange) -> str:
    """
    Formata uma mensagem com a variação de preço de uma criptomoeda.
    
    Args:
        price_change: Modelo com a variação de preço.
        
    Returns:
        str: Mensagem formatada.
    """
    emoji = "🟢" if price_change.percent_change >= 0 else "🔴"
    return (
        f"{emoji} <b>{price_change.symbol}</b>\n"
        f"Preço atual: {format_price(price_change.current_price)} USDT\n"
        f"Variação 24h: {price_change.formatted_change}\n"
        f"Atualizado em: {format_timestamp(price_change.timestamp)}"
    )


def format_technical_analysis_message(analysis: TechnicalAnalysis) -> str:
    """
    Formata uma mensagem com a análise técnica de uma criptomoeda.
    
    Args:
        analysis: Modelo com a análise técnica.
        
    Returns:
        str: Mensagem formatada.
    """
    # Cabeçalho
    text = (
        f"📊 <b>Análise Técnica: {analysis.symbol}</b>\n"
        f"Preço atual: {analysis.price.formatted_price} USDT\n"
        f"Atualizado em: {format_timestamp(analysis.price.timestamp)}\n\n"
    )
    
    # EMAs
    if analysis.ema:
        text += "<b>📈 Médias Móveis Exponenciais (EMA)</b>\n"
        for timeframe, ema in analysis.ema.items():
            trend_emoji = "🟢" if ema.trend == "Alta" else "🔴" if ema.trend == "Baixa" else "⚪"
            text += (
                f"{trend_emoji} <b>{timeframe}</b>: {ema.trend}\n"
                f"  EMA Curta (9): {ema.short_ema:.2f}\n"
                f"  EMA Média (21): {ema.medium_ema:.2f}\n"
                f"  EMA Longa (50): {ema.long_ema:.2f}\n"
            )
        text += "\n"
    
    # RSIs
    if analysis.rsi:
        text += "<b>📉 Índice de Força Relativa (RSI)</b>\n"
        for timeframe, rsi in analysis.rsi.items():
            condition_emoji = "🟢" if rsi.condition == "Sobrevendido" else "🔴" if rsi.condition == "Sobrecomprado" else "⚪"
            text += f"{condition_emoji} <b>{timeframe}</b>: {rsi.value:.2f} ({rsi.condition})\n"
        text += "\n"
    
    # Volume
    if analysis.volume:
        text += "<b>📊 Análise de Volume</b>\n"
        for timeframe, vol in analysis.volume.items():
            volume_emoji = "🟢" if vol.is_high_volume else "🔴" if vol.is_low_volume else "⚪"
            text += (
                f"{volume_emoji} <b>{timeframe}</b>: {vol.volume_description}\n"
                f"  Volume atual: {format_volume(vol.current_volume)}\n"
                f"  Volume médio: {format_volume(vol.average_volume)}\n"
                f"  Razão: {vol.volume_ratio:.2f}x\n"
            )
    
    return text


def format_summary(analysis: TechnicalAnalysis) -> str:
    """
    Formata um resumo da análise técnica.
    
    Args:
        analysis: Modelo com a análise técnica.
        
    Returns:
        str: Resumo formatado.
    """
    # Determina a tendência geral
    trends = [ema.trend for ema in analysis.ema.values()]
    if all(trend == "Alta" for trend in trends):
        overall_trend = "Alta"
        trend_emoji = "🟢"
    elif all(trend == "Baixa" for trend in trends):
        overall_trend = "Baixa"
        trend_emoji = "🔴"
    else:
        overall_trend = "Lateral"
        trend_emoji = "⚪"
    
    # Determina a condição do RSI
    rsi_conditions = [rsi.condition for rsi in analysis.rsi.values()]
    if "Sobrecomprado" in rsi_conditions:
        rsi_condition = "Sobrecomprado"
        rsi_emoji = "🔴"
    elif "Sobrevendido" in rsi_conditions:
        rsi_condition = "Sobrevendido"
        rsi_emoji = "🟢"
    else:
        rsi_condition = "Neutro"
        rsi_emoji = "⚪"
    
    # Determina o volume
    volume_high = any(vol.is_high_volume for vol in analysis.volume.values())
    volume_low = any(vol.is_low_volume for vol in analysis.volume.values())
    
    if volume_high:
        volume_desc = "Alto"
        volume_emoji = "🟢"
    elif volume_low:
        volume_desc = "Baixo"
        volume_emoji = "🔴"
    else:
        volume_desc = "Normal"
        volume_emoji = "⚪"
    
    # Formata o resumo
    return (
        f"{trend_emoji} <b>Tendência</b>: {overall_trend}\n"
        f"{rsi_emoji} <b>RSI</b>: {rsi_condition}\n"
        f"{volume_emoji} <b>Volume</b>: {volume_desc}"
    ) 