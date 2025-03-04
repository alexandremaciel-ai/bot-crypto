"""
Serviço para análise de criptomoedas usando o indicador VMC Cipher Divergency.
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Tenta importar o talib, mas não falha se não estiver disponível
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("Aviso: Biblioteca TA-Lib não encontrada. Usando alternativa.")

from config import DEFAULT_SYMBOLS
from models.crypto import VMCAnalysisResult, PerfectBuyOpportunity, GreatBuyOpportunity, VMCCipherIndicator
from utils.logger import get_logger, log_exception

# Configuração do logger
logger = get_logger(__name__)

class VMCCipherService:
    """Serviço para análise de criptomoedas usando o indicador VMC Cipher Divergency."""
    
    def __init__(self, crypto_service, telegram_service):
        """
        Inicializa o serviço de análise VMC Cipher.
        
        Args:
            crypto_service: Serviço de criptomoedas.
            telegram_service: Serviço do Telegram.
        """
        self.crypto_service = crypto_service
        self.telegram_service = telegram_service
        
        # Parâmetros do WaveTrend
        self.wt_channel_len = 9
        self.wt_average_len = 12
        self.wt_ma_len = 3
        
        # Níveis de overbought e oversold
        self.ob_level = 53
        self.ob_level2 = 60
        self.ob_level3 = 100
        self.os_level = -53
        self.os_level2 = -60
        self.os_level3 = -75
        
        # Timeframes para análise
        self.weekly_timeframe = "1w"
        self.hourly_timeframes = ["3h", "4h", "12h"]
    
    async def analyze_symbol(self, symbol: str, timeframe: str) -> VMCAnalysisResult:
        """
        Analisa um símbolo usando o indicador VMC Cipher.
        
        Args:
            symbol: Símbolo da criptomoeda.
            timeframe: Timeframe para análise.
            
        Returns:
            VMCAnalysisResult: Resultado da análise.
        """
        try:
            # Obter dados históricos
            df = await self.crypto_service.get_historical_data(symbol, timeframe)
            if df is None or df.empty:
                logger.error(f"Não foi possível obter dados históricos para {symbol} em {timeframe}")
                return VMCAnalysisResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    has_green_circle=False,
                    has_gold_circle=False,
                    has_red_circle=False,
                    has_purple_triangle=False
                )
            
            # Calcular indicadores
            wt1, wt2 = self._calculate_wavetrend(df)
            rsi = self._calculate_rsi(df)
            
            # Verificar sinais
            has_green_circle = self._check_green_circle(wt1, wt2)
            has_gold_circle = self._check_gold_circle(wt1, wt2, rsi)
            has_red_circle = self._check_red_circle(wt1, wt2)
            has_purple_triangle = self._check_purple_triangle(wt1, wt2, df)
            
            # Verificar condições de sobrecompra/sobrevenda
            from config import TECHNICAL_INDICATORS
            is_overbought = wt1.iloc[-1] >= TECHNICAL_INDICATORS['vmc_cipher']['ob_level']
            is_oversold = wt1.iloc[-1] <= TECHNICAL_INDICATORS['vmc_cipher']['os_level']
            
            # Criar e retornar o resultado da análise
            result = VMCAnalysisResult(
                symbol=symbol,
                timeframe=timeframe,
                has_green_circle=has_green_circle,
                has_gold_circle=has_gold_circle,
                has_red_circle=has_red_circle,
                has_purple_triangle=has_purple_triangle
            )
            
            # Criar também o indicador completo para uso interno
            indicator = VMCCipherIndicator(
                wt1=wt1.iloc[-1],
                wt2=wt2.iloc[-1],
                rsi=rsi.iloc[-1],
                is_overbought=is_overbought,
                is_oversold=is_oversold,
                has_green_circle=has_green_circle,
                has_gold_circle=has_gold_circle,
                has_red_circle=has_red_circle,
                has_purple_triangle=has_purple_triangle,
                symbol=symbol,
                timeframe=timeframe
            )
            
            # Registrar o resultado no log
            logger.info(f"VMC Cipher para {symbol} ({timeframe}): {indicator.signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao analisar {symbol} com VMC Cipher: {str(e)}")
            return VMCAnalysisResult(
                symbol=symbol,
                timeframe=timeframe,
                has_green_circle=False,
                has_gold_circle=False,
                has_red_circle=False,
                has_purple_triangle=False
            )
    
    def _calculate_wavetrend(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Calcula o indicador WaveTrend.
        
        Args:
            df: DataFrame com os dados históricos.
            
        Returns:
            Tuple[pd.Series, pd.Series]: Séries wt1 e wt2.
        """
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        
        # Cálculo do WaveTrend
        esa = hlc3.ewm(span=self.wt_channel_len).mean()
        de = abs(hlc3 - esa).ewm(span=self.wt_channel_len).mean()
        ci = (hlc3 - esa) / (0.015 * de)
        
        wt1 = ci.ewm(span=self.wt_average_len).mean()
        wt2 = wt1.rolling(window=self.wt_ma_len).mean()
        
        return wt1, wt2
    
    def _calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """
        Calcula o indicador RSI.
        
        Args:
            df: DataFrame com os dados históricos.
            
        Returns:
            pd.Series: Série RSI.
        """
        if TALIB_AVAILABLE:
            try:
                return talib.RSI(df['close'], timeperiod=14)
            except Exception as e:
                logger.warning(f"Erro ao calcular RSI com TA-Lib: {str(e)}")
                # Continua para usar a alternativa
        
        # Usa a biblioteca 'ta' como alternativa
        try:
            from ta.momentum import RSIIndicator
            rsi_indicator = RSIIndicator(close=df['close'], window=14)
            return rsi_indicator.rsi()
        except Exception as e:
            logger.error(f"Erro ao calcular RSI com biblioteca 'ta': {str(e)}")
            # Retorna uma série de zeros como fallback
            return pd.Series(0, index=df.index)
    
    def _check_green_circle(self, wt1: pd.Series, wt2: pd.Series) -> bool:
        """
        Verifica se há um círculo verde (sinal de compra).
        O círculo verde aparece quando as ondas do wavetrend estão no nível de sobrevenda e cruzaram para cima.
        
        Args:
            wt1: Série wt1.
            wt2: Série wt2.
            
        Returns:
            bool: True se houver um círculo verde, False caso contrário.
        """
        # Verifica se wt2 está abaixo do nível de sobrevenda
        oversold = wt2.iloc[-1] <= self.os_level
        
        # Verifica se houve um cruzamento para cima
        cross_up = wt1.iloc[-2] < wt2.iloc[-2] and wt1.iloc[-1] > wt2.iloc[-1]
        
        return oversold and cross_up
    
    def _check_gold_circle(self, wt1: pd.Series, wt2: pd.Series, rsi: pd.Series) -> bool:
        """
        Verifica se há um círculo dourado (sinal de compra forte).
        O círculo dourado aparece quando o RSI está abaixo de 20, as ondas do wavetrend estão abaixo ou iguais a -80
        e cruzaram para cima após uma boa divergência de alta.
        
        Args:
            wt1: Série wt1.
            wt2: Série wt2.
            rsi: Série RSI.
            
        Returns:
            bool: True se houver um círculo dourado, False caso contrário.
        """
        # Verifica se o RSI está abaixo de 20
        rsi_below_20 = rsi.iloc[-1] < 20
        
        # Verifica se wt2 está abaixo ou igual a -80
        wt_below_80 = wt2.iloc[-1] <= -80
        
        # Verifica se houve um cruzamento para cima
        cross_up = wt1.iloc[-2] < wt2.iloc[-2] and wt1.iloc[-1] > wt2.iloc[-1]
        
        # Simplificação: não estamos verificando a divergência de alta
        return rsi_below_20 and wt_below_80 and cross_up
    
    def _check_red_circle(self, wt1: pd.Series, wt2: pd.Series) -> bool:
        """
        Verifica se há um círculo vermelho (sinal de venda).
        O círculo vermelho aparece quando as ondas do wavetrend estão no nível de sobrecompra e cruzaram para baixo.
        
        Args:
            wt1: Série wt1.
            wt2: Série wt2.
            
        Returns:
            bool: True se houver um círculo vermelho, False caso contrário.
        """
        # Verifica se wt2 está acima do nível de sobrecompra
        overbought = wt2.iloc[-1] >= self.ob_level
        
        # Verifica se houve um cruzamento para baixo
        cross_down = wt1.iloc[-2] > wt2.iloc[-2] and wt1.iloc[-1] < wt2.iloc[-1]
        
        return overbought and cross_down
    
    def _check_purple_triangle(self, wt1: pd.Series, wt2: pd.Series, df: pd.DataFrame) -> bool:
        """
        Verifica se há um triângulo roxo (divergência).
        O triângulo roxo aparece quando uma divergência de alta ou baixa é formada e as ondas do wavetrend
        cruzam nos pontos de sobrecompra e sobrevenda.
        
        Args:
            wt1: Série wt1.
            wt2: Série wt2.
            df: DataFrame com os dados históricos.
            
        Returns:
            bool: True se houver um triângulo roxo, False caso contrário.
        """
        # Simplificação: não estamos implementando a verificação completa de divergência
        # Apenas verificamos se há um cruzamento nos pontos de sobrecompra ou sobrevenda
        
        # Verifica se wt2 está no nível de sobrecompra ou sobrevenda
        extreme_level = wt2.iloc[-1] >= self.ob_level or wt2.iloc[-1] <= self.os_level
        
        # Verifica se houve um cruzamento
        cross = (wt1.iloc[-2] < wt2.iloc[-2] and wt1.iloc[-1] > wt2.iloc[-1]) or \
                (wt1.iloc[-2] > wt2.iloc[-2] and wt1.iloc[-1] < wt2.iloc[-1])
        
        return extreme_level and cross
    
    async def find_perfect_buy_opportunities(self) -> List[PerfectBuyOpportunity]:
        """
        Encontra oportunidades perfeitas de compra (círculo verde no timeframe de 1 semana).
        
        Returns:
            List[PerfectBuyOpportunity]: Lista de oportunidades perfeitas de compra.
        """
        opportunities = []
        
        for symbol in DEFAULT_SYMBOLS:
            try:
                # Analisa o símbolo no timeframe semanal
                result = await self.analyze_symbol(symbol, self.weekly_timeframe)
                
                # Se houver um círculo verde, é uma oportunidade perfeita de compra
                if result.has_green_circle:
                    price = await self.crypto_service.get_price(symbol)
                    opportunities.append(PerfectBuyOpportunity(
                        symbol=symbol,
                        price=price.price
                    ))
                    
                    logger.info(f"Oportunidade perfeita de compra encontrada para {symbol}")
            
            except Exception as e:
                log_exception(logger, e, f"Erro ao buscar oportunidade perfeita para {symbol}")
        
        return opportunities
    
    async def find_great_buy_opportunities(self) -> List[GreatBuyOpportunity]:
        """
        Encontra ótimas oportunidades de compra (círculo verde nos timeframes de 3h, 4h e 12h).
        
        Returns:
            List[GreatBuyOpportunity]: Lista de ótimas oportunidades de compra.
        """
        opportunities = []
        
        for symbol in DEFAULT_SYMBOLS:
            try:
                # Analisa o símbolo em cada timeframe
                results = {}
                for timeframe in self.hourly_timeframes:
                    results[timeframe] = await self.analyze_symbol(symbol, timeframe)
                
                # Verifica se há círculo verde em todos os timeframes
                green_timeframes = [tf for tf, result in results.items() if result.has_green_circle]
                
                # Se houver círculo verde em todos os timeframes, é uma ótima oportunidade de compra
                if len(green_timeframes) == len(self.hourly_timeframes):
                    price = await self.crypto_service.get_price(symbol)
                    opportunities.append(GreatBuyOpportunity(
                        symbol=symbol,
                        price=price.price,
                        timeframes=green_timeframes
                    ))
                    
                    logger.info(f"Ótima oportunidade de compra encontrada para {symbol} nos timeframes {green_timeframes}")
            
            except Exception as e:
                log_exception(logger, e, f"Erro ao buscar ótima oportunidade para {symbol}")
        
        return opportunities
    
    async def check_opportunities(self) -> None:
        """Verifica oportunidades de compra e venda com base no VMC Cipher."""
        try:
            # Verifica oportunidades perfeitas de compra
            perfect_opportunities = await self.find_perfect_buy_opportunities()
            if perfect_opportunities:
                for opportunity in perfect_opportunities:
                    message = (
                        f"🚨 *OPORTUNIDADE PERFEITA DE COMPRA* 🚨\n\n"
                        f"Símbolo: *{opportunity.symbol}*\n"
                        f"Preço: *{opportunity.price:.8f}*\n"
                        f"Sinal: *Círculo Verde* no timeframe *1 semana*\n\n"
                        f"Esta é uma oportunidade rara e potencialmente lucrativa!"
                    )
                    await self.telegram_service.send_message_to_all_users(message, parse_mode='Markdown')
            
            # Verifica ótimas oportunidades de compra
            great_opportunities = await self.find_great_buy_opportunities()
            if great_opportunities:
                for opportunity in great_opportunities:
                    timeframes_str = ", ".join([f"*{tf}*" for tf in opportunity.timeframes])
                    message = (
                        f"🔔 *ÓTIMA OPORTUNIDADE DE COMPRA* 🔔\n\n"
                        f"Símbolo: *{opportunity.symbol}*\n"
                        f"Preço: *{opportunity.price:.8f}*\n"
                        f"Sinal: *Círculo Verde* nos timeframes {timeframes_str}\n\n"
                        f"Considere analisar esta oportunidade!"
                    )
                    await self.telegram_service.send_message_to_all_users(message, parse_mode='Markdown')
                    
        except Exception as e:
            logger.error(f"Erro ao verificar oportunidades VMC Cipher: {str(e)}")
            
    async def generate_vmc_chart(self, symbol: str, timeframe: str) -> str:
        """
        Gera um gráfico do VMC Cipher para um símbolo e timeframe específicos.
        
        Args:
            symbol: Símbolo da criptomoeda.
            timeframe: Timeframe para análise.
            
        Returns:
            str: Caminho para o arquivo de imagem gerado.
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib.patches import Circle, Polygon
            import os
            from datetime import datetime
            
            # Obter dados históricos
            df = await self.crypto_service.get_historical_data(symbol, timeframe)
            if df is None or df.empty:
                logger.error(f"Não foi possível obter dados históricos para {symbol} em {timeframe}")
                return None
            
            # Calcular indicadores
            wt1, wt2 = self._calculate_wavetrend(df)
            rsi = self._calculate_rsi(df)
            
            # Verificar sinais
            has_green_circle = self._check_green_circle(wt1, wt2)
            has_gold_circle = self._check_gold_circle(wt1, wt2, rsi)
            has_red_circle = self._check_red_circle(wt1, wt2)
            has_purple_triangle = self._check_purple_triangle(wt1, wt2, df)
            
            # Criar figura
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
            
            # Plotar preço no gráfico superior
            ax1.plot(df.index, df['close'], color='black', linewidth=1.5)
            ax1.set_title(f'{symbol} - {timeframe}', fontsize=16)
            ax1.set_ylabel('Preço', fontsize=12)
            ax1.grid(True, alpha=0.3)
            
            # Formatar eixo x
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            # Plotar WaveTrend no gráfico inferior
            ax2.plot(df.index, wt1, color='blue', linewidth=1.5, label='WT1')
            ax2.plot(df.index, wt2, color='red', linewidth=1.5, label='WT2')
            
            # Adicionar linhas de sobrecompra/sobrevenda
            from config import TECHNICAL_INDICATORS
            ob_level = TECHNICAL_INDICATORS['vmc_cipher']['ob_level']
            os_level = TECHNICAL_INDICATORS['vmc_cipher']['os_level']
            ax2.axhline(y=ob_level, color='red', linestyle='--', alpha=0.5)
            ax2.axhline(y=os_level, color='green', linestyle='--', alpha=0.5)
            ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
            
            # Adicionar sinais ao gráfico
            last_idx = df.index[-1]
            
            if has_green_circle:
                circle = Circle((last_idx, wt2.iloc[-1]), 2, color='green', alpha=0.8)
                ax2.add_patch(circle)
                ax2.annotate('Círculo Verde', (last_idx, wt2.iloc[-1]), 
                             xytext=(10, 10), textcoords='offset points', color='green')
            
            if has_gold_circle:
                circle = Circle((last_idx, wt2.iloc[-1]), 2, color='gold', alpha=0.8)
                ax2.add_patch(circle)
                ax2.annotate('Círculo Dourado', (last_idx, wt2.iloc[-1]), 
                             xytext=(10, -10), textcoords='offset points', color='gold')
            
            if has_red_circle:
                circle = Circle((last_idx, wt2.iloc[-1]), 2, color='red', alpha=0.8)
                ax2.add_patch(circle)
                ax2.annotate('Círculo Vermelho', (last_idx, wt2.iloc[-1]), 
                             xytext=(10, 10), textcoords='offset points', color='red')
            
            if has_purple_triangle:
                triangle = Polygon([(last_idx, wt2.iloc[-1]), 
                                    (last_idx-2, wt2.iloc[-1]-2), 
                                    (last_idx+2, wt2.iloc[-1]-2)], 
                                   color='purple', alpha=0.8)
                ax2.add_patch(triangle)
                ax2.annotate('Triângulo Roxo', (last_idx, wt2.iloc[-1]), 
                             xytext=(10, -10), textcoords='offset points', color='purple')
            
            ax2.set_ylabel('WaveTrend', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # Ajustar layout
            plt.tight_layout()
            
            # Criar diretório para gráficos se não existir
            os.makedirs('charts', exist_ok=True)
            
            # Salvar gráfico
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f'charts/{symbol}_{timeframe}_{timestamp}.png'
            plt.savefig(filename)
            plt.close()
            
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar gráfico VMC Cipher para {symbol}: {str(e)}")
            return None 