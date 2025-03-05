import requests
import pandas as pd
import time
from typing import Dict, List
import os
from dotenv import load_dotenv
import json


class WhatsAppSender:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv('WHATSAPP_TOKEN')
        self.phone_number_id = os.getenv('PHONE_NUMBER_ID')
        self.version = 'v17.0'
        self.base_url = f'https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages'
       
        print("Iniciando WhatsAppSender")
        print(f"Token encontrado: {self.token[:10]}..." if self.token else "Token não encontrado")
        print(f"Phone Number ID encontrado: {self.phone_number_id}" if self.phone_number_id else "Phone Number ID não encontrado")

    def format_phone_number(self, phone: str) -> str:
        """
        Formata qualquer número de telefone para o padrão internacional +5511999999999.
        
        Args:
            phone (str): Número de telefone em qualquer formato
            
        Returns:
            str: Número formatado no padrão internacional
        """
        phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if phone.startswith('+'): phone = phone[1:]
        if not phone.startswith('55'): phone = '55' + phone
        return '+' + phone

    def send_template_message(self, to: str, template: str, parameters) -> Dict:
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
       
        # Formatar o número de telefone usando o método dedicado
        to = self.format_phone_number(to)
       
        # Payload base
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'template',
            'template': {
                'name': template,
                'language': {
                    'code': 'pt_BR'
                },
                'components': []
            }
        }
       
        # Lógica específica para cada template
        if template.lower() == "oferta_inss":
            # 1. Adicionar o componente de cabeçalho com estrutura completa para o tipo IMAGE
            payload['template']['components'].append({
                'type': 'header',
                'parameters': [
                    {
                        'type': 'image',
                        'image': {
                            'link': 'https://i.imgur.com/cl59zpz.png'  # Link correto com extensão PNG
                        }
                    }
                ]
            })
           
            # 2. Adicionar o componente do corpo com o parâmetro NOMEADO "nome"
            if isinstance(parameters, dict) and 'nome' in parameters:
                payload['template']['components'].append({
                    'type': 'body',
                    'parameters': [
                        {
                            'type': 'text',
                            'text': str(parameters['nome']).strip(),
                            'parameter_name': 'nome'  # Adicionando o nome do parâmetro
                        }
                    ]
                })
        else:
            # Para templates POSITIONAL como "primiero_contato_consignado"
            # Manter o comportamento atual que já funciona
            payload['template']['components'] = [{
                'type': 'body',
                'parameters': parameters
            }]
       
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Detalhes do erro: {e.response.text}")
                print(f"Payload enviado: {json.dumps(payload, indent=2)}")
            raise

    def send_text_message(self, to: str, message: str) -> Dict:
        """
        Envia uma mensagem de texto simples para um número do WhatsApp.
       
        Args:
            to (str): Número de telefone do destinatário
            message (str): Texto da mensagem a ser enviada
           
        Returns:
            dict: Resposta da API do WhatsApp
        """
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
       
        # Formatar o número de telefone usando o método dedicado
        to = self.format_phone_number(to)
       
        # Payload para mensagem de texto simples
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': to,
            'type': 'text',
            'text': {
                'preview_url': False,
                'body': message
            }
        }
       
        try:
            print(f"Enviando mensagem de texto para {to}")
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Detalhes do erro: {e.response.text}")
                print(f"Payload enviado: {json.dumps(payload, indent=2)}")
            raise
       
    def send_dynamic_template_message(self, to, template_name, parameters=None):
        """
        Envia uma mensagem de template dinâmico do WhatsApp
        """
        try:
            print(f"Enviando mensagem para {to} usando template {template_name}")
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "pt_BR"
                    },
                    "components": []
                }
            }
            
            # Lógica específica para cada template
            if template_name.lower() == "oferta_inss":
                # 1. Adicionar o componente de cabeçalho com a imagem
                payload['template']['components'].append({
                    'type': 'header',
                    'parameters': [
                        {
                            'type': 'image',
                            'image': {
                                'link': 'https://i.imgur.com/cl59zpz.png'
                            }
                        }
                    ]
                })
                
                # 2. Adicionar o componente do corpo com o parâmetro nomeado
                nome_valor = ""
                if isinstance(parameters, list) and parameters:
                    for param in parameters:
                        if param.get('type') == 'text':
                            nome_valor = param.get('text', '')
                            break
                
                payload['template']['components'].append({
                    'type': 'body',
                    'parameters': [
                        {
                            'type': 'text',
                            'text': str(nome_valor),
                            'parameter_name': 'nome'
                        }
                    ]
                })
            else:
                # Para templates POSITIONAL como "primiero_contato_consignado"
                payload['template']['components'] = [{
                    'type': 'body',
                    'parameters': parameters
                }]
            
            # Enviar a requisição
            url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
            response = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            # Verificar resposta
            if response.status_code != 200:
                print(f"Erro na requisição: {response.status_code} {response.reason} for url: {url}")
                print(f"Detalhes do erro: {response.text}")
                response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            print(f"Erro ao enviar mensagem de template para {to}: {str(e)}")
            raise

   
    def get_available_templates(self):
        """Obtém lista de templates disponíveis na conta do WhatsApp Business"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
       
        # Usa o ID da conta comercial que já está no .env
        business_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
        url = f'https://graph.facebook.com/{self.version}/{business_id}/message_templates'
       
        print(f"Tentando acessar URL: {url}")
        print(f"Usando business_id: {business_id}")
        print(f"Token (primeiros 10 caracteres): {self.token[:10]}...")
       
        try:
            response = requests.get(url, headers=headers)
            print(f"Status code: {response.status_code}")
            print(f"Resposta completa: {response.text}")
           
            response.raise_for_status()
            result = response.json()
            return result.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter templates: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Detalhes do erro: {e.response.text}")
            import traceback
            print(f"Traceback completo: {traceback.format_exc()}")
            return []

def process_csv_with_dynamic_template(csv_file: str, template_name: str, params_config: dict, template_info=None):
    """
    Processa um arquivo CSV e envia mensagens usando um template dinâmico
    """
    try:
        print("Iniciando processamento do CSV com template dinâmico")
        print(f"Template: {template_name}")
        print(f"Configuração de parâmetros: {json.dumps(params_config, indent=2)}")
        
        # Verificação de segurança para parâmetros
        if not params_config:
            print("AVISO: Configuração de parâmetros vazia. O template pode exigir parâmetros.")
        
        # Carregar CSV usando ponto e vírgula explicitamente e mostrar as colunas
        try:
            df = pd.read_csv(csv_file, sep=';', encoding='utf-8')
            print("CSV carregado com separador ';'")
        except:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                print("CSV carregado com separador padrão ','")
            except:
                df = pd.read_csv(csv_file, sep=';', encoding='latin1')
                print("CSV carregado com encoding alternativo 'latin1'")
            
        print(f"CSV carregado com {len(df)} linhas")
        print(f"Colunas disponíveis: {list(df.columns)}")
        
        # Normalizar nomes das colunas (remover espaços e converter para minúsculas)
        df.columns = [col.strip().lower() for col in df.columns]
        print(f"Colunas normalizadas: {list(df.columns)}")
        
        # Verificar coluna telefone
        if 'telefone' not in df.columns:
            raise ValueError(f"O arquivo CSV deve conter uma coluna 'telefone'. Colunas encontradas: {list(df.columns)}")
        
        sender = WhatsAppSender()
        
        # Obter template_info se não fornecido
        if template_info is None:
            templates = sender.get_available_templates()
            template_info = next((t for t in templates if t['name'] == template_name), None)
        
        # Determinar tipo de formato de parâmetro
        is_positional = template_info and template_info.get('parameter_format') == 'POSITIONAL'
        print(f"Template é posicional: {is_positional}")
        
        # Processar cada linha
        for idx, row in df.iterrows():
            phone = str(row['telefone'])
            # Usar o método de formatação de telefone
            phone = sender.format_phone_number(phone)
            
            # Construir parâmetros
            parameters = []
            
            # Se for posicional, precisamos garantir a ordem correta
            if is_positional:
                # Para parâmetros posicionais, a ordem é crítica (1, 2, 3...)
                for i in range(1, 10):  # Assumindo no máximo 9 parâmetros
                    param_key = str(i)
                    if param_key not in params_config:
                        break
                    
                    config = params_config[param_key]
                    csv_column = config.get('csv_column', '').strip().lower()
                    default_value = config.get('default_value', '')
                    
                    # Se a coluna CSV está especificada e existe no DataFrame
                    if csv_column and csv_column in df.columns:
                        value = str(row[csv_column])
                    else:
                        # Usar valor padrão
                        value = default_value
                    
                    # Adicionar como um parâmetro separado!
                    parameters.append({
                        "type": "text",
                        "text": str(value)
                    })
            else:
                # Para parâmetros nomeados
                for param_name, config in params_config.items():
                    csv_column = config.get('csv_column', '').strip().lower()
                    default_value = config.get('default_value', '')
                    
                    # Se a coluna CSV está especificada e existe no DataFrame
                    if csv_column and csv_column in df.columns:
                        value = str(row[csv_column])
                    else:
                        value = default_value
                    
                    parameters.append({
                        "type": "text",
                        "text": str(value)
                    })
            
            # Debug para verificar parâmetros
            print(f"Parâmetros para {phone}: {parameters}")
            
            # Enviar mensagem
            print(f"Enviando mensagem para {phone} (linha {idx+1}/{len(df)})")
            try:
                sender.send_dynamic_template_message(
                    to=phone,
                    template_name=template_name,
                    parameters=parameters
                )
                # Pequena pausa para evitar limites de taxa da API
                time.sleep(1)
            except Exception as e:
                print(f"Erro ao enviar para {phone}: {str(e)}")
    
    except Exception as e:
        print(f"Erro ao processar arquivo CSV: {str(e)}")
        raise
 
def process_csv_and_send_messages(csv_path, template_name, progress_callback=None, column_mapping=None):
    """
    Processa um arquivo CSV e envia mensagens usando um template.
   
    Args:
        csv_path (str): Caminho para o arquivo CSV
        template_name (str): Nome do template a ser usado
        progress_callback (callable, opcional): Função para reportar progresso
       
    Returns:
        dict: Estatísticas do processamento
    """
    results = {
        'success': 0,
        'error': 0,
        'error_log': []
    }
   
    try:
        # Tentar primeiro com ponto e vírgula (padrão brasileiro)
        try:
            df = pd.read_csv(csv_path, sep=';')
        except:
            # Se falhar, tentar com vírgula
            df = pd.read_csv(csv_path)
       
        # Identificar a coluna de telefone (deve ser 'telefone')
        if 'telefone' not in df.columns:
            raise ValueError("O CSV deve ter uma coluna chamada 'telefone'")
       
        phone_column = 'telefone'
       
        # Verificar colunas necessárias com base no template
        template_name_lower = template_name.lower()
       
        if "primiero_contato_consignado" in template_name_lower:
            # Verificar se as colunas necessárias existem
            required_columns = ['nome', 'empresa', 'valor']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"O CSV deve ter uma coluna '{col}' para o template {template_name}")
       
        elif "oferta_inss" in template_name_lower:
            # Verificar se a coluna 'nome' existe
            if 'nome' not in df.columns:
                raise ValueError(f"O CSV deve ter uma coluna 'nome' para o template {template_name}")
       
        total_rows = len(df)
        sender = WhatsAppSender()
       
        for index, row in df.iterrows():
            try:
                # Usar o método de formatação de telefone ao invés de fazer manualmente
                phone = sender.format_phone_number(str(row[phone_column]))
               
                # Preparar parâmetros de acordo com o template
                parameters = []
               
                if "primiero_contato_consignado" in template_name_lower:
                    # Template com 3 variáveis: nome, empresa, valor
                    parameters = [
                        {"type": "text", "text": str(row['nome'])},
                        {"type": "text", "text": str(row['empresa'])},
                        {"type": "text", "text": str(row['valor'])}
                    ]
               
                elif "oferta_inss" in template_name_lower:
                    # Template com 1 variável nomeada: nome
                    # Modificar o formato dos parâmetros para template NAMED
                    parameters = {"nome": str(row['nome'])}
               
                else:
                    # Template genérico - usar todas as colunas exceto telefone
                    for col in df.columns:
                        if col != phone_column:
                            parameters.append({"type": "text", "text": str(row[col])})
               
                # Enviar a mensagem usando o formato original que funcionava
                response = sender.send_template_message(
                    to=phone,
                    template=template_name,  # Use o nome do parâmetro que funcionava antes
                    parameters=parameters
                )
               
                # Verificar resultado
                if response and 'messages' in response and len(response['messages']) > 0:
                    results['success'] += 1
                else:
                    results['error'] += 1
                    results['error_log'].append(f"Falha ao enviar para {phone}: Resposta inválida")
               
                # Reportar progresso
                if progress_callback:
                    status = f"Enviado para {phone}"
                    progress_callback(index + 1, total_rows, status)
               
                # Pausa para evitar limitações de API
                time.sleep(1)
           
            except Exception as e:
                results['error'] += 1
                results['error_log'].append(f"Erro ao processar linha {index+1}: {str(e)}")
               
                if progress_callback:
                    progress_callback(index + 1, total_rows, f"Erro: {str(e)}")
   
    except Exception as e:
        results['error'] += 1
        results['error_log'].append(f"Erro ao processar CSV: {str(e)}")
   
    return results


if __name__ == '__main__':
    sender = WhatsAppSender()
    result = sender.send_template_message(
        to="5561999999999",
        nome="João",
        empresa="Empresa XYZ",
        valor="1000"
    )
    print(f"Resultado do teste: {result}")
