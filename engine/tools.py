from .tools_mapper import EXECUTOR_FERRAMENTAS as DISPATCHER




TOOL_DECLARATIONS = [
    # ── SISTEMA ───────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Abre qualquer aplicativo instalado no sistema operacional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nome do aplicativo. Ex: 'chrome', 'spotify', 'vscode'.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "computer_control",
            "description": (
                "Controla o computador: minimizar janelas, fechar janela ativa, "
                "tirar screenshot, bloquear tela, limpar lixeira, ajustar volume, "
                "obter status do sistema (CPU, RAM, disco)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": (
                            "Ação a executar. Valores: 'fechar', 'minimizar_tudo', "
                            "'print', 'bloqueio', 'limpar', 'status', 'volume'."
                        ),
                    },
                    "nivel": {
                        "type": "integer",
                        "description": "Nível de volume (0–100). Usado apenas quando action='volume'.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Texto para digitar (quando action='type').",
                    },
                    "keys": {
                        "type": "string",
                        "description": "Atalho de teclado (ex: 'ctrl+c'). Quando action='hotkey'.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cmd_control",
            "description": (
                "Executa um comando de terminal (PowerShell no Windows, bash no Linux/Mac). "
                "Use para tarefas de sistema, scripts, criar arquivos, instalar pacotes, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Descrição da tarefa em português. A IA gera o comando adequado.",
                    },
                    "command": {
                        "type": "string",
                        "description": "Comando direto a executar (opcional, substitui geração automática).",
                    },
                },
                "required": ["task"],
            },
        },
    },
    # ── WEB & NAVEGADOR ───────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Pesquisa na web e retorna um resumo dos resultados. "
                "Use para qualquer pergunta factual, notícias, definições, pessoas, lugares."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de pesquisa.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_control",
            "description": (
                "Controla o navegador: abrir URL, pesquisar no Google, "
                "clicar em elementos, preencher formulários, fechar aba."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Ação: 'open', 'search', 'click', 'type', 'close_tab'.",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL completa para navegar (quando action='open').",
                    },
                    "query": {
                        "type": "string",
                        "description": "Termo para pesquisar (quando action='search').",
                    },
                    "text": {
                        "type": "string",
                        "description": "Texto para digitar no campo (quando action='type').",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_video",
            "description": "Abre o YouTube, pesquisa e reproduz automaticamente o primeiro vídeo encontrado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nome do vídeo, música ou canal a buscar.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    # ── MÍDIA / SPOTIFY ───────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "spotify_control",
            "description": (
                "Controla o Spotify: reproduzir música/artista, playlist, "
                "pausar, continuar, próxima faixa, faixa anterior, favoritas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": (
                            "Ação: 'play', 'pause', 'proxima', 'anterior', "
                            "'buscar', 'playlist', 'favoritas'."
                        ),
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Nome da música ou artista para buscar.",
                    },
                    "playlist_name": {
                        "type": "string",
                        "description": "Nome da playlist para reproduzir.",
                    },
                },
                "required": [],
            },
        },
    },
    # ── CLIMA ─────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "weather_report",
            "description": (
                "Retorna condição climática atual (temperatura, umidade, vento) "
                "e previsão para amanhã de uma cidade."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Nome da cidade. Padrão: Esteio.",
                    },
                    "forecast": {
                        "type": "string",
                        "description": "Tipo: 'hoje' ou 'amanha'. Padrão: 'hoje'.",
                    },
                },
                "required": ["city"],
            },
        },
    },
    # ── ALARMES & AGENDA ──────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Cria, lista ou remove alarmes e lembretes com hora e missão.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "description": "Operação: 'add' (criar), 'list' (listar), 'remove' (remover). Padrão: 'add'.",
                    },
                    "hora": {
                        "type": "string",
                        "description": "Horário no formato HH:MM. Ex: '07:30'.",
                    },
                    "missao": {
                        "type": "string",
                        "description": "Descrição do lembrete ou alarme.",
                    },
                    "repetir": {
                        "type": "boolean",
                        "description": "Se true, o alarme se repete diariamente.",
                    },
                },
                "required": [],
            },
        },
    },
    # ── SMART HOME ────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "smart_home",
            "description": (
                "Controla dispositivos domésticos inteligentes via SmartThings: "
                "TV Samsung, lâmpadas, tomadas, sensores. "
                "Use para comandos como 'liga a TV', 'apaga as luzes', 'liga a lâmpada da sala'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "description": (
                            "Dispositivo alvo. Exemplos: 'tv', 'lampada_sala', "
                            "'lampada_quarto', 'tomada_escritorio', 'all_lights'."
                        ),
                    },
                    "action": {
                        "type": "string",
                        "description": "Ação: 'on' (ligar), 'off' (desligar), 'toggle', 'status'.",
                    },
                    "value": {
                        "type": "integer",
                        "description": "Valor numérico (ex: volume 30, brilho 80). Opcional.",
                    },
                    "capability": {
                        "type": "string",
                        "description": "Capacidade SmartThings (ex: 'switch', 'audioVolume', 'switchLevel'). Opcional.",
                    },
                },
                "required": ["device", "action"],
            },
        },
    },
    # ── ARQUIVOS ──────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "file_controller",
            "description": (
                "Gerencia arquivos e pastas: criar, ler, deletar, organizar, "
                "fazer backup (zip), listar diretório, verificar espaço em disco."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": (
                            "Ação: 'list', 'create_file', 'create_folder', "
                            "'delete', 'read', 'organize', 'backup', 'disk'."
                        ),
                    },
                    "path": {
                        "type": "string",
                        "description": "Caminho ou atalho: 'desktop', 'downloads', 'documents', ou caminho completo.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Nome do arquivo ou pasta.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Conteúdo de texto (para create_file).",
                    },
                    "permanent": {
                        "type": "boolean",
                        "description": "Se true, deleta permanentemente (sem lixeira).",
                    },
                },
                "required": ["action"],
            },
        },
    },
    # ── MEMÓRIA PERSISTENTE ───────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": (
                "Salva informações importantes sobre o usuário em memória persistente. "
                "Use para guardar preferências, fatos pessoais, configurações, metas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Categoria: 'preferences', 'personal', 'work', 'goals', 'habits'.",
                    },
                    "key": {
                        "type": "string",
                        "description": "Identificador único da informação. Ex: 'cidade_favorita'.",
                    },
                    "value": {
                        "type": "string",
                        "description": "Valor a armazenar.",
                    },
                },
                "required": ["category", "key", "value"],
            },
        },
    },
    # ── PLANEJAMENTO ESTRATÉGICO ───────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "agent_task",
            "description": (
                "Planeja e executa tarefas complexas multi-etapa de forma autônoma. "
                "Use para objetivos que exigem várias ações sequenciais, como "
                "'organizar meu desktop', 'preparar ambiente de desenvolvimento', "
                "'pesquisar e resumir um tópico'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Objetivo completo em linguagem natural.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Contexto adicional relevante para a tarefa. Opcional.",
                    },
                },
                "required": ["goal"],
            },
        },
    },
    # ── CÓDIGO ────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "code_helper",
            "description": (
                "Escreve, edita, depura e executa código. "
                "Suporta Python, JavaScript, PowerShell, Bash e outros."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "O que o código deve fazer.",
                    },
                    "language": {
                        "type": "string",
                        "description": "Linguagem: 'python', 'javascript', 'powershell', 'bash'. Padrão: 'python'.",
                    },
                    "code": {
                        "type": "string",
                        "description": "Código existente para editar ou depurar (opcional).",
                    },
                    "execute": {
                        "type": "boolean",
                        "description": "Se true, executa o código gerado imediatamente.",
                    },
                },
                "required": ["description"],
            },
        },
    },
    # ── VISÃO COMPUTACIONAL ───────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "screen_analysis",
            "description": (
                "Captura e analisa o que está na tela agora. "
                "Use quando o usuário pedir para 'olhar a tela', 'ver o que está acontecendo', "
                "ou quando precisar de contexto visual para ajudar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Pergunta específica sobre o conteúdo da tela. Opcional.",
                    }
                },
                "required": [],
            },
        },
    },
    # ── ROTEAMENTO DE IA ──────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "switch_ia_mode",
            "description": (
                "Altera o modelo de IA em uso em tempo real. "
                "Use quando o usuário disser 'muda para ollama', 'usa o modelo local', "
                "'muda para gemini', 'usa ia local', 'troca a ia'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Modo desejado: 'gemini', 'ollama' ou 'auto'.",
                    }
                },
                "required": ["mode"],
            },
        },
    },
]
