import os
import sys
import time
import re
import threading
from engine.constants import Colors

class WebBridgeStorage:
    _local = threading.local()

    @classmethod
    def get_bridge(cls):
        return getattr(cls._local, 'bridge', None)

    @classmethod
    def set_bridge(cls, bridge):
        cls._local.bridge = bridge

def remove_ansi(text):
    """Removes ANSI escape codes to calculate true string length."""
    if not isinstance(text, str):
        text = str(text)
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def clear_screen():
    """Clears the terminal screen using ClearScreen DTO."""
    from engine.dto import ClearScreen
    from engine.adapter import get_adapter
    get_adapter().emit(ClearScreen())

def print_divider(color=Colors.BRIGHT_BLACK, length=80):
    """Prints a styled divider line using NarrativeText DTO."""
    from engine.dto import NarrativeText
    from engine.adapter import get_adapter
    from engine.adapter import WebUIAdapter
    adapter = get_adapter()
    if not isinstance(adapter, WebUIAdapter):
        adapter.emit(NarrativeText('─' * length))

def print_centered(text, color=Colors.WHITE, width=78):
    """Prints text centered in a custom width using NarrativeText DTO."""
    from engine.dto import NarrativeText
    from engine.adapter import get_adapter
    from engine.adapter import WebUIAdapter
    adapter = get_adapter()
    cleaned = remove_ansi(text)
    if isinstance(adapter, WebUIAdapter):
        adapter.emit(NarrativeText(cleaned))
    else:
        padding = max(0, (width - len(cleaned)) // 2)
        adapter.emit(NarrativeText(f"{' ' * padding}{color}{text}{Colors.RESET}"))

def typewriter(text, delay=0.02, color=Colors.WHITE, wait_on_end=0.0):
    """Prints text with a typewriter effect using NarrativeText DTO."""
    from engine.dto import NarrativeText
    from engine.adapter import get_adapter
    from engine.adapter import WebUIAdapter
    adapter = get_adapter()
    cleaned = remove_ansi(text)
    
    if isinstance(adapter, WebUIAdapter):
        adapter.emit(NarrativeText(cleaned))
        # Small read delay for web
        time.sleep(len(cleaned) * 0.01)
        if wait_on_end > 0:
            time.sleep(wait_on_end)
    else:
        # CLI typewriter effect is rendered inside CLI adapter.emit.
        # But wait, if CLI adapter.emit prints the whole text instantly, 
        # let's simulate the delay here or inside adapter.emit.
        # For simplicity, we emit the raw colored string to CLI
        adapter.emit(NarrativeText(f"{color}{text}{Colors.RESET}"))
        if wait_on_end > 0:
            time.sleep(wait_on_end)

def play_sound_effect(effect_text, color=Colors.BRIGHT_MAGENTA):
    """Outputs a text-based sound effect using SoundEffect DTO."""
    from engine.dto import SoundEffect
    from engine.adapter import get_adapter
    from engine.adapter import WebUIAdapter
    adapter = get_adapter()
    adapter.emit(SoundEffect(effect_text))
    if not isinstance(adapter, WebUIAdapter):
        time.sleep(0.8)

def draw_box(title, lines, color=Colors.CYAN, width=78, align="left"):
    """Draws a beautiful single-column box using NarrativeText DTO."""
    from engine.dto import NarrativeText
    from engine.adapter import get_adapter
    from engine.adapter import WebUIAdapter
    adapter = get_adapter()
    
    if isinstance(adapter, WebUIAdapter):
        content = f"\n✨ {remove_ansi(title)} ✨\n" + "\n".join(remove_ansi(l) for l in lines)
        adapter.emit(NarrativeText(content))
    else:
        top = f"┌─ {Colors.BOLD}{title}{Colors.RESET}{color} {'─' * (width - len(remove_ansi(title)) - 5)}┐"
        bottom = f"└{'─' * (width - 2)}┘"
        box_str = f"{color}{top}{Colors.RESET}\n"
        for line in lines:
            cleaned = remove_ansi(line)
            needed_spaces = width - 4 - len(cleaned)
            if needed_spaces < 0:
                line = line[:width - 7] + "..."
                needed_spaces = 0
                
            if align == "center":
                left_pad = needed_spaces // 2
                right_pad = needed_spaces - left_pad
                box_str += f"{color}│{Colors.RESET}{' ' * left_pad}{line}{' ' * right_pad}{color}│{Colors.RESET}\n"
            else:
                box_str += f"{color}│{Colors.RESET} {line}{' ' * needed_spaces} {color}│{Colors.RESET}\n"
        box_str += f"{color}{bottom}{Colors.RESET}"
        adapter.emit(NarrativeText(box_str))

def draw_two_columns(col1_title, col1_lines, col2_title, col2_lines, col1_width=36, col2_width=38, color=Colors.CYAN):
    """Draws two boxes side by side using NarrativeText DTO."""
    from engine.dto import NarrativeText
    from engine.adapter import get_adapter
    from engine.adapter import WebUIAdapter
    adapter = get_adapter()
    
    if isinstance(adapter, WebUIAdapter):
        # Web uses combat state sync, so skip manual text columns
        return
        
    max_len = max(len(col1_lines), len(col2_lines))
    col1_padded = col1_lines + [""] * (max_len - len(col1_lines))
    col2_padded = col2_lines + [""] * (max_len - len(col2_lines))
    
    c1_title_clean = remove_ansi(col1_title)
    c2_title_clean = remove_ansi(col2_title)
    
    top1 = f"┌─ {Colors.BOLD}{col1_title}{Colors.RESET}{color} {'─' * (col1_width - len(c1_title_clean) - 5)}┬─ {Colors.BOLD}{col2_title}{Colors.RESET}{color} {'─' * (col2_width - len(c2_title_clean) - 5)}┐"
    col_str = f"{color}{top1}{Colors.RESET}\n"
    
    for i in range(max_len):
        l1 = col1_padded[i]
        l2 = col2_padded[i]
        
        l1_clean = remove_ansi(l1)
        c1_spaces = col1_width - len(l1_clean) - 2
        if c1_spaces < 0:
            l1 = l1[:col1_width - 5] + "..."
            c1_spaces = 0
            
        l2_clean = remove_ansi(l2)
        c2_spaces = col2_width - len(l2_clean) - 2
        if c2_spaces < 0:
            l2 = l2[:col2_width - 5] + "..."
            c2_spaces = 0
            
        col_str += f"{color}│{Colors.RESET} {l1}{' ' * c1_spaces} {color}│{Colors.RESET} {l2}{' ' * c2_spaces} {color}│{Colors.RESET}\n"
        
    bottom = f"└{'─' * (col1_width)}┴{'─' * (col2_width)}┘"
    col_str += f"{color}{bottom}{Colors.RESET}"
    adapter.emit(NarrativeText(col_str))

def make_bar(current, maximum, color=Colors.GREEN, bar_char="█", empty_char="░", length=15):
    """Returns a string representation of a status bar."""
    current = max(0, current)
    if maximum <= 0:
        percent = 0
    else:
        percent = max(0, min(1, current / maximum))
    filled_len = int(length * percent)
    empty_len = length - filled_len
    bar = f"{color}{bar_char * filled_len}{Colors.RESET}{Colors.BRIGHT_BLACK}{empty_char * empty_len}{Colors.RESET}"
    return f"[{bar}] {current}/{maximum}"

def get_menu_choice(options, prompt="Escolha uma opção: ", error_msg="Opção inválida. Tente novamente."):
    """Presents a list of options and safely gets player input using ChoiceRequested DTO."""
    from engine.dto import ChoiceRequested, NarrativeText
    from engine.adapter import get_adapter
    from engine.adapter import WebUIAdapter
    adapter = get_adapter()
    
    if isinstance(options, list):
        options_dict = {str(i + 1): opt for i, opt in enumerate(options)}
    else:
        options_dict = dict(options) if options else {}
        
    if not options_dict:
        options_dict = {"exit": "Voltar"}
        
    if isinstance(adapter, WebUIAdapter):
        # Web uses event-based input prompt
        return adapter.emit(ChoiceRequested(remove_ansi(prompt), {k: remove_ansi(v) for k, v in options_dict.items()}))
        
    # CLI mode drawing:
    box_lines = []
    for key, value in options_dict.items():
        box_lines.append(f" {Colors.YELLOW}{key}{Colors.RESET} - {value}")
        
    draw_box("Opções", box_lines, Colors.YELLOW, width=78)
    
    while True:
        choice = adapter.emit(ChoiceRequested(remove_ansi(prompt), {k: remove_ansi(v) for k, v in options_dict.items()}))
        if choice in options_dict:
            return choice
        adapter.emit(NarrativeText(f"{Colors.RED}{error_msg}{Colors.RESET}"))

def press_any_key(msg="Pressione [ENTER] para continuar..."):
    """Pauses the game until user interacts using PressAnyKey DTO."""
    from engine.dto import PressAnyKey
    from engine.adapter import get_adapter
    get_adapter().emit(PressAnyKey(remove_ansi(msg)))
