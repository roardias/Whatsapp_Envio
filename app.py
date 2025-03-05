from flask import Flask, request, jsonify
import json
from database import get_db_connection
import logging
from whatsapp_sender import WhatsAppSender
import os
from datetime import datetime

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Caminho para o arquivo de flag
FLAG_FILE = "new_messages_flag.txt"

def create_update_flag_file():
    """Cria ou atualiza o arquivo de flag para sinalizar novas mensagens"""
    try:
        with open(FLAG_FILE, "w") as f:
            f.write(str(datetime.now()))
        logger.info(f"Arquivo de flag atualizado: {FLAG_FILE}")
    except Exception as e:
        logger.error(f"Erro ao criar arquivo de flag: {e}")

def handle_button_response(message_text, sender_number):
    try:
        whatsapp_sender = WhatsAppSender()
       
        if message_text == "Tenho Interesse":
            response = (    "Olá! Que bom falar com você! 😊\n\n"
                            "O Kelvin entrará em contato em breve para dar seguimento ao seu atendimento.\n\n"
                            "Se preferir, pode falar com nosso suporte pelo WhatsApp clicando no link:\n\n"
                            "https://wa.me/6136865169.\n\n"
                            "Ficamos felizes em ajudar! Tenha um ótimo dia! 💰✨"
                       )
            whatsapp_sender.send_text_message(to=sender_number, message=response)
           
        elif message_text == "Não":
            response = ("Tudo bem, obrigado pelo seu retorno, se precisar de um empréstimo futuramente, pode contar comigo.\n"
                       "Basta me chamar no numero 6136865169")
            whatsapp_sender.send_text_message(to=sender_number, message=response)
           
    except Exception as e:
        logger.error(f"Erro ao enviar resposta automática: {e}")

@app.before_request
def log_request_info():
    logger.info('=== Nova Requisição ===')
    logger.info(f'Headers: {dict(request.headers)}')
    logger.info(f'Body: {request.get_data()}')

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
       
        logger.info(f"Verificação Webhook - Mode: {mode}, Token: {token}, Challenge: {challenge}")
       
        verify_token = "consigocred2024"
       
        if mode and token:
            if mode == 'subscribe' and token == verify_token:
                logger.info("Webhook verificado com sucesso!")
                return challenge, 200
            else:
                logger.warning("Verificação falhou: token inválido")
                return "Forbidden", 403
       
        logger.warning("Verificação falhou: parâmetros ausentes")
        return "Bad Request", 400
       
    elif request.method == 'POST':
        logger.info("=== NOVA MENSAGEM RECEBIDA NO WEBHOOK ===")
        try:
            data = request.get_json()
            logger.info(f"Headers recebidos: {dict(request.headers)}")
            logger.info(f"Payload completo: {json.dumps(data, indent=2)}")
           
            if not data:
                logger.error("Payload vazio")
                return jsonify({"error": "No data received"}), 400
               
            conn = get_db_connection()
            cursor = conn.cursor()
            
            mensagens_processadas = 0
           
            for entry in data.get('entry', []):
                logger.info(f"Processando entry: {entry}")
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                   
                    for message in messages:
                        logger.info(f"Tipo de mensagem recebida: {message.keys()}")
                        whatsapp_id = message.get('id')
                        sender = message.get('from')
                        recipient = value.get('metadata', {}).get('display_phone_number', '')
                        text = None
                        message_type = None
                       
                        if 'text' in message:
                            text = message['text'].get('body', '')
                            message_type = 'text'
                            logger.info(f"Mensagem de texto recebida: {text}")
                        elif 'button' in message:
                            text = message['button'].get('text', '')
                            message_type = 'button'
                            logger.info(f"Resposta do botão recebida: {text}")
                           
                            # Processa resposta automática para botões
                            if text in ["Tenho Interesse", "Não"]:
                                handle_button_response(text, sender)
                       
                        if text and message_type:
                            # Salvar a nova mensagem com visualized=0
                            cursor.execute('''
                                INSERT INTO messages
                                (whatsapp_id, sender, recipient, message, message_type, status, answered, visualized)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (whatsapp_id, sender, recipient, text, message_type, 'received', 0, 0))
                            
                            conn.commit()
                            mensagens_processadas += 1
                            logger.info("Mensagem salva com sucesso")
            
            conn.close()
            
            # Se mensagens foram processadas, criar/atualizar o arquivo de flag
            if mensagens_processadas > 0:
                create_update_flag_file()
                logger.info(f"Processadas {mensagens_processadas} mensagens. Flag de notificação criada.")
           
            return jsonify({"status": "success"}), 200
           
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
