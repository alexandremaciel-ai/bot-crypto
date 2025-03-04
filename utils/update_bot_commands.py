"""Utility script to update Telegram bot commands."""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import Application
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def update_bot_commands():
    """Updates the bot commands in Telegram to match the implemented commands."""
    # Initialize the bot application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Start the application
    await app.initialize()
    await app.start()
    
    # Define the available commands with their descriptions
    commands = [
        BotCommand("start", "Inicia a interação com o bot"),
        BotCommand("preco", "Consulta o preço atual de uma criptomoeda"),
        BotCommand("variacao", "Consulta a variação em 24h de uma criptomoeda"),
        BotCommand("analise", "Análise técnica completa de uma criptomoeda"),
        BotCommand("alerta", "Define alerta de variação de preço"),
        BotCommand("compras", "Lista oportunidades de compra"),
        BotCommand("moedas", "Lista as criptomoedas disponíveis na Binance"),
        BotCommand("vmc", "Análise usando o indicador VMC Cipher"),
        BotCommand("ajuda", "Exibe a lista de comandos disponíveis")
    ]
    
    try:
        # Update the bot's command list for all scopes
        await app.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        print("✅ Bot commands updated successfully!")
        
        # Also update for private chats
        await app.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
        print("✅ Bot commands updated for private chats!")
        
        # Try to update for specific chat if TELEGRAM_CHAT_ID is defined
        try:
            if TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID != 0:
                await app.bot.set_my_commands(
                    commands=commands,
                    scope=BotCommandScopeChat(chat_id=TELEGRAM_CHAT_ID)
                )
                print(f"✅ Bot commands updated for specific chat ID: {TELEGRAM_CHAT_ID}")
                
                # Send a message to the chat to force refresh
                await app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text="🔄 Lista de comandos atualizada! Digite / para ver todos os comandos disponíveis."
                )
                print(f"✅ Notification sent to chat ID: {TELEGRAM_CHAT_ID}")
        except Exception as e:
            print(f"⚠️ Could not update commands for specific chat: {str(e)}")
        
        # List the updated commands
        print("\n📋 Available commands:")
        for cmd in commands:
            print(f"/{cmd.command} - {cmd.description}")
            
    except Exception as e:
        print(f"❌ Error updating bot commands: {str(e)}")
    finally:
        # Cleanup
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    import asyncio
    asyncio.run(update_bot_commands())