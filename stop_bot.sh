#!/bin/bash

# Script para encerrar o bot de forma segura
# Este script verifica e mata qualquer instância do bot em execução
# e remove arquivos de lock.

echo "=== Iniciando processo de encerramento do Crypto Agent ==="
echo "$(date): Verificando instâncias em execução..."

# Diretório do projeto
PROJECT_DIR="$(pwd)"
LOCK_FILE="$PROJECT_DIR/crypto_agent.lock"
LOG_FILE="$PROJECT_DIR/bot.log"

# Função para verificar e encerrar processos existentes
stop_bot_processes() {
    # Verifica se existe um arquivo de lock
    if [ -f "$LOCK_FILE" ]; then
        PID=$(cat "$LOCK_FILE")
        echo "Arquivo de lock encontrado com PID: $PID"
        
        # Verifica se o processo está em execução
        if ps -p $PID > /dev/null; then
            echo "Processo principal com PID $PID está em execução."
            echo "Enviando sinal SIGTERM para encerramento gracioso..."
            kill -15 $PID
            
            # Aguarda até 10 segundos pelo encerramento gracioso
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null; then
                    echo "Processo $PID encerrado com sucesso (graciosamente)"
                    break
                fi
                echo "Aguardando encerramento ($i/10)..."
                sleep 1
            done
            
            # Se ainda estiver em execução, força o encerramento
            if ps -p $PID > /dev/null; then
                echo "Processo não respondeu ao SIGTERM. Forçando encerramento com SIGKILL..."
                kill -9 $PID
                sleep 2
                
                if ! ps -p $PID > /dev/null; then
                    echo "Processo $PID encerrado com sucesso (forçado)"
                else
                    echo "ERRO: Não foi possível encerrar o processo $PID"
                    return 1
                fi
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
            kill -15 $PID  # Tenta primeiro com SIGTERM
            sleep 2
            
            # Se ainda estiver em execução, força o encerramento
            if ps -p $PID > /dev/null; then
                echo "Forçando encerramento do processo $PID..."
                kill -9 $PID
                sleep 1
            fi
            
            if ! ps -p $PID > /dev/null; then
                echo "Processo $PID encerrado com sucesso"
            else
                echo "ERRO: Não foi possível encerrar o processo $PID"
            fi
        done
    else
        echo "Nenhum outro processo encontrado"
    fi
    
    return 0
}

# Função para remover arquivos de lock
remove_lock_files() {
    echo "Removendo arquivos de lock..."
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        echo "Arquivo de lock removido: $LOCK_FILE"
    fi
}

# Função para registrar o encerramento no log
log_shutdown() {
    if [ -f "$LOG_FILE" ]; then
        echo "Registrando encerramento no arquivo de log..."
        echo "=== Bot encerrado em $(date) ===" >> "$LOG_FILE"
    fi
}

# Executa as funções em sequência
stop_bot_processes
STOP_RESULT=$?

if [ $STOP_RESULT -eq 0 ]; then
    remove_lock_files
    log_shutdown
    echo "=== Bot encerrado com sucesso ==="
else
    echo "=== AVISO: Houve problemas ao encerrar o bot ==="
    echo "Verifique manualmente se há processos remanescentes."
fi

# Verifica se ainda há processos em execução
REMAINING=$(ps aux | grep "python.*main\.py" | grep -v grep | wc -l)
if [ $REMAINING -gt 0 ]; then
    echo "AVISO: Ainda existem $REMAINING processos do bot em execução."
    echo "Você pode verificá-los com: ps aux | grep 'python.*main\.py' | grep -v grep"
else
    echo "Nenhum processo do bot em execução."
fi

echo "=== Processo de encerramento concluído ===" 