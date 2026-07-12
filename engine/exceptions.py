class EngineShutdownException(Exception):
    """Raised when the engine needs to shut down immediately (e.g., client disconnected)."""
    pass

class GameOverException(Exception):
    """Raised when the player dies/loses the game."""
    pass
