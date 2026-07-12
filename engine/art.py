from engine.constants import Colors

# Game Title Screen
TITLE_ART = f"""
{Colors.BRIGHT_YELLOW}
 ⚔   A E T H E L G A R D     R P G   ⚔
{Colors.BRIGHT_CYAN}    ─── CRÔNICAS DE AVENTURA (v1.0) ───{Colors.RESET}
"""

# Environments
FOREST_ART = f"""
{Colors.GREEN}
       _-_
    /~~   ~~\\
 /~~         ~~\\
{{               }}
 \\  _-     -_  /
   ~  \\\\ //  ~
_ _--- ██ ---_ _
      ███
      ███
{Colors.RESET}
"""

CABIN_ART = f"""
{Colors.YELLOW}
      /\\
     /  \\
    /    \\
   /______\\
   |  __  |
   | |  | |
   |_|__|_|
{Colors.RESET}
"""

TOWN_ART = f"""
{Colors.BRIGHT_CYAN}
  /\\          /\\          /\\
 /  \\        /  \\        /  \\
/____\\      /____\\      /____\\
| [] |      | [] |      | [] |
|    |      |    |      |    |
{Colors.RESET}
"""

CAVES_ART = f"""
{Colors.BRIGHT_BLACK}
   _____________________
  /                     \\
 /   /\\    /\\    /\\      \\
|   /  \\  /  \\  /  \\      |
|  /____\\/____\\/____\\     |
|   |  |   |  |   |  |    |
 \\_______________________/
{Colors.RESET}
"""

TEMPLE_ART = f"""
{Colors.BRIGHT_MAGENTA}
       /\\
      /  \\
     /____\\
    |======|
    | [  ] |
    |      |
   /========\\
  /__________\\
{Colors.RESET}
"""

# Bosses
OGRE_ART = f"""
{Colors.BRIGHT_GREEN}
        ,      ,
       /(.-""-.)\\
   |\\  \\/      \\/  /|
   | \\ / =.  .= \\ / |
   \\( \\   o\\/o   / )/
    \\_, '-/  \\-' ,_/
      /   \\__/   \\
      \\ \\__/\\\\__/ /
    ___\\ \\|--|/ /___
{Colors.RESET}
"""

INQUISITOR_ART = f"""
{Colors.BRIGHT_RED}
         /\\
        /  \\
       /____\\
      [| oo |]  <- Inquisidor das Sombras
       \\ == /
      /| ++ |\\
     / | || | \\
       | || |
       | || |
{Colors.RESET}
"""

MALAKAR_ART = f"""
{Colors.BRIGHT_MAGENTA}
        /\\  /\\
       /  \\/  \\
      (  o  o  )  <- Lorde Malakar, O Flamejante
       \\  --  /
       /\\====/\\
      /  \\  /  \\
     /    \\/    \\
    /  /\\    /\\  \\
   /__/  \\__/  \\__\\
{Colors.RESET}
"""

# Game States
GAME_OVER_ART = f"""
{Colors.RED}
 ██████╗  █████╗ ███╗   ███╗███████╗     ██████╗ ██╗   ██╗███████╗██████╗ 
██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔═══██╗██║   ██║██╔════╝██╔══██╗
██║  ███╗███████║██╔████╔██║█████╗      ██║   ██║██║   ██║█████╗  ██████╔╝
██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗
╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║
 ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝     ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝
{Colors.RESET}
"""

VICTORY_ART = f"""
{Colors.BRIGHT_YELLOW}
██╗   ██╗██╗████████╗ ██████╗ ██████╗ ██╗ █████╗  ██╗
██║   ██║██║╚══██╔══╝██╔═══██╗██╔══██╗██║██╔══██╗ ██║
██║   ██║██║   ██║   ██║   ██║██████╔╝██║███████║ ██║
╚██╗ ██╔╝██║   ██║   ██║   ██║██╔══██╗██║██╔══██║ ╚═╝
 ╚████╔╝ ██║   ██║   ╚██████╔╝██║  ██║██║██║  ██║ ██╗
  ╚═══╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═╝
{Colors.RESET}
"""

def get_enemy_art(name: str) -> str:
    name_upper = name.upper()
    if "OGRO" in name_upper:
        return OGRE_ART
    elif "INQUISIDOR" in name_upper:
        return INQUISITOR_ART
    elif "MALAKAR" in name_upper:
        return MALAKAR_ART
    elif "LOBO" in name_upper:
        return f"""{Colors.BRIGHT_BLACK}
      /\\_ /\\
     ( o.o )
      > ^ <
{Colors.RESET}"""
    elif "SALTEADOR" in name_upper:
        return f"""{Colors.BRIGHT_WHITE}
       /\\
      /__\\
     (|oo|) 
      \\__/
      /|\\
{Colors.RESET}"""
    elif "MORCEGO" in name_upper:
        return f"""{Colors.BRIGHT_BLACK}
     /\\___/\\
    (  o_o  )
     \\ / \\ /
      V   V
{Colors.RESET}"""
    elif "GUARDIÃO" in name_upper:
        return f"""{Colors.BRIGHT_GREEN}
       \\|/
      --O--
       /|\\
      / | \\
{Colors.RESET}"""
    elif "GOBLIN" in name_upper:
        return f"""{Colors.BRIGHT_GREEN}
       /\\
      /  \\
     ( .. )
     / >< \\
{Colors.RESET}"""
    elif "VERME" in name_upper:
        return f"""{Colors.YELLOW}
       ___
     / ___ \\
    | /   \\ |
    | |   | |
    \\ \\___/ /
{Colors.RESET}"""
    elif "CULTISTA" in name_upper:
        return f"""{Colors.RED}
       /\\
      /  \\
     (|xx|) 
      \\__/
      /|\\
{Colors.RESET}"""
    elif "GOLEM" in name_upper:
        return f"""{Colors.BRIGHT_BLACK}
      [___]
      [o o]
     /[---]\\
      [___]
{Colors.RESET}"""
    elif "DEMÔNIO" in name_upper:
        return f"""{Colors.BRIGHT_RED}
      \\   /
       \\ /
      (o o)
      / V \\
{Colors.RESET}"""
    elif "ELENA" in name_upper:
        return f"""{Colors.CYAN}
       /\\
      /  \\
     ( .. ) >>---|>
      \\__/
{Colors.RESET}"""
    else:
        # Generic monster fallback
        return f"""{Colors.MAGENTA}
       \\ /
      (o o)
      /___\\
{Colors.RESET}"""

