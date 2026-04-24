TOOL_DECLARATIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Abre qualquer aplicativo instalado no sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Nome do app. Ex: 'chrome', 'spotify', 'vscode'."}
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "computer_control",
            "description": "Controla o PC: minimizar janelas, screenshot, bloquear tela, limpar lixeira, volume, status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "Acao: 'fechar', 'minimizar_tudo', 'print', 'bloqueio', 'limpar', 'status', 'volume', 'type', 'hotkey'."},
                    "nivel":  {"type": "integer", "description": "Volume 0-100 (só para action='volume')."},
                    "text":   {"type": "string",  "description": "Texto para digitar (action='type')."},
                    "keys":   {"type": "string",  "description": "Atalho de teclado ex: 'ctrl+c' (action='hotkey')."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cmd_control",
            "description": "Executa comandos de terminal. Use para scripts, criar arquivos, instalar pacotes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task":    {"type": "string", "description": "Descrição da tarefa em português. A IA gera o comando."},
                    "command": {"type": "string", "description": "Comando direto (opcional, substitui geração automática)."},
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Pesquisa na web e retorna resumo. Use para fatos, notícias, definições.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de pesquisa."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_control",
            "description": "Controla o navegador: abrir URL, pesquisar, clicar, preencher formulários.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "Acao: 'open', 'search', 'click', 'type', 'close_tab'."},
                    "url":    {"type": "string", "description": "URL para navegar (action='open')."},
                    "query":  {"type": "string", "description": "Termo para pesquisar (action='search')."},
                    "text":   {"type": "string", "description": "Texto para digitar (action='type')."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_video",
            "description": "Busca e reproduz o primeiro vídeo encontrado no YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Nome do vídeo, música ou canal."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_control",
            "description": "Controla o Spotify: tocar, pausar, próxima, anterior, playlist, favoritas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action":        {"type": "string", "description": "Acao: 'play', 'pause', 'proxima', 'anterior', 'favoritas'."},
                    "search_query":  {"type": "string", "description": "Música ou artista para buscar."},
                    "playlist_name": {"type": "string", "description": "Nome da playlist."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather_report",
            "description": "Clima atual e previsão de amanhã para uma cidade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city":     {"type": "string", "description": "Nome da cidade."},
                    "forecast": {"type": "string", "description": "'hoje' ou 'amanha'. Padrão: 'hoje'."},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Cria, lista ou remove alarmes e lembretes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op":     {"type": "string", "description": "'add', 'list' ou 'remove'. Padrão: 'add'."},
                    "hora":   {"type": "string", "description": "Horário HH:MM."},
                    "missao": {"type": "string", "description": "Descrição do lembrete."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "smart_home",
            "description": "Controla dispositivos inteligentes via SmartThings: TV, lâmpadas, tomadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device":     {"type": "string", "description": "Dispositivo: 'tv', 'lampada_sala', 'all_lights'."},
                    "action":     {"type": "string", "description": "'on', 'off', 'toggle', 'status'."},
                    "value":      {"type": "integer", "description": "Valor numérico (volume, brilho). Opcional."},
                    "capability": {"type": "string",  "description": "Capacidade SmartThings. Opcional."},
                },
                "required": ["device", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_controller",
            "description": "Gerencia arquivos: criar, ler, deletar, listar, backup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action":    {"type": "string",  "description": "'list', 'create_file', 'create_folder', 'delete', 'read', 'backup', 'disk'."},
                    "path":      {"type": "string",  "description": "Caminho ou atalho: 'desktop', 'downloads', etc."},
                    "name":      {"type": "string",  "description": "Nome do arquivo ou pasta."},
                    "content":   {"type": "string",  "description": "Conteúdo de texto (create_file)."},
                    "permanent": {"type": "boolean", "description": "Se true, deleta sem lixeira."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Salva informações sobre o usuário em memória persistente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "'preferences', 'personal', 'work', 'goals'."},
                    "key":      {"type": "string", "description": "Identificador. Ex: 'cidade_favorita'."},
                    "value":    {"type": "string", "description": "Valor a guardar."},
                },
                "required": ["category", "key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agent_task",
            "description": "Planeja e executa tarefas complexas multi-etapa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal":    {"type": "string", "description": "Objetivo em linguagem natural."},
                    "context": {"type": "string", "description": "Contexto adicional. Opcional."},
                },
                "required": ["goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "code_helper",
            "description": "Escreve, edita, depura e executa código Python, JS, Bash, PowerShell.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string",  "description": "O que o código deve fazer."},
                    "language":    {"type": "string",  "description": "'python', 'javascript', 'bash'. Padrão: 'python'."},
                    "code":        {"type": "string",  "description": "Código existente para editar (opcional)."},
                    "execute":     {"type": "boolean", "description": "Se true, executa imediatamente."},
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screen_analysis",
            "description": "Captura e analisa o que está na tela agora.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Pergunta sobre o conteúdo da tela. Opcional."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_ia_mode",
            "description": "Altera o modelo de IA em uso: ollama, gemini ou auto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "description": "'gemini', 'ollama' ou 'auto'."}
                },
                "required": ["mode"],
            },
        },
    },
]