#!/bin/bash

# Script para iniciar o bot de forma robusta
# Este script verifica e mata qualquer instância do bot em execução,
# remove arquivos de lock e inicia o bot de forma segura.

echo "=== Iniciando processo de inicialização do Crypto Agent ==="
echo "$(date): Verificando instâncias existentes..."

# Diretório do projeto
PROJECT_DIR="$(pwd)"
LOCK_FILE="$PROJECT_DIR/crypto_agent.lock"
LOG_FILE="$PROJECT_DIR/bot.log"

# Função para verificar e matar processos existentes
kill_existing_processes() {
    # Verifica se existe um arquivo de lock
    if [ -f "$LOCK_FILE" ]; then
        PID=$(cat "$LOCK_FILE")
        echo "Arquivo de lock encontrado com PID: $PID"
        
        # Verifica se o processo está em execução
        if ps -p $PID > /dev/null; then
            echo "Processo com PID $PID está em execução. Encerrando..."
            kill -9 $PID
            sleep 2
            
            # Verifica se o processo foi encerrado
            if ps -p $PID > /dev/null; then
                echo "ERRO: Não foi possível encerrar o processo $PID"
            else
                echo "Processo $PID encerrado com sucesso"
            fi
        else
            echo "Processo com PID $PID não está em execução"
        fi
    else
        echo "Nenhum arquivo de lock encontrado"
    fi
    
    # Procura por outros processos Python executando main.py
    echo "Procurando por outros processos Python executando main.py..."
    PIDS=$(ps aux | grep "python.*main\.py" | grep -v grep | awk '{print $2}')
    
    if [ -n "$PIDS" ]; then
        echo "Encontrados os seguintes processos: $PIDS"
        for PID in $PIDS; do
            echo "Encerrando processo $PID..."
            kill -9 $PID
            sleep 1
        done
    else
        echo "Nenhum outro processo encontrado"
    fi
}

# Função para remover arquivos de lock
remove_lock_files() {
    echo "Removendo arquivos de lock..."
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        echo "Arquivo de lock removido: $LOCK_FILE"
    fi
}

# Função para iniciar o bot
start_bot() {
    echo "Iniciando o bot..."
    
    # Cria um novo arquivo de log ou limpa o existente
    echo "=== Log do Crypto Agent iniciado em $(date) ===" > "$LOG_FILE"
    
    # Inicia o bot em segundo plano
    nohup python3 main.py >> "$LOG_FILE" 2>&1 &
    
    # Obtém o PID do processo
    BOT_PID=$!
    
    # Verifica se o processo foi iniciado corretamente
    if ps -p $BOT_PID > /dev/null; then
        echo "Bot iniciado com sucesso! PID: $BOT_PID"
        echo "Logs disponíveis em: $LOG_FILE"
    else
        echo "ERRO: Falha ao iniciar o bot"
        exit 1
    fi
}

# Executa as funções em sequência
kill_existing_processes
remove_lock_files
start_bot

echo "=== Processo de inicialização concluído ===" 