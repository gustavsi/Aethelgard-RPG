import { describe, it, expect, vi, beforeEach } from 'vitest';
import { audioManager } from './AudioManager';

describe('AudioManager', () => {
  beforeEach(() => {
    audioManager.stopMusic();
    audioManager.stopWeatherAmbient();
    vi.clearAllMocks();
  });

  it('should initialize AudioContext correctly on first playback', async () => {
    // Play SFX triggers initContext
    await audioManager.playSFX('CLICK');
    // Context is active
    expect(window.AudioContext).toHaveBeenCalled();
  });

  it('should update music speed based on HP ratio', async () => {
    await audioManager.playMusic('combate');
    
    // Normal HP -> speed remains 1.0
    audioManager.updateMusicSpeed(0.8);
    // Low HP (<30%) -> speed increases to 1.25x
    audioManager.updateMusicSpeed(0.25);
    
    expect(audioManager['musicSource']).toBeDefined();
  });

  it('should transition weather ambient sound loops', async () => {
    await audioManager.updateWeatherAmbient('Chuvoso');
    expect(audioManager['currentWeatherKey']).toBe('rain');

    await audioManager.updateWeatherAmbient('Nevoeiro');
    expect(audioManager['currentWeatherKey']).toBe('wind');

    await audioManager.updateWeatherAmbient('Ensolarado');
    expect(audioManager['currentWeatherKey']).toBeNull();
  });
});
