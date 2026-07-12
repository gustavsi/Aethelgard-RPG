class NarrativeText:
    def __init__(self, content: str):
        self.content = content
        
    def to_dict(self) -> dict:
        return {"type": "NARRATIVE_TEXT", "content": self.content}

class ChoiceRequested:
    def __init__(self, prompt: str, options: dict):
        self.prompt = prompt
        if isinstance(options, list):
            options_dict = {str(i + 1): opt for i, opt in enumerate(options)}
        else:
            options_dict = dict(options) if options else {}
        if not options_dict:
            options_dict = {"exit": "Voltar"}
        self.options = options_dict
        
    def to_dict(self) -> dict:
        return {"type": "WAITING_INPUT", "prompt": self.prompt, "options": self.options}

class ClearScreen:
    def to_dict(self) -> dict:
        return {"type": "CLEAR_SCREEN"}

class PressAnyKey:
    def __init__(self, prompt: str = "Pressione [ENTER] para continuar..."):
        self.prompt = prompt
        
    def to_dict(self) -> dict:
        return {"type": "WAITING_INPUT", "subtype": "PRESS_ANY_KEY", "prompt": self.prompt}

class AsciiArt:
    def __init__(self, art: str):
        self.art = art
        
    def to_dict(self) -> dict:
        return {"type": "ASCII_ART", "art": self.art}

class SoundEffect:
    def __init__(self, effect_id: str):
        self.effect_id = effect_id
        
    def to_dict(self) -> dict:
        return {"type": "SOUND_EFFECT", "effect_id": self.effect_id}

class CombatNarrativeMoment:
    def __init__(self, text: str, options: dict):
        self.text = text
        if isinstance(options, list):
            options_dict = {str(i + 1): opt for i, opt in enumerate(options)}
        else:
            options_dict = dict(options) if options else {}
        self.options = options_dict
        
    def to_dict(self) -> dict:
        return {"type": "COMBAT_MOMENT", "text": self.text, "options": self.options}

class VisualEffect:
    def __init__(self, effect_type: str, target_id: str, style: str = None, duration: int = 800, from_side: str = None):
        self.effect_type = effect_type
        self.target_id = target_id
        self.style = style
        self.duration = duration
        self.from_side = from_side

    def to_dict(self) -> dict:
        return {
            "type": "VISUAL_EFFECT",
            "effect_type": self.effect_type,
            "target_id": self.target_id,
            "style": self.style,
            "duration": self.duration,
            "from_side": self.from_side,
        }
