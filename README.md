# Crypto Agent - Assistente de Monitoramento de Criptomoedas

Um bot do Telegram para monitoramento de criptomoedas em tempo real, com análise técnica e alertas personalizados.

## Funcionalidades

- Monitoramento em tempo real de preços de criptomoedas
- Análise técnica com indicadores como EMA, RSI e análise de volume
- Alertas personalizados baseados em variações de preço e indicadores técnicos
- Análise de divergência VMC Cipher para identificação de oportunidades de trading
  - Detecção de círculos verdes (oportunidades de compra)
  - Detecção de círculos dourados (confirmação de compra)
  - Detecção de círculos vermelhos (oportunidades de venda)
  - Detecção de triângulos roxos (alertas de divergência)
- **Novo:** Detecção de tendência de baixa de curto prazo
  - Identifica criptomoedas com RSI abaixo de 45 no timeframe de 4 horas
  - Verifica VMC Cipher com círculo vermelho no timeframe de 1 hora
- Interface amigável via Telegram
- Suporte a múltiplos usuários com controle de acesso
- **Novo:** Scripts robustos para inicialização e encerramento seguro do bot

## Requisitos

- Python 3.9+
- Conta de bot do Telegram (via BotFather)
- Ngrok ou serviço similar para webhooks (em produção)
- Acesso às APIs de criptomoedas (Binance, etc.)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/crypto-agent.git
cd crypto-agent
```

2. Instale o TA-Lib (biblioteca de análise técnica):

   **macOS**:
   ```bash
   # Instale o Homebrew primeiro, se ainda não estiver instalado
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Adicione o Homebrew ao PATH, se necessário
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   eval "$(/opt/homebrew/bin/brew shellenv)"
   
   # Agora instale o TA-Lib
   brew install ta-lib
   ```

   **Alternativa para macOS (sem Homebrew)**:
   ```bash
   # Baixe e compile manualmente
   curl -O http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
   tar -xzf ta-lib-0.4.0-src.tar.gz
   cd ta-lib/
   ./configure --prefix=/usr/local
   make
   sudo make install
   cd ..
   ```

   **Linux (Ubuntu/Debian)**:
   ```bash
   wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
   tar -xzf ta-lib-0.4.0-src.tar.gz
   cd ta-lib/
   ./configure --prefix=/usr
   make
   sudo make install
   cd ..
   ```

   **Windows**:
   - Baixe os binários pré-compilados em: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
   - Instale o arquivo .whl baixado:
   ```bash
   pip install caminho/para/arquivo/TA_Lib‑0.4.28‑cp39‑cp39‑win_amd64.whl
   ```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. Execute o bot:
```bash
# Método recomendado (usando o script de inicialização segura)
./start_bot.sh

# Método alternativo (execução direta)
python main.py
```

## Estrutura do Projeto

```
crypto-agent/
├── main.py                           # Ponto de entrada da aplicação
├── config.py                         # Configurações e carregamento de variáveis de ambiente
├── start_bot.sh                      # Script para inicialização segura do bot
├── stop_bot.sh                       # Script para encerramento seguro do bot
├── services/                         # Serviços modulares
│   ├── telegram_service.py           # Serviço de integração com o Telegram
│   ├── crypto_service.py             # Serviço de dados de criptomoedas
│   ├── analysis_service.py           # Serviço de análise técnica
│   ├── scheduler_service.py          # Serviço de agendamento de tarefas
│   ├── vmc_cipher_service.py         # Serviço de análise VMC Cipher Divergency
│   └── short_term_downtrend_service.py # Serviço de detecção de tendência de baixa de curto prazo
├── models/                           # Modelos de dados
│   ├── crypto.py                     # Modelos para dados de criptomoedas
│   └── user.py                       # Modelos para dados de usuários
└── utils/                            # Utilitários
    ├── logger.py                     # Configuração de logging
    ├── formatters.py                 # Formatadores de mensagens
    └── validators.py                 # Validadores de entrada
```

## Uso

Após iniciar o bot, envie o comando `/start` no Telegram para começar a interagir com ele.

Comandos disponíveis:
- `/start` - Inicia a interação com o bot
- `/help` - Exibe a lista de comandos disponíveis
- `/price <símbolo>` - Exibe o preço atual de uma criptomoeda
- `/analysis <símbolo>` - Exibe análise técnica de uma criptomoeda
- `/alert <símbolo> <percentual>` - Configura um alerta de variação de preço
- `/watchlist` - Gerencia sua lista de criptomoedas favoritas
- `/analise <símbolo>` - Exibe análise de preço e variação percentual
- `/vmc <símbolo> [timeframe]` - Análise usando o indicador VMC Cipher

## Gerenciamento do Bot

### Scripts de Gerenciamento

O projeto agora inclui scripts robustos para gerenciar o ciclo de vida do bot:

#### Inicialização Segura (start_bot.sh)

Este script garante uma inicialização segura do bot:
- Verifica e encerra qualquer instância do bot em execução
- Remove arquivos de lock que possam bloquear a inicialização
- Inicia o bot em segundo plano com redirecionamento de logs

```bash
./start_bot.sh
```

#### Encerramento Seguro (stop_bot.sh)

Este script encerra o bot de forma segura:
- Tenta primeiro um encerramento gracioso (SIGTERM)
- Se necessário, força o encerramento (SIGKILL)
- Remove arquivos de lock
- Registra o encerramento no arquivo de log

```bash
./stop_bot.sh
```

## Serviços Agendados

O bot executa os seguintes serviços em intervalos regulares:

- **Verificação de Preços**: A cada 5 minutos
- **Análise VMC Cipher**: A cada 15 minutos
- **Verificação de Oportunidades de Compra**: A cada 30 minutos
- **Verificação de Tendência de Baixa de Curto Prazo**: A cada 12 minutos (novo)

## Configuração de Logging

O sistema de logging foi configurado para registrar apenas erros, tanto no console quanto nos arquivos de log, reduzindo o ruído e facilitando a identificação de problemas.

Os logs são armazenados no diretório `logs/` com o formato `crypto_agent_YYYY-MM-DD.log`.

## VMC Cipher

O VMC Cipher é um indicador técnico avançado que combina o WaveTrend com o RSI para identificar oportunidades de compra e venda. O bot implementa os seguintes sinais:

- **Círculo Verde**: Indica uma possível oportunidade de compra. Ocorre quando o WaveTrend cruza para cima a partir de uma condição de sobrevenda.
- **Círculo Dourado**: Confirmação adicional de oportunidade de compra. Ocorre quando o WaveTrend cruza para cima e o RSI está em condição de sobrevenda.
- **Círculo Vermelho**: Indica uma possível oportunidade de venda. Ocorre quando o WaveTrend cruza para baixo a partir de uma condição de sobrecompra.
- **Triângulo Roxo**: Alerta de divergência. Ocorre quando há uma divergência entre o preço e o WaveTrend.

O bot verifica automaticamente estes sinais em intervalos regulares e notifica os usuários quando encontra oportunidades de trading. Você também pode solicitar uma análise manual usando o comando `/vmc`.

## Detecção de Tendência de Baixa de Curto Prazo

O novo serviço de detecção de tendência de baixa de curto prazo identifica criptomoedas que atendem aos seguintes critérios:

1. RSI abaixo de 45 no timeframe de 4 horas
2. VMC Cipher com círculo vermelho no timeframe de 1 hora

Este serviço é executado a cada 12 minutos e envia notificações para o chat do Telegram quando encontra criptomoedas que atendem a esses critérios.

## Solução de Problemas

### Instalação do TA-Lib

O TA-Lib pode ser complicado de instalar em alguns sistemas. Aqui estão algumas soluções para problemas comuns:

#### macOS

- **Erro "command not found: brew"**: Instale o Homebrew primeiro usando o comando fornecido nas instruções de instalação.
- **Erro ao compilar**: Certifique-se de ter o Xcode Command Line Tools instalado:
  ```bash
  xcode-select --install
  ```

#### Linux

- **Erro "fatal error: ta-lib/ta_defs.h file not found"**: Verifique se o TA-Lib foi instalado corretamente. Tente reinstalar com:
  ```bash
  sudo apt-get install build-essential
  ```
  E depois siga as instruções de instalação do TA-Lib novamente.

#### Windows

- **Erro ao instalar o arquivo .whl**: Certifique-se de baixar a versão correta para sua versão do Python e arquitetura do sistema (32 ou 64 bits).
- **Alternativa**: Você pode usar o conda para instalar o TA-Lib:
  ```bash
  conda install -c conda-forge ta-lib
  ```

### Alternativa: Usar apenas a biblioteca 'ta'

Se você continuar tendo problemas com o TA-Lib, pode optar por usar apenas a biblioteca 'ta' que já está incluída nas dependências. Ela oferece funcionalidades similares, embora não tão completas quanto o TA-Lib.

O bot está configurado para usar a biblioteca 'ta' como alternativa quando o TA-Lib não está disponível.

### Problemas com o Arquivo de Lock

Se você encontrar mensagens de erro indicando que "Outra instância do Crypto Agent já está em execução", mas tem certeza de que não há outra instância em execução, use o script `start_bot.sh` que foi projetado para lidar com essa situação automaticamente.

Alternativamente, você pode remover manualmente o arquivo de lock:
```bash
rm crypto_agent.lock
```

## Licença

MIT 