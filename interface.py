import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from datetime import datetime
import sqlite3
from database import get_db_connection
import threading
import queue
import emoji
import shutil
import os
import time
import json
import pandas as pd
from tkinter import messagebox
from whatsapp_sender import process_csv_and_send_messages, WhatsAppSender, process_csv_with_dynamic_template
from PIL import Image, ImageTk
import sv_ttk  # Precisa instalar: pip install sv-ttk
import webbrowser

# Configurações de cores e estilos
COLORS = {
    "primary": "#128C7E",       # Verde WhatsApp
    "light_primary": "#25D366", # Verde claro WhatsApp
    "secondary": "#075E54",     # Verde escuro WhatsApp
    "bg_gray": "#F5F5F5",       # Cinza para background
    "received_msg": "#FFFFFF",  # Branco para mensagens recebidas
    "sent_msg": "#DCF8C6",      # Verde claro para mensagens enviadas
    "text_gray": "#4A4A4A",     # Cinza para texto
    "divider": "#E1E1E1",       # Cinza para divisores
    "unread_bg": "#E8F5E9"      # Verde muito claro para destacar não lidas
}

class EmojiSelector(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Selecionar Emoji")
        self.geometry("900x700")
        self.configure(bg=COLORS["bg_gray"])
        
        # Maximizar a janela
        self.state('zoomed')  # Para Windows

        # Adicionar ícone e estilo à janela
        self.iconbitmap("assets/emoji_icon.ico") if os.path.exists("assets/emoji_icon.ico") else None
        
        self.emoji_font = ("Segoe UI Emoji", 24)
        
        self.common_emojis = [
            "😀", "😃", "😄", "😁", "😅", "😂", "🤣", "😊", "😇", "🙂", "🙃",
            "😉", "😌", "😍", "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜",
            "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔",
            "😟", "😕", "🙁", "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭",
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💯", "✨",
            "👍", "👎", "👏", "🙌", "👋", "🤝", "💪", "🙏"
        ]
        
        # Adicionar título
        title_label = tk.Label(self, text="Selecione um emoji", font=("Segoe UI", 14, "bold"), 
                              bg=COLORS["bg_gray"], fg=COLORS["primary"])
        title_label.pack(pady=(10, 5))
        
        self.frame = ttk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.frame, bg=COLORS["bg_gray"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical",
                                      command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Organizar emojis em grade
        row = 0
        col = 0
        for emoji_char in self.common_emojis:
            btn = tk.Button(self.scrollable_frame,
                           text=emoji_char,
                           font=self.emoji_font,
                           width=2,
                           height=1,
                           cursor="hand2",
                           relief="flat",
                           background="white",
                           command=lambda e=emoji_char: self.select_emoji(e))
            btn.grid(row=row, column=col, padx=4, pady=4)
            
            # Efeitos de hover
            btn.bind("<Enter>", lambda e, btn=btn: btn.config(background="#f0f0f0"))
            btn.bind("<Leave>", lambda e, btn=btn: btn.config(background="white"))
            
            col += 1
            if col > 7:
                col = 0
                row += 1
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Adicionar barra de pesquisa
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.focus_set()

    def select_emoji(self, emoji_char):
        self.callback(emoji_char)
        self.destroy()

class WhatsAppInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp API - Interface Moderna")
        self.root.geometry("1200x700")
        self.root.minsize(800, 600)
        self.status_bar = ttk.Label(self.root, text="Pronto", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.style = ttk.Style()
        self.style.configure("Send.TButton", background=COLORS["primary"], foreground="black")
        self.style.configure("Toolbar.TButton", background=COLORS["primary"], foreground="black")

        # Aplicar tema moderno
        sv_ttk.set_theme("light")
        
        # Configurar ícone da aplicação
        if os.path.exists("assets/whatsapp_icon.ico"):
            self.root.iconbitmap("assets/whatsapp_icon.ico")
        
        self.current_conversation = None
        
        self.attachments_dir = "attachments"
        if not os.path.exists(self.attachments_dir):
            os.makedirs(self.attachments_dir)
        
        self.message_queue = queue.Queue()
        self.current_attachment = None
        
        # Configurando estilo personalizado para a aplicação
        self.style = ttk.Style()
        self.style.configure("TFrame", background=COLORS["bg_gray"])
        self.style.configure("TLabel", background=COLORS["bg_gray"], foreground=COLORS["text_gray"])
        self.style.configure("TButton", background=COLORS["primary"], foreground="white")
        
        # Criar menu principal
        self.create_menu()
        
        # Configurar layout principal
        self.setup_main_layout()
        self.load_initial_messages()
        
        self.update_thread = threading.Thread(target=self.check_new_messages, daemon=True)
        self.update_thread.start()
        
        self.process_message_queue()
        
        # Iniciar verificação periódica de arquivo flag
        self.root.after(1000, self.check_new_messages_flag)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Pronto", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_menu(self):
        """Criar menu principal da aplicação"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # Menu Arquivo
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(label="Envio em Massa", command=self.open_bulk_send)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.root.quit)
        
        # Menu Ferramentas
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Ferramentas", menu=tools_menu)
        tools_menu.add_command(label="Configurações", command=self.show_settings)
        tools_menu.add_command(label="Exportar Conversas", command=self.export_conversations)
        
        # Menu Ajuda
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Manual do Usuário", command=lambda: webbrowser.open("https://docs.example.com/whatsapp-api"))
        help_menu.add_command(label="Sobre", command=self.show_about)

    def setup_main_layout(self):
        # Container principal
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Barra de ferramentas
        toolbar = ttk.Frame(main_container, style="Toolbar.TFrame", height=40)
        toolbar.pack(fill=tk.X, pady=(0, 2))
        
        # Botões da barra de ferramentas com ícones
        self.create_toolbar_button(toolbar, "Novo Chat", self.new_chat, 0)
        self.create_toolbar_button(toolbar, "Envio em Massa", self.open_bulk_send, 1)
        self.create_toolbar_button(toolbar, "Atualizar", self.refresh_conversations, 2)
        
        # Painel principal com divisor
        self.main_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Painéis esquerdo e direito 
        self.left_frame = ttk.Frame(self.main_paned, style="LeftPanel.TFrame")
        self.main_paned.add(self.left_frame, weight=1)

        self.right_frame = ttk.Frame(self.main_paned, style="RightPanel.TFrame")
        self.main_paned.add(self.right_frame, weight=2)

        self.setup_left_frame()
        self.setup_right_frame()

    def create_toolbar_button(self, parent, text, command, position):
        """Criar botão para a barra de ferramentas"""
        btn = ttk.Button(parent, text=text, command=command, style="Accent.TButton")
        btn.pack(side=tk.LEFT, padx=5, pady=5)
        return btn

    def setup_left_frame(self):
        # Cabeçalho do painel esquerdo
        header_frame = ttk.Frame(self.left_frame, style="Header.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        header_label = ttk.Label(header_frame, text="Conversas", 
                               font=("Segoe UI", 12, "bold"), 
                               foreground=COLORS["secondary"])
        header_label.pack(side=tk.LEFT, padx=10, pady=10)

        # Campo de busca com ícone
        search_frame = ttk.Frame(self.left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.search_var = tk.StringVar()
        search_icon_label = ttk.Label(search_frame, text="🔍")
        search_icon_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, padx=(5, 5), expand=True)
        self.search_var.trace('w', self.filter_conversations)

        # Lista de conversas com estilo personalizado
        self.conversation_frame = ttk.Frame(self.left_frame)
        self.conversation_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.conv_scrollbar = ttk.Scrollbar(self.conversation_frame)
        self.conv_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Adaptar a listbox para parecer mais moderna
        self.conversation_list = tk.Listbox(
            self.conversation_frame,
            yscrollcommand=self.conv_scrollbar.set,
            font=("Segoe UI", 10),
            bg="white",
            fg=COLORS["text_gray"],
            selectbackground=COLORS["primary"],
            selectforeground="white",
            highlightthickness=0,
            bd=1,
            relief=tk.SOLID,
            activestyle="none"
        )
        self.conversation_list.pack(fill=tk.BOTH, expand=True)
        self.conv_scrollbar.config(command=self.conversation_list.yview)
        self.conversation_list.bind('<<ListboxSelect>>', self.on_select_conversation)
        
        # Botão de novo chat
        new_chat_button = ttk.Button(
            self.left_frame, 
            text="Nova Conversa", 
            command=self.new_chat,
            style="Accent.TButton"
        )
        new_chat_button.pack(fill=tk.X, padx=5, pady=5)

    def setup_right_frame(self):
        # Cabeçalho da conversa
        self.chat_header = ttk.Frame(self.right_frame, style="ChatHeader.TFrame")
        self.chat_header.pack(fill=tk.X, pady=(0, 2))
        
        # Adicionar borda inferior ao cabeçalho
        self.chat_header.configure(borderwidth=1, relief="solid")
        
        self.contact_photo = ttk.Label(self.chat_header, text="👤", font=("Segoe UI Emoji", 16))
        self.contact_photo.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.chat_title = ttk.Label(
            self.chat_header, 
            text="Selecione uma conversa", 
            font=("Segoe UI", 12, "bold"),
            foreground=COLORS["secondary"]
        )
        self.chat_title.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Área de mensagens com estilo melhorado
        self.messages_frame = ttk.Frame(self.right_frame)
        self.messages_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar para mensagens
        messages_scrollbar = ttk.Scrollbar(self.messages_frame)
        messages_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Área de texto para mensagens com visual melhorado
        self.messages_area = tk.Text(
            self.messages_frame, 
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg="white",
            bd=1,
            relief=tk.SOLID,
            highlightthickness=0,
            yscrollcommand=messages_scrollbar.set,
            state=tk.DISABLED
        )
        self.messages_area.pack(fill=tk.BOTH, expand=True)
        messages_scrollbar.config(command=self.messages_area.yview)
        
        # Configurar as tags para estilização das mensagens
        self.messages_area.tag_configure("sent", justify="right")
        self.messages_area.tag_configure("received", justify="left")
        self.messages_area.tag_configure(
            "sent_bubble",
            background=COLORS["sent_msg"],
            relief="solid",
            borderwidth=1,
            lmargin1=50,
            rmargin=20
        )
        self.messages_area.tag_configure(
            "received_bubble",
            background=COLORS["received_msg"],
            relief="solid",
            borderwidth=1,
            lmargin1=20,
            rmargin=50
        )
        self.messages_area.tag_configure(
            "timestamp_sent",
            justify="right",
            foreground="gray",
            spacing1=10,
            font=("Segoe UI", 8)
        )
        self.messages_area.tag_configure(
            "timestamp_received",
            justify="left",
            foreground="gray",
            spacing1=10,
            font=("Segoe UI", 8)
        )
        
        # Separador visual
        ttk.Separator(self.right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)

        # Área de entrada de mensagens com design moderno
        self.input_frame = ttk.Frame(self.right_frame, style="InputFrame.TFrame")
        self.input_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Botão de emoji com visual melhorado
        self.emoji_button = tk.Button(
            self.input_frame,
            text="😊",
            font=("Segoe UI Emoji", 16),
            width=2,
            height=1,
            cursor="hand2",
            relief="flat",
            background="white",
            foreground="black", 
            activebackground=COLORS["bg_gray"],
            command=self.show_emoji_selector
        )
        self.emoji_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.emoji_button.bind("<Enter>", lambda e: self.emoji_button.config(background="#f0f0f0"))
        self.emoji_button.bind("<Leave>", lambda e: self.emoji_button.config(background="white"))

        # Botão de anexo com visual melhorado
        self.attach_button = tk.Button(
            self.input_frame,
            text="📎",
            font=("Segoe UI Emoji", 16),
            width=2,
            height=1,
            cursor="hand2",
            relief="flat",
            background="white",
            foreground="black",
            activebackground=COLORS["bg_gray"],
            command=self.attach_file
        )
        self.attach_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.attach_button.bind("<Enter>", lambda e: self.attach_button.config(background="#f0f0f0"))
        self.attach_button.bind("<Leave>", lambda e: self.attach_button.config(background="white"))

        # Campo de entrada com visual melhorado
        entry_frame = ttk.Frame(self.input_frame, style="EntryFrame.TFrame")
        entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.message_entry = ttk.Entry(
            entry_frame,
            font=("Segoe UI", 10),
            style="Message.TEntry"
        )
        self.message_entry.pack(fill=tk.BOTH, expand=True)

        # Botão de enviar com visual melhorado
        self.send_button = ttk.Button(self.input_frame, text="Enviar", 
                            command=self.send_message,
                            style="Accent.TButton")
        self.send_button.pack(side=tk.RIGHT)

        # Vincular tecla Enter para enviar mensagem
        self.message_entry.bind("<Return>", lambda e: self.send_message())

        # Indicador de anexo
        self.attachment_frame = ttk.Frame(self.right_frame, style="Attachment.TFrame")
        self.attachment_frame.pack(fill=tk.X, padx=5)
        
        self.attachment_label = ttk.Label(
            self.attachment_frame, 
            text="",
            font=("Segoe UI", 9),
            foreground=COLORS["primary"]
        )
        self.attachment_label.pack(side=tk.LEFT, fill=tk.X)
        
        # Botão para remover anexo
        self.clear_attachment_button = ttk.Button(
            self.attachment_frame,
            text="❌",
            width=2,
            command=self.clear_attachment,
            style="Accent.TButton"
        )


        # O botão só será exibido quando houver um anexo

    def clear_attachment(self):
        """Remover anexo atual"""
        self.current_attachment = None
        self.attachment_label.config(text="")
        self.clear_attachment_button.pack_forget()
        
    def show_emoji_selector(self):
        def add_emoji(emoji_char):
            current_text = self.message_entry.get()
            cursor_position = self.message_entry.index(tk.INSERT)
            new_text = current_text[:cursor_position] + emoji_char + current_text[cursor_position:]
            self.message_entry.delete(0, tk.END)
            self.message_entry.insert(0, new_text)
            self.message_entry.icursor(cursor_position + len(emoji_char))
            self.message_entry.focus()

        emoji_window = EmojiSelector(self.root, add_emoji)
        emoji_window.transient(self.root)
        emoji_window.grab_set()

    def attach_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecione um arquivo para anexar",
            filetypes=[
                ("Todos os arquivos", "*.*"),
                ("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Documentos", "*.pdf *.doc *.docx *.txt"),
            ]
        )
        
        if file_path:
            file_name = os.path.basename(file_path)
            destination = os.path.join(self.attachments_dir, file_name)
            
            try:
                shutil.copy2(file_path, destination)
                self.attachment_label.config(text=f"Anexo: {file_name}")
                self.current_attachment = destination
                
                # Mostrar botão para remover anexo
                self.clear_attachment_button.pack(side=tk.RIGHT)
                
                # Atualizar status
                self.status_bar.config(text=f"Arquivo anexado: {file_name}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao anexar arquivo: {str(e)}")
                self.status_bar.config(text=f"Erro ao anexar arquivo")

    def send_message(self):
        message = self.message_entry.get().strip()
        
        if not message and not self.current_attachment:
            return
            
        try:
            self.status_bar.config(text="Enviando mensagem...")
            
            sender = WhatsAppSender()
            selection = self.conversation_list.curselection()
            
            if not selection:
                return
                
            recipient = self.conversation_list.get(selection[0])
            
            if not recipient:
                return
            
            # Se tiver anexo, enviar primeiro
            if self.current_attachment:
                # Implementação do envio de anexo seria aqui
                pass
                
            result = sender.send_text_message(
                to=recipient,
                message=message
            )
            
            if not result or 'messages' not in result:
                self.status_bar.config(text="Erro ao enviar mensagem")
                return
                
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE messages
                SET answered = 1
                WHERE sender = ? AND recipient = ? AND answered = 0
            ''', (recipient, recipient))
            cursor.execute('''
                INSERT INTO messages (whatsapp_id, sender, recipient, message, message_type, status, answered)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (result['messages'][0]['id'], 'Você', recipient, message, 'text', 'sent', 1))
            
            conn.commit()
            conn.close()
            
            self.add_message("Você", message)
            self.message_entry.delete(0, tk.END)
            
            # Limpar anexo após envio
            self.clear_attachment()
            
            self.load_initial_messages()
            if recipient:
                # Procura o número na lista de conversas
                items = self.conversation_list.get(0, tk.END)
                if recipient in items:
                    index = items.index(recipient)
                    # Reseleciona a conversa atual
                    self.conversation_list.selection_clear(0, tk.END)
                    self.conversation_list.selection_set(index)
                    self.conversation_list.see(index)
                    # Mantém o cursor no campo de mensagem
                    self.message_entry.focus()
            
            self.status_bar.config(text="Mensagem enviada com sucesso")
            
        except Exception as e:
            self.status_bar.config(text=f"Erro ao enviar mensagem: {str(e)}")
            print(f"Erro ao enviar mensagem: {e}")
            import traceback
            print(f"Traceback completo: {traceback.format_exc()}")

    def add_message(self, sender, message):
        if sender == self.current_conversation or sender == "Você":
            self.messages_area.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M")
            
            # Adicionar espaço para margem e melhorar aparência dos balões
            self.messages_area.insert(tk.END, "\n")
            
            # Criar o balão da mensagem com visual mais moderno
            if sender == "Você":
                # Balão de mensagem enviada
                self.messages_area.insert(tk.END, f"{message}\n", ("sent", "sent_bubble"))
                self.messages_area.insert(tk.END, f"{timestamp} ✓\n", "timestamp_sent")
            else:
                # Balão de mensagem recebida
                self.messages_area.insert(tk.END, f"{message}\n", ("received", "received_bubble"))
                self.messages_area.insert(tk.END, f"{timestamp}\n", "timestamp_received")
            
            # Rolar para o final
            self.messages_area.see(tk.END)
            self.messages_area.config(state=tk.DISABLED)

    def on_select_conversation(self, event):
        selection = self.conversation_list.curselection()
        if selection:
            self.current_conversation = self.conversation_list.get(selection[0])
            self.chat_title.config(text=self.current_conversation)
            
            # Atualizar status e avatar (simulação)
            self.contact_photo.config(text="👤")
            self.status_bar.config(text=f"Conversa com {self.current_conversation} selecionada")
            
            # Marcar todas as mensagens deste contato como visualizadas
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE messages
                SET visualized = 1
                WHERE sender = ? AND sender != 'Você' AND visualized = 0
            ''', (self.current_conversation,))
            
            conn.commit()
            conn.close()
            
            # Remover destaque de fundo da conversa selecionada
            self.conversation_list.itemconfig(selection, {'bg': 'white'})
            
            # Carregar as mensagens com animação de carregamento
            self.messages_area.config(state=tk.NORMAL)
            self.messages_area.delete(1.0, tk.END)
            self.messages_area.insert(tk.END, "Carregando mensagens...", "timestamp_received")
            self.messages_area.config(state=tk.DISABLED)
            
            # Usar after para criar sensação de carregamento
            self.root.after(300, self.load_conversation_messages)
            
            # Focar no campo de entrada
            self.message_entry.focus()

    def load_conversation_messages(self):
        self.messages_area.config(state=tk.NORMAL)
        self.messages_area.delete(1.0, tk.END)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta modificada para buscar as mensagens corretamente
        cursor.execute('''
            SELECT sender, recipient, message, timestamp, status FROM messages
            WHERE (sender = ? AND recipient = '556199571754') OR (sender = 'Você' AND recipient = ?)
            ORDER BY timestamp ASC
        ''', (self.current_conversation, self.current_conversation))
        
        messages = cursor.fetchall()
        conn.close()
        
        # Adicionar efeito de "histórico" se houver muitas mensagens
        if len(messages) > 10:
            self.messages_area.insert(tk.END, "--- Início da conversa ---\n\n", "timestamp_received")
        
        for msg in messages:
            sender, recipient, message, timestamp, status = msg
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M")
            except:
                time_str = "12:00" # Fallback
            
            # Adicionar espaço para margem
            self.messages_area.insert(tk.END, "\n")
            
            # Modificação: verificar com base no status (received/sent)
            if sender == "Você" or status == "sent":
                self.messages_area.insert(tk.END, f"{message}\n", ("sent", "sent_bubble"))
                self.messages_area.insert(tk.END, f"{time_str} ✓\n", "timestamp_sent")
            else:
                self.messages_area.insert(tk.END, f"{message}\n", ("received", "received_bubble"))
                self.messages_area.insert(tk.END, f"{time_str}\n", "timestamp_received")
        
        self.messages_area.config(state=tk.DISABLED)
        self.messages_area.see(tk.END)
        
        # Atualizar status
        self.status_bar.config(text=f"Conversa com {self.current_conversation} carregada")

    def load_initial_messages(self):
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row  # Usar dicionários para resultados
        cursor = conn.cursor()
        
        # Consulta otimizada para identificar conversas com mensagens não lidas
        cursor.execute('''
            SELECT
                CASE
                    WHEN sender = 'Você' THEN recipient
                    ELSE sender
                END AS contact,
                SUM(CASE WHEN sender != 'Você' AND (visualized = 0 OR visualized IS NULL) THEN 1 ELSE 0 END) AS unread_count,
                MAX(timestamp) as last_timestamp,
                MAX(CASE WHEN sender != 'Você' THEN message ELSE "" END) as last_message
            FROM messages
            GROUP BY contact
            HAVING contact != 'Você'
            ORDER BY unread_count DESC, last_timestamp DESC
        ''')
        
        contacts = cursor.fetchall()
        conn.close()
        
        self.conversation_list.delete(0, tk.END)
        
        for contact in contacts:
            contact_name = contact['contact']
            unread_count = contact['unread_count']
            
            # CORREÇÃO: Tratamento seguro para acesso à coluna
            try:
                last_message = contact['last_message']
                if last_message:
                    last_message = last_message[:20]  # Limitar o tamanho
                else:
                    last_message = ''
            except (IndexError, KeyError):
                last_message = ''
            
            if contact_name != 'Você':
                # Adicionar indicador de mensagens não lidas
                display_text = contact_name
                if unread_count > 0:
                    display_text = f"{contact_name} ({unread_count})"
                
                self.conversation_list.insert(tk.END, contact_name)  # Guardar apenas o número
                
                # Índice do item adicionado
                index = self.conversation_list.size() - 1
                
                if unread_count > 0:
                    # Colorir conversas com mensagens não lidas
                    self.conversation_list.itemconfig(index, {'bg': '#D4E6F1'})  # Use a cor definida ou COLORS["unread_bg"]


    def update_interface_with_new_messages(self):
        """Atualiza a interface quando novas mensagens são detectadas."""
        self.status_bar.config(text="Atualizando conversas...")
        
        # Salvar a seleção atual
        selected_indices = self.conversation_list.curselection()
        selected_item = None
        if selected_indices:
            selected_item = self.conversation_list.get(selected_indices[0])
        
        # Recarregar a lista de conversas com efeito de carregamento
        self.root.after(100, lambda: self.load_initial_messages())
        
        # Restaurar a seleção
        def restore_selection():
            if selected_item:
                items = self.conversation_list.get(0, tk.END)
                if selected_item in items:
                    index = items.index(selected_item)
                    self.conversation_list.selection_clear(0, tk.END)
                    self.conversation_list.selection_set(index)
                    
                    # Se estiver na conversa ativa, recarregar mensagens
                    if selected_item == self.current_conversation:
                        self.load_conversation_messages()
            
            self.status_bar.config(text="Pronto")
                        
        self.root.after(300, restore_selection)

    def check_new_messages_flag(self):
        """Verifica se há um arquivo de flag indicando novas mensagens."""
        try:
            flag_file = "new_messages_flag.txt"
            if os.path.exists(flag_file):
                modified_time = os.path.getmtime(flag_file)
                current_time = time.time()
                
                # Se o arquivo foi modificado nos últimos 10 segundos
                if current_time - modified_time < 10:
                    # Atualizar interface
                    print("Flag de novas mensagens detectada!")
                    self.status_bar.config(text="Novas mensagens recebidas!")
                    self.update_interface_with_new_messages()
        except Exception as e:
            print(f"Erro ao verificar flag: {e}")
        
        # Verificar a cada 1 segundo
        self.root.after(1000, self.check_new_messages_flag)

    def check_new_messages(self):
        """Thread para verificar novas mensagens periodicamente."""
        last_check_time = datetime.now()
        
        while True:
            try:
                current_time = datetime.now()
                
                # Verificar se há novas mensagens desde a última verificação
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, whatsapp_id, sender, recipient, message, message_type,
                        status, timestamp, answered, visualized
                    FROM messages
                    WHERE sender != 'Você' AND timestamp > ?
                    ORDER BY timestamp ASC
                ''', (last_check_time.isoformat(),))
                
                new_messages = cursor.fetchall()
                conn.close()
                
                if new_messages:
                    print(f"Encontradas {len(new_messages)} novas mensagens!")
                    last_check_time = current_time
                    
                    # Importante: atualizar a interface na thread principal
                    self.root.after(0, self.update_interface_with_new_messages)
                
                # Verificar a cada 2 segundos
                time.sleep(2)
                
            except Exception as e:
                print(f"Erro ao verificar novas mensagens: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)

    def process_message_queue(self):
        """Processa mensagens da fila e atualiza a interface."""
        try:
            messages_processed = False
            while not self.message_queue.empty():
                msg = self.message_queue.get_nowait()
                messages_processed = True
                
                print(f"Processando nova mensagem de: {msg['sender']}")
                self.status_bar.config(text=f"Nova mensagem de {msg['sender']}")
                
                # Inserir mensagem no banco de dados
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Adicionado campo visualized=0 para marcar mensagens como não lidas
                cursor.execute('''
                    INSERT INTO messages (whatsapp_id, sender, recipient, message, message_type, status, timestamp, visualized)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (msg['id'], msg['sender'], 'Você', msg['message'], msg['type'], 'received', msg['timestamp'], 0))
                
                conn.commit()
                conn.close()
                
                # Atualizar interface se a conversa atual for com o remetente
                if self.current_conversation == msg['sender']:
                    self.add_message(msg['sender'], msg['message'])
                    
                    # Marcar como visualizada se estiver na conversa ativa
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE messages
                        SET visualized = 1
                        WHERE sender = ? AND visualized = 0
                    ''', (msg['sender'],))
                    conn.commit()
                    conn.close()
        
            # Somente atualizar a interface se processou mensagens
            if messages_processed:
                print("Mensagens processadas, atualizando interface...")
                self.load_initial_messages()
                
                # Se a conversa atual estiver aberta, manter selecionada
                if self.current_conversation:
                    items = self.conversation_list.get(0, tk.END)
                    if self.current_conversation in items:
                        index = items.index(self.current_conversation)
                        self.conversation_list.selection_clear(0, tk.END)
                        self.conversation_list.selection_set(index)

        except Exception as e:
            print(f"Erro ao processar fila de mensagens: {e}")
            import traceback
            traceback.print_exc()

        # Agendar próxima verificação
        self.root.after(500, self.process_message_queue)

    def filter_conversations(self, *args):
        search_term = self.search_var.get().lower()
        self.conversation_list.delete(0, tk.END)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT
                CASE
                    WHEN sender = 'Você' THEN recipient
                    ELSE sender
                END AS contact,
                MAX(CASE WHEN (sender != 'Você' AND visualized = 0) THEN 1 ELSE 0 END) AS has_unread
            FROM messages
            GROUP BY contact
            ORDER BY has_unread DESC, MAX(timestamp) DESC
        ''')
        
        contacts = cursor.fetchall()
        conn.close()
        
        for contact, has_unread in contacts:
            if contact != 'Você' and (not search_term or search_term in contact.lower()):
                self.conversation_list.insert(tk.END, contact)
                if has_unread == 1:
                    index = self.conversation_list.size() - 1
                    self.conversation_list.itemconfig(index, {'bg': COLORS["unread_bg"]})
        
        self.status_bar.config(text=f"Filtrando conversas: {search_term}")

    # Novos métodos para funcionalidades adicionais
    
    def new_chat(self):
        """Iniciar uma nova conversa"""
        def start_new_conversation():
            number = number_var.get().strip()
            if not number:
                messagebox.showwarning("Campo Vazio", "Digite um número válido com DDD")
                return
            
            # Verificar formato do número
            if not number.isdigit() or len(number) < 10:
                messagebox.showwarning("Formato Inválido", "O número deve conter pelo menos 10 dígitos (com DDD)")
                return
            
            # Fechar janela
            dialog.destroy()
            
            # Adicionar à lista se não existir
            numbers = self.conversation_list.get(0, tk.END)
            if number not in numbers:
                self.conversation_list.insert(0, number)
                self.conversation_list.itemconfig(0, {'bg': 'white'})
            
            # Selecionar a conversa
            self.conversation_list.selection_clear(0, tk.END)
            index = self.conversation_list.get(0, tk.END).index(number)
            self.conversation_list.selection_set(index)
            self.conversation_list.see(index)
            
            # Gatilho manual para carregar a conversa
            self.on_select_conversation(None)
        
        # Janela de diálogo
        dialog = tk.Toplevel(self.root)
        dialog.title("Nova Conversa")
        dialog.geometry("400x170")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centralizar
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="Iniciar Nova Conversa", 
                 font=("Segoe UI", 14, "bold"), 
                 foreground=COLORS["primary"]).grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")
        
        # Instruções
        ttk.Label(main_frame, text="Digite o número com DDD:").grid(row=1, column=0, sticky="w", pady=(0, 5))
        
        # Campo para número
        number_var = tk.StringVar()
        number_entry = ttk.Entry(main_frame, textvariable=number_var, width=30, font=("Segoe UI", 11))
        number_entry.grid(row=2, column=0, sticky="we", pady=(0, 15))
        number_entry.focus_set()
        
        # Botões
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky="e")
        
        ttk.Button(button_frame, text="Cancelar", 
                command=dialog.destroy,
                style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 10))

        
        ttk.Button(button_frame, text="Iniciar Conversa", 
                  style="Accent.TButton", 
                  command=start_new_conversation).pack(side=tk.LEFT)
        
        # Bind Enter key
        dialog.bind("<Return>", lambda event: start_new_conversation())

    def refresh_conversations(self):
        """Atualizar lista de conversas manualmente"""
        self.status_bar.config(text="Atualizando conversas...")
        
        # Efeito visual de carregamento
        current_selection = None
        if self.conversation_list.curselection():
            current_selection = self.conversation_list.get(self.conversation_list.curselection()[0])
        
        # Limpar lista atual
        self.conversation_list.delete(0, tk.END)
        self.conversation_list.insert(tk.END, "Carregando...")
        
        # Recarregar após breve delay para efeito visual
        def reload_conversations():
            self.conversation_list.delete(0, tk.END)
            self.load_initial_messages()
            
            # Restaurar seleção se aplicável
            if current_selection:
                items = self.conversation_list.get(0, tk.END)
                if current_selection in items:
                    index = items.index(current_selection)
                    self.conversation_list.selection_clear(0, tk.END)
                    self.conversation_list.selection_set(index)
                    self.conversation_list.see(index)
            
            self.status_bar.config(text="Conversas atualizadas")
            
        self.root.after(500, reload_conversations)

    def show_settings(self):
        """Exibir janela de configurações"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Configurações")
        settings_window.geometry("500x400")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Centralizar
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (settings_window.winfo_screenheight() // 2) - (height // 2)
        settings_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Notebook para abas
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Aba de configurações gerais
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="Geral")
        
        # Título
        ttk.Label(general_frame, text="Configurações Gerais", 
                 font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # Opções fictícias para demonstração
        ttk.Checkbutton(general_frame, text="Iniciar com o sistema").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Checkbutton(general_frame, text="Mostrar notificações").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Checkbutton(general_frame, text="Som de notificação").grid(row=3, column=0, sticky="w", pady=5)
        
        # Tema
        ttk.Label(general_frame, text="Tema:").grid(row=4, column=0, sticky="w", pady=(10, 5))
        theme_combo = ttk.Combobox(general_frame, values=["Claro", "Escuro", "Sistema"], state="readonly")
        theme_combo.current(0)
        theme_combo.grid(row=4, column=1, sticky="w", pady=(10, 5))
        
        # Aba de API
        api_frame = ttk.Frame(notebook, padding=10)
        notebook.add(api_frame, text="API")
        
        ttk.Label(api_frame, text="Configurações de API", 
                 font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        ttk.Label(api_frame, text="Token de API:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(api_frame, width=40).grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(api_frame, text="URL da API:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(api_frame, width=40).grid(row=2, column=1, sticky="w", pady=5)
        
        # Botões
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Na função show_settings, remova o estilo Accent.TButton do botão Cancelar
        ttk.Button(button_frame, text="Cancelar",
                command=settings_window.destroy).pack(side=tk.RIGHT, padx=(10, 0))

        
        ttk.Button(button_frame, text="Salvar", 
                  style="Accent.TButton").pack(side=tk.RIGHT)

    def export_conversations(self):
        """Exportar conversas para arquivo"""
        # Perguntar qual contato exportar
        export_window = tk.Toplevel(self.root)
        export_window.title("Exportar Conversas")
        export_window.geometry("450x400")
        export_window.transient(self.root)
        export_window.grab_set()
        
        main_frame = ttk.Frame(export_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Selecione os contatos para exportar:", 
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Lista de contatos com checkboxes
        contacts_frame = ttk.Frame(main_frame)
        contacts_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(contacts_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        contacts_listbox = tk.Listbox(contacts_frame, selectmode=tk.MULTIPLE, 
                                      yscrollcommand=scrollbar.set)
        contacts_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=contacts_listbox.yview)
        
        # Preencher com contatos
        contacts = self.conversation_list.get(0, tk.END)
        for contact in contacts:
            contacts_listbox.insert(tk.END, contact)
        
        # Formato de exportação
        format_frame = ttk.Frame(main_frame)
        format_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(format_frame, text="Formato:").pack(side=tk.LEFT)
        
        format_var = tk.StringVar(value="csv")
        ttk.Radiobutton(format_frame, text="CSV", variable=format_var, 
                       value="csv").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="JSON", variable=format_var, 
                       value="json").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="TXT", variable=format_var, 
                       value="txt").pack(side=tk.LEFT, padx=10)
        
        # Botões
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Na função export_conversations, remova o estilo Accent.TButton do botão Cancelar
        ttk.Button(buttons_frame, text="Cancelar",
                command=export_window.destroy).pack(side=tk.RIGHT, padx=(10, 0))

        
        def export_selected():
            selected_indices = contacts_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("Aviso", "Selecione pelo menos um contato para exportar.")
                return
                
            selected_contacts = [contacts_listbox.get(i) for i in selected_indices]
            export_format = format_var.get()
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{export_format}",
                filetypes=[(f"{export_format.upper()} files", f"*.{export_format}"), 
                          ("All files", "*.*")]
            )
            
            if file_path:
                try:
                    self.status_bar.config(text=f"Exportando conversas para {file_path}...")
                    
                    # Simulação de exportação
                    self.root.after(1000, lambda: self.status_bar.config(
                        text=f"Conversas exportadas com sucesso para {file_path}"))
                    
                    export_window.destroy()
                    messagebox.showinfo("Sucesso", f"Conversas exportadas com sucesso para {file_path}")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao exportar conversas: {str(e)}")
                    self.status_bar.config(text="Erro ao exportar conversas")
        
        ttk.Button(buttons_frame, text="Exportar", 
                  style="Accent.TButton", 
                  command=export_selected).pack(side=tk.RIGHT)

    def show_about(self):
        """Exibir janela Sobre"""
        about_window = tk.Toplevel(self.root)
        about_window.title("Sobre")
        about_window.geometry("400x300")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        main_frame = ttk.Frame(about_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo (placeholder)
        logo_label = ttk.Label(main_frame, text="📱", font=("Segoe UI Emoji", 36))
        logo_label.pack(pady=(0, 10))
        
        # Título da aplicação
        app_name = ttk.Label(main_frame, text="WhatsApp API", 
                            font=("Segoe UI", 18, "bold"),
                            foreground=COLORS["primary"])
        app_name.pack()
        
        # Versão
        version_label = ttk.Label(main_frame, text="Versão 2.0", font=("Segoe UI", 10))
        version_label.pack()
        
        # Descrição
        description = ttk.Label(main_frame, 
                              text="Interface moderna para envio e gerenciamento de mensagens via WhatsApp API.",
                              wraplength=350, justify="center")
        description.pack(pady=10)
        
        # Informação de copyright
        copyright_info = ttk.Label(main_frame, 
                                 text="© 2023. Todos os direitos reservados.",
                                 font=("Segoe UI", 8))
        copyright_info.pack(pady=(20, 0))
        
        # Botão OK
        ttk.Button(main_frame, text="OK", 
                command=about_window.destroy,
                style="Accent.TButton").pack(pady=(20, 0))

    def test_highlight(self):
        """Função de teste para destacar manualmente um número"""
        # Substituir pelo seu número de teste
        test_number = "SEU_NUMERO_AQUI"  # Coloque o número que você usou para enviar a mensagem de teste
        
        # Encontrar o número na lista
        items = self.conversation_list.get(0, tk.END)
        if test_number in items:
            index = items.index(test_number)
            # Destacar manualmente
            self.conversation_list.itemconfig(index, {'bg': COLORS["unread_bg"]})
            print(f"Número {test_number} destacado manualmente!")
        else:
            print(f"Número {test_number} não encontrado na lista!")

    def open_bulk_send(self):
        bulk_window = BulkSendWindow(self.root)  # Mudando de self para self.root
        bulk_window.transient(self.root)
        bulk_window.grab_set()
        bulk_window.focus_set()  # Adicionar foco na janela

class TemplateSelector(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Selecionar Template")
        self.geometry("700x550")
        self.configure(bg=COLORS["bg_gray"])
        
        # Para uso em sistemas Windows com ícone disponível
        if os.path.exists("assets/template_icon.ico"):
            self.iconbitmap("assets/template_icon.ico")
            
        self.selected_template = None
        
        # Frame principal
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        title_label = ttk.Label(main_frame, text="Selecione um Template", 
                              font=("Segoe UI", 14, "bold"),
                              foreground=COLORS["primary"])
        title_label.pack(pady=(0, 15), anchor="w")
        
        # Barra de pesquisa
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        search_icon = ttk.Label(search_frame, text="🔍")
        search_icon.pack(side="left", padx=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.focus_set()
        
        self.search_var.trace("w", self.filter_templates)
        
        # Layout dividido
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, pady=10)
        
        # Frame para lista de templates
        list_frame = ttk.LabelFrame(paned, text="Templates Disponíveis")
        paned.add(list_frame, weight=1)
        
        # Container para Listbox e scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Lista de templates com visual melhorado
        self.template_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 10),
            bg="white",
            fg=COLORS["text_gray"],
            selectbackground=COLORS["primary"],
            selectforeground="white",
            highlightthickness=0,
            bd=1,
            relief=tk.SOLID
        )
        self.template_listbox.pack(side="left", fill="both", expand=True)
        
        # Scrollbar para a lista
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.template_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.template_listbox.config(yscrollcommand=scrollbar.set)
        
        # Frame para detalhes do template
        details_frame = ttk.LabelFrame(paned, text="Detalhes do Template")
        paned.add(details_frame, weight=2)
        
        # Text widget estilizado para exibir detalhes
        self.details_text = tk.Text(
            details_frame, 
            wrap="word", 
            height=10,
            font=("Segoe UI", 10),
            bg="white",
            padx=10,
            pady=10,
            bd=1,
            relief=tk.SOLID,
            highlightthickness=0
        )
        self.details_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Botões
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", padx=5, pady=10)
        
        ttk.Button(buttons_frame, text="Cancelar", 
                command=self.destroy,
                style="Accent.TButton").pack(side="right", padx=5)

        ttk.Button(buttons_frame, text="Selecionar", command=self.select_template, 
                  style="Accent.TButton").pack(side="right", padx=5)
        
        # Status de carregamento
        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill="x")
        
        self.status_label = ttk.Label(
            self.status_frame, 
            text="Carregando templates...",
            foreground=COLORS["primary"]
        )
        self.status_label.pack(fill="x", padx=5, pady=5)
        
        # Carregamento com animação
        self.loading_bar = ttk.Progressbar(
            self.status_frame, 
            mode="indeterminate", 
            length=200
        )
        self.loading_bar.pack(fill="x", padx=5, pady=(0, 5))
        self.loading_bar.start()
        
        # Binding para atualizar detalhes quando um template é selecionado
        self.template_listbox.bind('<<ListboxSelect>>', self.show_template_details)
        self.template_listbox.bind('<Double-1>', lambda e: self.select_template())
        
        # Carregar templates da API
        self.after(500, self.load_templates_from_api)
        
    def filter_templates(self, *args):
        """Filtrar templates por texto de busca"""
        search_text = self.search_var.get().lower()
        self.template_listbox.delete(0, tk.END)
        
        for template in self.templates:
            name = template.get('name', '').lower()
            if search_text in name:
                self.template_listbox.insert(tk.END, template.get('name', 'Template sem nome'))
    
    def load_templates_from_api(self):
        """Carrega templates diretamente da API da Meta"""
        try:
            # Inicializar o sender
            sender = WhatsAppSender()
            
            # Obter templates da API
            self.templates = sender.get_available_templates()
            
            # Parar animação de carregamento
            self.loading_bar.stop()
            self.loading_bar.pack_forget()
            
            if not self.templates:
                self.status_label.config(text="Nenhum template encontrado na API.")
                return
                
            # Limpar a listbox
            self.template_listbox.delete(0, tk.END)
            
            # Preencher a listbox com templates da API
            for template in self.templates:
                self.template_listbox.insert(tk.END, template.get('name', 'Template sem nome'))
                
            self.status_label.config(text=f"{len(self.templates)} templates carregados.")
                
        except Exception as e:
            self.loading_bar.stop()
            self.loading_bar.pack_forget()
            self.status_label.config(text=f"Erro ao carregar templates: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao carregar templates da API: {str(e)}")
            self.templates = []
            
    def show_template_details(self, event):
        selection = self.template_listbox.curselection()
        if selection:
            index = selection[0]
            template = self.templates[index]
            
            # Limpa o texto atual
            self.details_text.config(state=tk.NORMAL)
            self.details_text.delete(1.0, tk.END)
            
            # Insere os detalhes com formatação
            self.details_text.insert(tk.END, "Nome: ", "label")
            self.details_text.insert(tk.END, f"{template.get('name', 'N/A')}\n\n", "value")
            
            self.details_text.insert(tk.END, "Status: ", "label")
            self.details_text.insert(tk.END, f"{template.get('status', 'N/A')}\n\n", "value")
            
            # Configurar tags para formatação
            self.details_text.tag_configure("label", font=("Segoe UI", 10, "bold"), foreground=COLORS["primary"])
            self.details_text.tag_configure("value", font=("Segoe UI", 10))
            self.details_text.tag_configure("header", font=("Segoe UI", 11, "bold"), foreground=COLORS["secondary"])
            
            # Mostrar os componentes
            components = template.get('components', [])
            if components:
                self.details_text.insert(tk.END, "Componentes:\n", "header")
                for comp in components:
                    comp_type = comp.get('type', 'N/A')
                    self.details_text.insert(tk.END, f"- Tipo: ", "label")
                    self.details_text.insert(tk.END, f"{comp_type}\n", "value")
                    
                    # Se for body ou header, pode ter parâmetros
                    if 'format' in comp:
                        self.details_text.insert(tk.END, f"  Formato: ", "label")
                        self.details_text.insert(tk.END, f"{comp.get('format')}\n", "value")
                    
                    if 'text' in comp:
                        self.details_text.insert(tk.END, f"  Texto: ", "label")
                        self.details_text.insert(tk.END, f"{comp.get('text')}\n", "value")
            
            self.details_text.config(state=tk.DISABLED)
    
    def select_template(self):
        selection = self.template_listbox.curselection()
        if selection:
            index = selection[0]
            self.selected_template = self.templates[index]
            self.destroy()
        else:
            messagebox.showwarning("Aviso", "Por favor, selecione um template da lista.")
    
    def get_selected_template(self):
        return self.selected_template

class BulkSendWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Envio em Massa")
        
        # Tentativa de maximizar em diferentes sistemas
        try:
            # Método para Windows
            if os.name == 'nt':
                self.state('zoomed')
            else:
                # Método para Linux/Mac
                self.attributes('-zoomed', True)
        except:
            # Método alternativo se os anteriores falharem
            width = self.winfo_screenwidth() - 50
            height = self.winfo_screenheight() - 50
            self.geometry(f"{width}x{height}+25+25")
        
        self.configure(bg=COLORS["bg_gray"])
        
        # Para uso em sistemas Windows com ícone disponível
        if os.path.exists("assets/bulk_send_icon.ico"):
            self.iconbitmap("assets/bulk_send_icon.ico")
        
        # Variáveis
        self.csv_file_path = tk.StringVar()
        self.selected_template = None
        
        # Componentes da interface
        self.create_widgets()

    def maximize_window(self):
        """Tenta maximizar a janela de várias maneiras"""
        try:
            # Tenta maximizar com state (Windows)
            self.state('zoomed')
        except:
            try:
                # Tenta maximizar com attributes (Linux)
                self.attributes('-zoomed', True)
            except:
                # Caso falhe, definir tamanho grande manualmente
                width = self.winfo_screenwidth() - 50
                height = self.winfo_screenheight() - 50
                self.geometry(f"{width}x{height}+25+25")
    
    def create_widgets(self):
        try:
            style = ttk.Style()
            style.configure("TButton",
                        background=COLORS["primary"],
                        foreground="black",
                        font=("Segoe UI", 10),
                        padding=6)
        
            style.map("TButton",
                    foreground=[('disabled', 'gray'), ('pressed', 'black'), ('active', 'black')],
                    background=[('disabled', '#cccccc'), ('pressed', COLORS["accent"]), ('active', COLORS["accent"])])
                    
            # Container principal
            main_frame = ttk.Frame(self, padding=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
        
            # Título
            title_label = ttk.Label(main_frame, text="Envio em Massa de Mensagens",
                                font=("Segoe UI", 16, "bold"),
                                foreground=COLORS["primary"])
            title_label.pack(anchor="w", pady=(0, 20))
        
            # Frame para selecionar arquivo CSV
            csv_frame = ttk.LabelFrame(main_frame, text="Arquivo CSV com Contatos", padding=10)
            csv_frame.pack(fill="x", pady=(0, 15))
        
            # Layout interno do frame CSV
            csv_content = ttk.Frame(csv_frame)
            csv_content.pack(fill="x")
        
            ttk.Label(csv_content, text="Arquivo:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ttk.Entry(csv_content, textvariable=self.csv_file_path, width=60).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            ttk.Button(csv_content, text="Procurar...",
            command=self.browse_csv,
            style="Accent.TButton").grid(row=0, column=2, padx=5, pady=5)
        
            # Dicas e instruções
            tip_label = ttk.Label(csv_content,
                                text="Dica: O arquivo CSV deve conter pelo menos as colunas 'telefone' e 'nome'.",
                                font=("Segoe UI", 9, "italic"),
                                foreground="gray")
            tip_label.grid(row=1, column=0, columnspan=3, sticky="w", padx=5)
        
            # Frame para template
            template_frame = ttk.LabelFrame(main_frame, text="Template da Mensagem", padding=10)
            template_frame.pack(fill="both", expand=True, pady=(0, 15))
        
            # Texto explicativo
            ttk.Label(template_frame,
                    text="Selecione um template pré-aprovado ou crie uma mensagem personalizada:").pack(anchor="w", pady=(0, 10))
        
            # Área para texto do template
            self.template_text = tk.Text(template_frame, wrap="word", height=10,
                                    font=("Segoe UI", 10),
                                    bg="white",
                                    padx=10,
                                    pady=10,
                                    bd=1,
                                    relief=tk.SOLID,
                                    highlightthickness=0)
            self.template_text.pack(fill="both", expand=True, padx=5, pady=5)
        
            # Barra de ferramentas para o template
            tools_frame = ttk.Frame(template_frame)
            tools_frame.pack(fill="x", padx=5, pady=5)
        
            # Indicação visual dos campos dinâmicos
            ttk.Label(tools_frame, text="Campos dinâmicos:").pack(side="left", padx=(0, 5))
            ttk.Button(tools_frame, text="{nome}",
                    command=lambda: self.insert_template_field("{nome}"),
                    style="Accent.TButton").pack(side="left", padx=2)
            ttk.Button(tools_frame, text="{empresa}",
                    command=lambda: self.insert_template_field("{empresa}"),
                    style="Accent.TButton").pack(side="left", padx=2)
            ttk.Button(tools_frame, text="{valor}",
                    command=lambda: self.insert_template_field("{valor}"),
                    style="Accent.TButton").pack(side="left", padx=2)
            
            # Botão de seleção de template à direita
            ttk.Button(tools_frame, text="Selecionar Template",
                    command=self.select_template,
                    style="Accent.TButton").pack(side="right", padx=5)
        
            # Frame para visualização prévia com abas
            preview_frame = ttk.LabelFrame(main_frame, text="Visualização e Configuração", padding=10)
            preview_frame.pack(fill="both", expand=True, pady=(0, 15))
        
            # Notebook para abas
            self.preview_notebook = ttk.Notebook(preview_frame)
            self.preview_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
            # Adicione esta linha para manter referência às abas
            self.tabs = {"data": None, "config": None, "send": None}

            # Aba de dados do CSV
            data_tab = ttk.Frame(self.preview_notebook)
            self.preview_notebook.add(data_tab, text="Dados do CSV")
            self.tabs["data"] = data_tab
        
            # Treeview para dados
            self.preview_tree = ttk.Treeview(data_tab, height=12, selectmode="browse")
            self.preview_tree.pack(fill="both", expand=True, padx=5, pady=5)

            # Scrollbars para o Treeview
            tree_x_scroll = ttk.Scrollbar(data_tab, orient="horizontal", command=self.preview_tree.xview)
            tree_x_scroll.pack(fill="x", side="bottom", padx=5)
        
            tree_y_scroll = ttk.Scrollbar(data_tab, orient="vertical", command=self.preview_tree.yview)
            tree_y_scroll.pack(fill="y", side="right", pady=5)
        
            self.preview_tree.configure(yscrollcommand=tree_y_scroll.set, xscrollcommand=tree_x_scroll.set)
        
            # Vincular evento de seleção do Treeview
            self.preview_tree.bind('<<TreeviewSelect>>', self.on_tree_select)

            # Adicionar mensagem inicial
            self.preview_tree["columns"] = ["mensagem"]
            self.preview_tree["show"] = "headings"
            self.preview_tree.heading("mensagem", text="Instruções")
            self.preview_tree.column("mensagem", width=400, anchor="center")
            self.preview_tree.insert("", "end", values=["Selecione um arquivo CSV clicando no botão 'Procurar...'"])

            # Aba de configurações
            config_tab = ttk.Frame(self.preview_notebook)
            self.preview_notebook.add(config_tab, text="Configurações de Envio")
            self.tabs["config"] = config_tab    

            # Opções de configuração
            config_options = ttk.Frame(config_tab, padding=10)
            config_options.pack(fill="both", expand=True)
        
            # Intervalo entre mensagens
            ttk.Label(config_options, text="Intervalo entre mensagens (segundos):").grid(
                row=0, column=0, sticky="w", pady=5, padx=5)
        
            self.interval_var = tk.StringVar(value="10")
            interval_spin = ttk.Spinbox(config_options, from_=1, to=60, textvariable=self.interval_var, width=5)
            interval_spin.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        
            # Limite diário
            ttk.Label(config_options, text="Limite diário de mensagens:").grid(
                row=1, column=0, sticky="w", pady=5, padx=5)
        
            self.limit_var = tk.StringVar(value="1000")
            limit_spin = ttk.Spinbox(config_options, from_=1, to=1000, textvariable=self.limit_var, width=5)
            limit_spin.grid(row=1, column=1, sticky="w", pady=5, padx=5)
        
            # Opções extras
            ttk.Checkbutton(config_options, text="Confirmar antes de cada envio").grid(
                row=2, column=0, columnspan=2, sticky="w", pady=5, padx=5)
        
            ttk.Checkbutton(config_options, text="Enviar relatório por e-mail ao finalizar").grid(
                row=3, column=0, columnspan=2, sticky="w", pady=5, padx=5)
        
            # Aba de envio (substituindo a aba "Informações")
            send_tab = ttk.Frame(self.preview_notebook)
            self.preview_notebook.add(send_tab, text="Enviar")  # Renomeado para "Enviar"
            self.tabs["send"] = send_tab

            # Criar um frame para centralizar o botão
            center_frame = ttk.Frame(send_tab)
            center_frame.pack(fill="both", expand=True)

            # Adicionar um frame interno para melhor posicionamento
            button_container = ttk.Frame(center_frame)
            button_container.place(relx=0.5, rely=0.5, anchor="center")

            # Texto de instrução acima do botão
            ttk.Label(
                button_container,
                text="Clique no botão abaixo para iniciar o envio das mensagens",
                font=("Segoe UI", 12, "bold"),
                foreground=COLORS["primary"]
            ).pack(pady=(0, 20))

            # Botão de envio grande e destacado
            self.send_button = tk.Button(
                button_container,
                text="ENVIAR MENSAGENS",
                command=self.send_messages,
                bg=COLORS["primary"],
                fg="white",
                font=("Segoe UI", 14, "bold"),
                padx=20,
                pady=15,
                cursor="hand2",
                relief="raised",
                bd=2
            )
            self.send_button.pack(pady=20)

            # Texto de status abaixo do botão
            ttk.Label(
                button_container,
                text="O botão será ativado quando um CSV e um template forem selecionados",
                font=("Segoe UI", 10),
                foreground="gray"
            ).pack(pady=(20, 0))

            # O botão começa desabilitado
            self.send_button.config(state="disabled")

            # Status e progresso
            self.status_frame = ttk.Frame(main_frame)
            self.status_frame.pack(fill="x", pady=(0, 10))
        
            self.status_label = ttk.Label(self.status_frame, text="Aguardando dados...")
            self.status_label.pack(side="left")
        
            self.progress_bar = ttk.Progressbar(self.status_frame, mode="determinate", length=200)
            self.progress_bar.pack(side="right")
        
            # Frame para botões de ação
            action_frame = ttk.Frame(main_frame)
            action_frame.pack(fill="x", pady=(0, 5))

            # Apenas o botão de fechar
            ttk.Button(
                action_frame,
                text="Fechar",
                command=self.destroy
            ).pack(side="right", padx=10, pady=10)
        
            # Contadores
            counter_frame = ttk.Frame(main_frame)
            counter_frame.pack(fill="x")
        
            self.counter_label = ttk.Label(counter_frame,
                                        text="0 contatos carregados | 0 mensagens na fila")
            self.counter_label.pack(side="left")

        except Exception as e:
            import traceback
            print(f"ERRO AO CRIAR WIDGETS: {e}")
            print(traceback.format_exc())
            messagebox.showerror("Erro", f"Erro ao criar a interface: {str(e)}")



    def on_tree_select(self, event):
        """Responde quando o usuário seleciona uma linha na tabela de dados"""
        pass

    def insert_template_field(self, field_text):
        """Insere um campo de template na posição atual do cursor"""
        self.template_text.insert(tk.INSERT, field_text)
        self.template_text.focus_set()
    
    def browse_csv(self):
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo CSV",
            filetypes=[("Arquivos CSV", "*.csv"), ("Todos os arquivos", "*.*")]
        )
        
        if file_path:
            self.csv_file_path.set(file_path)
            self.load_csv_preview(file_path)
            
            # Ativar botão de envio se também tiver um template
            if self.template_text.get("1.0", tk.END).strip() or self.selected_template:
                self.send_button.config(state="normal")
    
    def load_csv_preview(self, file_path):
        try:
            # Limpar a visualização atual
            for item in self.preview_tree.get_children():
                self.preview_tree.delete(item)
            
            # Atualizar status
            self.status_label.config(text="Carregando arquivo CSV...")
            
            # Tentar carregar com diferentes configurações
            df = None
            excecoes = []
            
            # Tentativa 1: Separador ponto e vírgula, codificação UTF-8
            try:
                df = pd.read_csv(file_path, sep=';', encoding='utf-8')
            except Exception as e:
                excecoes.append(f"Tentativa 1: {str(e)}")
                
                # Tentativa 2: Separador vírgula, codificação UTF-8
                try:
                    df = pd.read_csv(file_path, sep=',', encoding='utf-8')
                except Exception as e:
                    excecoes.append(f"Tentativa 2: {str(e)}")
                    
                    # Tentativa 3: Codificação Latin-1
                    try:
                        df = pd.read_csv(file_path, encoding='latin1')
                    except Exception as e:
                        excecoes.append(f"Tentativa 3: {str(e)}")
                        raise Exception("Não foi possível ler o arquivo CSV com nenhuma configuração")
            
            # Verificar se o DataFrame tem dados
            if df is None or df.empty:
                self.preview_tree["columns"] = ["mensagem"]
                self.preview_tree["show"] = "headings"
                self.preview_tree.heading("mensagem", text="Aviso")
                self.preview_tree.column("mensagem", width=400, anchor="center")
                self.preview_tree.insert("", "end", values=["O arquivo CSV está vazio"])
                return
            
            # Continuar com o código original para configurar as colunas e mostrar os dados...

            
            # Configura as colunas
            self.preview_tree["columns"] = list(df.columns)
            self.preview_tree["show"] = "headings"
            
            # Limpar cabeçalhos existentes e configurar novos
            for column in df.columns:
                self.preview_tree.heading(column, text=column)
                # Ajusta a largura com base no nome da coluna
                width = max(150, len(column) * 10)  # Aumentei a largura mínima
                self.preview_tree.column(column, width=width, minwidth=100)
            
            # Adicionar os dados (limitados a 10 linhas para preview)
            for i, row in df.head(10).iterrows():
                # Converter cada valor individualmente para string
                values = []
                for val in row:
                    # Tratamento para valores especiais
                    if pd.isna(val):
                        values.append("")
                    else:
                        values.append(str(val))
                
                # Inserir no Treeview
                self.preview_tree.insert("", "end", values=values)
            
            # Atualizar contadores
            total_rows = len(df)
            self.counter_label.config(text=f"{total_rows} contatos carregados | {total_rows} mensagens na fila")
            
            # Atualizar status
            self.status_label.config(text="Arquivo CSV carregado com sucesso")
            
            # Ativar botão de envio se um template estiver selecionado
            if self.selected_template or self.template_text.get("1.0", tk.END).strip():
                self.send_button.config(state="normal")
                
        except Exception as e:
            import traceback
            print(f"Erro ao carregar CSV: {str(e)}")
            print(traceback.format_exc())
            messagebox.showerror("Erro", f"Erro ao carregar o arquivo CSV: {str(e)}")
            self.status_label.config(text=f"Erro: {str(e)}")


    
    def select_template(self):
        template_selector = TemplateSelector(self)
        self.wait_window(template_selector)
        
        selected_template = template_selector.get_selected_template()
        if selected_template:
            self.selected_template = selected_template
            
            # Adicionar mapeamento específico para cada template
            if selected_template['name'] == 'primiero_contato_consignado':
                self.selected_template['field_mapping'] = {
                    "1": "nome",
                    "2": "empresa", 
                    "3": "valor"
                }
            elif selected_template['name'] == 'oferta_inss':
                self.selected_template['field_mapping'] = {
                    "nome": "nome"
                }
            
            # Atualizar a visualização do template
            self.template_text.delete(1.0, tk.END)
            
            # Mostrar o conteúdo do template selecionado
            components = selected_template.get('components', [])
            for comp in components:
                if comp.get('type') == 'BODY' and 'text' in comp:
                    self.template_text.insert(tk.END, comp.get('text', ''))
            
            # Ativar botão de envio se um CSV estiver carregado
            if self.csv_file_path.get():
                self.send_button.config(state="normal")
            
            # Já não precisamos mais atualizar a aba de simulação
            # self.update_preview_tab()  <- remova ou comente esta linha            
    
    def update_preview_tab(self):
        """Atualiza a aba de informações"""
        # Não precisa fazer nada aqui, a aba agora é estática
        pass

    
    def simulate_message(self):
        """Simula a mensagem com dados da linha selecionada do CSV"""
        selected_items = self.preview_tree.selection()
        if not selected_items:
            return  # Sair silenciosamente se não houver seleção
        
        try:
            item = selected_items[0]
            values = self.preview_tree.item(item, "values")
            
            # Obter colunas
            columns = self.preview_tree["columns"]
            
            # Criar dicionário de dados
            data = {}
            for i, col in enumerate(columns):
                if i < len(values):  # Verificar se há valores suficientes
                    data[col] = values[i]
            
            # Obter o template
            template_text = self.template_text.get("1.0", tk.END).strip()
            
            # Substituir campos
            for key, value in data.items():
                template_text = template_text.replace(f"{{{key}}}", str(value))
            
            # Mostrar na área de preview
            self.message_preview.config(state=tk.NORMAL)
            self.message_preview.delete(1.0, tk.END)
            self.message_preview.insert(tk.END, template_text)
            self.message_preview.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Erro ao simular mensagem: {str(e)}")
            # Não mostrar mensagem de erro para o usuário para não interromper o fluxo

    
    def send_messages(self):
        csv_path = self.csv_file_path.get()
        
        if not csv_path:
            messagebox.showwarning("Aviso", "Por favor, selecione um arquivo CSV.")
            return
        
        if not self.selected_template and not self.template_text.get("1.0", tk.END).strip():
            messagebox.showwarning("Aviso", "Por favor, selecione um template ou crie uma mensagem personalizada.")
            return
        
        # Confirmar o envio
        total_rows = self.counter_label.cget("text").split("|")[0].strip().split()[0]
        confirm = messagebox.askyesno(
            "Confirmar Envio", 
            f"Você está prestes a enviar mensagens para {total_rows} contatos.\n\n"
            f"Intervalo entre mensagens: {self.interval_var.get()} segundos\n"
            f"Limite diário: {self.limit_var.get()} mensagens\n\n"
            "Deseja continuar?"
        )
        
        if not confirm:
            return
        
        try:
            # Preparar UI para envio
            self.send_button.config(state="disabled")
            self.status_label.config(text="Iniciando envio de mensagens...")
            self.progress_bar["value"] = 0
            
            # Obter nome do template
            template_name = self.selected_template.get('name') if self.selected_template else None
            
            # Preparar configuração de parâmetros com mapeamento para colunas CSV
            params_config = {}
            
            # Se estiver usando um template predefinido
            if template_name:
                # Para parâmetros posicionais
                if self.selected_template.get('parameter_format') == 'POSITIONAL':
                    # Percorrer os componentes procurando parâmetros
                    components = self.selected_template.get('components', [])
                    
                    for comp in components:
                        if comp.get('type') == 'BODY':
                            # Ver se há exemplos para usar como default
                            example = comp.get('example', {})
                            default_values = []
                            
                            if 'body_text' in example and example['body_text']:
                                default_values = example['body_text'][0]  # Primeiro conjunto de exemplos
                            
                            # Mapear para colunas do CSV baseado em nomes comuns
                            csv_columns = {
                                '1': 'nome',
                                '2': 'empresa',
                                '3': 'valor'
                            }
                            
                            # Para cada parâmetro posicional
                            for i in range(1, 4):  # Assumindo até 3 parâmetros
                                param_key = str(i)
                                default_value = ""
                                
                                # Se tiver valor default, usar
                                if i <= len(default_values):
                                    default_value = default_values[i-1]
                                
                                params_config[param_key] = {
                                    'csv_column': csv_columns.get(param_key, ''),
                                    'default_value': default_value
                                }
                else:
                    # Para parâmetros nomeados, como no template 'oferta_inss'
                    params_config = {
                        'nome': {'csv_column': 'nome', 'default_value': 'Cliente'}
                    }
                
                print(f"Template selecionado: {template_name}")
                print(f"Configuração de parâmetros: {params_config}")
                
                # Iniciar envio em nova thread para não bloquear a UI
                interval = int(self.interval_var.get())
                limit = int(self.limit_var.get())
                
                # Configurar callback para atualizar progresso
                def update_progress(current, total, status_text):
                    progress = int((current / total) * 100)
                    self.progress_bar["value"] = progress
                    self.status_label.config(text=status_text)
                    self.counter_label.config(text=f"{total} contatos carregados | {total-current} mensagens restantes")
                    
                # Iniciar thread de envio
                thread = threading.Thread(
                    target=self.send_messages_thread,
                    args=(csv_path, template_name, params_config, interval, limit, update_progress)
                )
                thread.daemon = True
                thread.start()
                
            else:
                # Se estiver usando mensagem personalizada
                template_text = self.template_text.get("1.0", tk.END).strip()
                
                # Identificar campos dinâmicos no formato {campo}
                import re
                fields = re.findall(r'{(\w+)}', template_text)
                
                # Configurar parâmetros
                for field in fields:
                    params_config[field] = {
                        'csv_column': field,
                        'default_value': f'[{field}]'  # Valor padrão se não encontrar a coluna
                    }
                
                # Iniciar envio em nova thread
                interval = int(self.interval_var.get())
                limit = int(self.limit_var.get())
                
                # Configurar callback para atualizar progresso
                def update_progress(current, total, status_text):
                    progress = int((current / total) * 100)
                    self.progress_bar["value"] = progress
                    self.status_label.config(text=status_text)
                    self.counter_label.config(text=f"{total} contatos carregados | {total-current} mensagens restantes")
                
                # Iniciar thread de envio
                thread = threading.Thread(
                    target=self.send_custom_messages_thread,
                    args=(csv_path, template_text, params_config, interval, limit, update_progress)
                )
                thread.daemon = True
                thread.start()
            
        except Exception as e:
            self.send_button.config(state="normal")
            messagebox.showerror("Erro", f"Erro ao enviar mensagens: {str(e)}")
            self.status_label.config(text=f"Erro: {str(e)}")
    
    def send_messages_thread(self, csv_path, template_name, params_config, interval, limit, callback):
        """Thread para envio de mensagens com template da API"""
        try:
            # Usar a função existente
            result = process_csv_with_dynamic_template(
                csv_file=csv_path,
                template_name=template_name, 
                params_config=params_config
            )
            
            # Atualizar UI quando concluir
            def complete():
                self.status_label.config(text="Envio de mensagens concluído com sucesso!")
                self.send_button.config(state="normal")
                self.progress_bar["value"] = 100
                messagebox.showinfo("Sucesso", f"Envio de mensagens concluído com sucesso!\n\n{result}")
            
            # Usar after para atualizar na thread principal
            self.after(0, complete)
            
        except Exception as e:
            # Capturar a mensagem de erro aqui, antes de definir a função interna
            error_message = str(e)
            print(f"Erro ao enviar mensagens: {error_message}")
            
            # Atualizar UI em caso de erro
            def show_error():
                self.status_label.config(text=f"Erro: {error_message}")  # Usar a variável local
                self.send_button.config(state="normal")
                messagebox.showerror("Erro", f"Erro ao enviar mensagens: {error_message}")  # Usar a variável local
            
            self.after(0, show_error)

    def send_custom_messages_thread(self, csv_path, template_text, params_config, interval, limit, callback):
        """Thread para envio de mensagens personalizadas"""
        try:
            # Carregar CSV
            df = pd.read_csv(csv_path)
            total = len(df)
            
            sender = WhatsAppSender()
            sent_count = 0
            
            for index, row in df.iterrows():
                if sent_count >= limit:
                    break
                
                # Substituir campos no template
                message = template_text
                for field in params_config:
                    column = params_config[field]['csv_column']
                    default = params_config[field]['default_value']
                    
                    if column in row:
                        value = str(row[column])
                        message = message.replace(f"{{{field}}}", value)
                    else:
                        message = message.replace(f"{{{field}}}", default)
                
                # Obter número de telefone
                phone_column = 'telefone'
                if phone_column in row:
                    phone = str(row[phone_column])
                    
                    # Enviar mensagem
                    try:
                        sender.send_text_message(to=phone, message=message)
                        sent_count += 1
                        
                        # Atualizar progresso
                        status_text = f"Enviado para {phone} ({index+1}/{total})"
                        callback(index+1, total, status_text)
                        
                        # Intervalo entre mensagens
                        time.sleep(interval)
                    except Exception as send_error:
                        print(f"Erro ao enviar para {phone}: {str(send_error)}")
                        # Continuar para o próximo
            
            # Resultado final - IMPORTANTE: não usa variáveis do escopo externo
            def complete():
                self.status_label.config(text=f"Envio concluído. {sent_count} mensagens enviadas.")
                self.send_button.config(state="normal")
                self.progress_bar["value"] = 100
                messagebox.showinfo("Sucesso", f"Envio de mensagens concluído!\n\n{sent_count} de {total} mensagens enviadas com sucesso.")
            
            self.after(0, complete)
            
        except Exception as e:
            # IMPORTANTE: Salvar a mensagem de erro em uma variável local
            error_message = str(e)
            print(f"Erro ao enviar mensagens: {error_message}")
            
            # Função que não depende de 'e' do escopo externo
            def show_error():
                self.status_label.config(text=f"Erro: {error_message}")
                self.send_button.config(state="normal")
                messagebox.showerror("Erro", f"Erro ao enviar mensagens: {error_message}")
            
            self.after(0, show_error)

            
            # Resultado final - apenas uma versão desta função
            def complete():
                self.status_label.config(text=f"Envio concluído. {sent_count} mensagens enviadas.")
                self.send_button.config(state="normal")
                self.progress_bar["value"] = 100
                messagebox.showinfo("Sucesso", f"Envio de mensagens concluído!\n\n{sent_count} de {total} mensagens enviadas com sucesso.")
            
            self.after(0, complete)
            
        except Exception as e:
            error_message = str(e)
            print(f"Erro ao enviar mensagens: {error_message}")
            
            # Atualizar UI em caso de erro - apenas uma versão desta função
            def show_error():
                self.status_label.config(text=f"Erro: {error_message}")
                self.send_button.config(state="normal")
                messagebox.showerror("Erro", f"Erro ao enviar mensagens: {error_message}")
            
            self.after(0, show_error)

          
            # Resultado final
            def complete():
                self.status_label.config(text=f"Envio concluído. {sent_count} mensagens enviadas.")
                self.send_button.config(state="normal")
                self.progress_bar["value"] = 100
                messagebox.showinfo("Sucesso", f"Envio de mensagens concluído!\n\n{sent_count} de {total} mensagens enviadas com sucesso.")
            
            self.after(0, complete)
            
        except Exception as e:
            # Capturar a mensagem de erro aqui, antes de definir a função interna
            error_message = str(e)
            print(f"Erro ao enviar mensagens: {error_message}")
            
            # Atualizar UI em caso de erro
            def show_error():
                self.status_label.config(text=f"Erro: {error_message}")  # Usar a variável local
                self.send_button.config(state="normal")
                messagebox.showerror("Erro", f"Erro ao enviar mensagens: {error_message}")  # Usar a variável local
            
            self.after(0, show_error)



            
            # Resultado final
            def complete():
                self.status_label.config(text=f"Envio concluído. {sent_count} mensagens enviadas.")
                self.send_button.config(state="normal")
                self.progress_bar["value"] = 100
                messagebox.showinfo("Sucesso", f"Envio de mensagens concluído!\n\n{sent_count} de {total} mensagens enviadas com sucesso.")
            
            self.after(0, complete)
            
        except Exception as e:
            # Atualizar UI em caso de erro
            def show_error():
                self.status_label.config(text=f"Erro: {str(e)}")
                self.send_button.config(state="normal")
                messagebox.showerror("Erro", f"Erro ao enviar mensagens: {str(e)}")
            
            self.after(0, show_error)

# Definindo constantes para cores
COLORS = {
    "primary": "#128C7E",       # Verde WhatsApp
    "secondary": "#075E54",     # Verde escuro
    "accent": "#25D366",        # Verde claro
    "bg_gray": "#F0F2F5",       # Fundo cinza
    "text_gray": "#1A1D27",     # Texto cinza escuro
    "sent_msg": "#DCF8C6",      # Balão de mensagem enviada
    "received_msg": "#FFFFFF",  # Balão de mensagem recebida
    "unread_bg": "#DCFFC6",     # Fundo para conversas não lidas
}

def main():
    root = tk.Tk()
    root.title("WhatsApp API Client")
    
    # Maximizar a janela principal
    root.state('zoomed')  # Para Windows


    # Configurar estilos para ttk
    style = ttk.Style()
    style.configure("TFrame", background=COLORS["bg_gray"])
    style.configure("TLabel", background=COLORS["bg_gray"], foreground=COLORS["text_gray"])
    style.configure("TButton", background=COLORS["primary"], foreground="black")
    
    style.map("TButton",
    foreground=[('active', 'black'), ('disabled', 'gray')],
    background=[('active', COLORS["accent"])]
    )

    # Estilo para botão de acento
    style.configure("Accent.TButton", background=COLORS["accent"], foreground="white")
    
    # Estilo para o campo de entrada de mensagens
    style.configure("Message.TEntry", padding=10)
    
    # Estilo para cabeçalho de conversa
    style.configure("ChatHeader.TFrame", background=COLORS["secondary"])
    
    # Frame de entrada
    style.configure("InputFrame.TFrame", background="white", relief="solid", borderwidth=1)
    
    # Frame para nome da conversa
    style.configure("ContactName.TLabel", foreground="white", font=("Segoe UI", 12, "bold"))
    # Estilo para caixas de diálogo
    root.option_add('*Dialog.msg.font', 'Segoe UI 10')
    root.option_add('*Dialog.msg.background', COLORS["bg_gray"])
    root.option_add('*Dialog.msg.foreground', COLORS["text_gray"])
    root.option_add('*Dialog.Button.background', COLORS["accent"])
    root.option_add('*Dialog.Button.foreground', "white")

    app = WhatsAppInterface(root)
    
    # Centralizar a janela na tela
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()