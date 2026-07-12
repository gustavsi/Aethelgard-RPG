import queue
import threading
from engine.exceptions import EngineShutdownException

class UIAdapter:
    """
    Abstrai a entrada de dados do usuário (Terminal ou Web).
    Em modo Terminal, usa o input() nativo síncrono.
    """
    _local = threading.local()
    
    @classmethod
    def get_instance(cls):
        if not hasattr(cls._local, 'instance') or cls._local.instance is None:
            cls._local.instance = UIAdapter()
        return cls._local.instance
        
    @classmethod
    def set_instance(cls, instance):
        cls._local.instance = instance
        
    def emit(self, event) -> any:
        import os
        from engine.dto import NarrativeText, ChoiceRequested, ClearScreen, PressAnyKey, AsciiArt, SoundEffect
        if isinstance(event, ClearScreen):
            os.system('clear' if os.name == 'posix' else 'cls')
            return None
        elif isinstance(event, NarrativeText):
            print(event.content)
            return None
        elif isinstance(event, PressAnyKey):
            input(event.prompt)
            return None
        elif isinstance(event, ChoiceRequested):
            print(f"\n{event.prompt}")
            for k, v in event.options.items():
                print(f" {k} - {v}")
            while True:
                choice = input("> ").strip()
                if choice in event.options:
                    return choice
        elif isinstance(event, AsciiArt):
            print(event.art)
            return None
        elif isinstance(event, SoundEffect):
            print(f"\n 🔊 * {event.effect_id.upper()} * 🔊\n")
            return None
        return None

    def get_menu_choice(self, prompt: str, options: dict) -> str:
        from engine.dto import ChoiceRequested
        return self.emit(ChoiceRequested(prompt, options))

    def get_input(self, prompt: str) -> str:
        """Coleta entrada livre de texto."""
        return input(prompt)
        
    def press_any_key(self, prompt: str):
        """Pausa até o usuário interagir."""
        from engine.dto import PressAnyKey
        self.emit(PressAnyKey(prompt))
        
    def on_state_change(self, state):
        """Hook chamado quando o GameState é alterado (usado primariamente pela Web)."""
        pass

class WebUIAdapter(UIAdapter):
    """
    Adapter para o servidor FastAPI. Intercepta requisições de input síncronas da Engine
    e as suspende até que o WebSocket devolva uma resposta.
    """
    def __init__(self, ws_callback):
        self.input_queue = queue.Queue()
        self.shutdown_event = threading.Event()
        self.ws_callback = ws_callback  # Função assíncrona passada pelo server para enviar dados via WS
        self.last_state = None
        self.last_waiting_input = None

    def emit(self, event) -> any:
        from engine.dto import NarrativeText, ChoiceRequested, ClearScreen, PressAnyKey, AsciiArt, SoundEffect
        from engine.utils import strip_ansi
        
        if isinstance(event, ClearScreen):
            # Web client ignores clear screen natively
            return None
        elif isinstance(event, NarrativeText):
            payload = event.to_dict()
            payload["content"] = strip_ansi(payload["content"])
            self.ws_callback(payload)
            return None
        elif isinstance(event, PressAnyKey):
            if getattr(self, 'state', None):
                self.on_state_change(self.state)
            payload = event.to_dict()
            payload["prompt"] = strip_ansi(payload["prompt"])
            self.ws_callback(payload)
            return self._wait_for_input()
        elif isinstance(event, ChoiceRequested):
            if getattr(self, 'state', None):
                self.on_state_change(self.state)
            payload = event.to_dict()
            payload["prompt"] = strip_ansi(payload["prompt"])
            if "options" in payload:
                payload["options"] = {k: strip_ansi(v) for k, v in payload["options"].items()}
            self.ws_callback(payload)
            return self._wait_for_input()
        elif isinstance(event, AsciiArt):
            # Web client uses graphical background images, ignore ASCII art
            return None
        elif isinstance(event, SoundEffect):
            self.ws_callback(event.to_dict())
            return None
        return None

    def get_menu_choice(self, prompt: str, options: dict) -> str:
        from engine.dto import ChoiceRequested
        return self.emit(ChoiceRequested(prompt, options))

    def get_input(self, prompt: str) -> str:
        from engine.utils import strip_ansi
        if getattr(self, 'state', None):
            self.on_state_change(self.state)
        self.ws_callback({"type": "WAITING_INPUT", "prompt": strip_ansi(prompt)})
        return self._wait_for_input()

    def _wait_for_input(self) -> str:
        # Bloqueia a thread da Engine de forma segura, com polling rápido
        while not self.shutdown_event.is_set():
            try:
                # 0.1s timeout permite checar a flag de shutdown continuamente
                user_input = self.input_queue.get(timeout=0.1)
                return user_input
            except queue.Empty:
                continue
                
        # Se a flag foi ativada (WebSocket desconectou), encerra a thread
        raise EngineShutdownException("Web Client desconectou. Matando thread da Engine.")

    def press_any_key(self, prompt: str):
        from engine.dto import PressAnyKey
        self.emit(PressAnyKey(prompt))

    def on_state_change(self, state):
        self.ws_callback({"type": "STATE_UPDATE", "state": state.to_dict()})

def get_adapter() -> UIAdapter:
    return UIAdapter.get_instance()
