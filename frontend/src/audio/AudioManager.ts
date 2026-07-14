import { SFX_MAP, resolveSfxKey, synthKindForKey, type SynthKind } from './sfx_map';
import { MUSIC_MAP } from './music_map';

class AudioManager {
  private ctx: AudioContext | null = null;
  private musicSource: AudioBufferSourceNode | null = null;
  private currentMusicKey: string | null = null;
  private weatherSource: AudioBufferSourceNode | null = null;
  private currentWeatherKey: string | null = null;

  private masterGain: GainNode | null = null;
  private bgmGain: GainNode | null = null;
  private sfxGain: GainNode | null = null;
  private weatherGain: GainNode | null = null;

  private masterVolume: number = 0.8;
  private bgmVolume: number = 0.55;
  private sfxVolume: number = 0.85;
  private weatherVolume: number = 0.4;

  private bufferCache: Map<string, AudioBuffer> = new Map();
  private lastPlayAt: Map<string, number> = new Map();

  constructor() {
    try {
      const storedMaster = localStorage.getItem('audio_master_vol');
      const storedBgm = localStorage.getItem('audio_bgm_vol');
      const storedSfx = localStorage.getItem('audio_sfx_vol');

      if (storedMaster !== null) this.masterVolume = parseFloat(storedMaster);
      if (storedBgm !== null) this.bgmVolume = parseFloat(storedBgm);
      if (storedSfx !== null) this.sfxVolume = parseFloat(storedSfx);
    } catch (e) {
      console.warn('LocalStorage access blocked, using default audio volumes.', e);
    }

    if (typeof window !== 'undefined') {
      const resumeAudio = () => {
        this.initContext();
        if (this.ctx && this.ctx.state === 'running') {
          window.removeEventListener('click', resumeAudio);
          window.removeEventListener('keydown', resumeAudio);
        }
      };
      window.addEventListener('click', resumeAudio);
      window.addEventListener('keydown', resumeAudio);
    }
  }

  private initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) {
        console.warn('Web Audio API not supported by this browser.');
        return;
      }
      this.ctx = new AudioCtx();

      this.masterGain = this.ctx.createGain();
      this.bgmGain = this.ctx.createGain();
      this.sfxGain = this.ctx.createGain();
      this.weatherGain = this.ctx.createGain();

      this.masterGain.gain.setValueAtTime(this.masterVolume, this.ctx.currentTime);
      this.bgmGain.gain.setValueAtTime(this.bgmVolume, this.ctx.currentTime);
      this.sfxGain.gain.setValueAtTime(this.sfxVolume, this.ctx.currentTime);
      this.weatherGain.gain.setValueAtTime(this.weatherVolume, this.ctx.currentTime);

      this.bgmGain.connect(this.masterGain);
      this.sfxGain.connect(this.masterGain);
      this.weatherGain.connect(this.masterGain);
      this.masterGain.connect(this.ctx.destination);
    }

    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  private async loadSound(url: string): Promise<AudioBuffer> {
    if (this.bufferCache.has(url)) {
      return this.bufferCache.get(url)!;
    }

    this.initContext();
    if (!this.ctx) {
      throw new Error('AudioContext not initialized');
    }
    const response = await fetch(url);
    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await this.ctx.decodeAudioData(arrayBuffer);
    this.bufferCache.set(url, audioBuffer);
    return audioBuffer;
  }

  private rand(min: number, max: number) {
    return min + Math.random() * (max - min);
  }

  /** Soft anti-spam for the same key within a short window. */
  private shouldThrottle(key: string, ms = 40): boolean {
    const now = performance.now();
    const last = this.lastPlayAt.get(key) ?? 0;
    if (now - last < ms) return true;
    this.lastPlayAt.set(key, now);
    return false;
  }

  /**
   * Procedural one-shots layered under (or instead of) sample files.
   * Gives punch even when MP3s are tiny/flat.
   */
  private playSynth(kind: SynthKind, intensity = 1) {
    if (kind === 'none' || !this.ctx || !this.sfxGain) return;
    // Graceful no-op under incomplete AudioContext mocks / unsupported browsers
    if (typeof this.ctx.createOscillator !== 'function' || typeof this.ctx.createBuffer !== 'function') {
      return;
    }
    const t0 = this.ctx.currentTime;
    const g = this.ctx.createGain();
    g.connect(this.sfxGain);

    const tone = (freq: number, type: OscillatorType, start: number, dur: number, peak: number) => {
      const osc = this.ctx!.createOscillator();
      const eg = this.ctx!.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, t0 + start);
      eg.gain.setValueAtTime(0.0001, t0 + start);
      eg.gain.exponentialRampToValueAtTime(Math.max(0.0001, peak * intensity), t0 + start + 0.01);
      eg.gain.exponentialRampToValueAtTime(0.0001, t0 + start + dur);
      osc.connect(eg);
      eg.connect(g);
      osc.start(t0 + start);
      osc.stop(t0 + start + dur + 0.02);
    };

    const noiseBurst = (start: number, dur: number, peak: number, hipass = 800) => {
      const len = Math.max(1, Math.floor(this.ctx!.sampleRate * dur));
      const buf = this.ctx!.createBuffer(1, len, this.ctx!.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len);
      const src = this.ctx!.createBufferSource();
      src.buffer = buf;
      const filter = this.ctx!.createBiquadFilter();
      filter.type = 'highpass';
      filter.frequency.value = hipass;
      const eg = this.ctx!.createGain();
      eg.gain.setValueAtTime(0.0001, t0 + start);
      eg.gain.exponentialRampToValueAtTime(Math.max(0.0001, peak * intensity), t0 + start + 0.005);
      eg.gain.exponentialRampToValueAtTime(0.0001, t0 + start + dur);
      src.connect(filter);
      filter.connect(eg);
      eg.connect(g);
      src.start(t0 + start);
      src.stop(t0 + start + dur + 0.02);
    };

    switch (kind) {
      case 'hit':
        noiseBurst(0, 0.08, 0.45, 400);
        tone(120 + this.rand(-20, 20), 'triangle', 0, 0.12, 0.35);
        tone(55, 'sine', 0, 0.15, 0.25);
        break;
      case 'crit':
        noiseBurst(0, 0.12, 0.55, 200);
        tone(90, 'sawtooth', 0, 0.18, 0.3);
        tone(180, 'square', 0.02, 0.1, 0.15);
        tone(440, 'sine', 0.04, 0.2, 0.12);
        break;
      case 'magic':
        tone(520 + this.rand(-40, 40), 'sine', 0, 0.25, 0.2);
        tone(780, 'triangle', 0.02, 0.3, 0.15);
        tone(1040, 'sine', 0.05, 0.35, 0.1);
        noiseBurst(0.05, 0.15, 0.12, 2000);
        break;
      case 'heal':
        tone(523.25, 'sine', 0, 0.2, 0.18);
        tone(659.25, 'sine', 0.05, 0.25, 0.14);
        tone(783.99, 'sine', 0.1, 0.3, 0.12);
        break;
      case 'swoosh':
        noiseBurst(0, 0.18, 0.3, 1200);
        tone(300 + this.rand(0, 80), 'triangle', 0, 0.15, 0.08);
        break;
      case 'ui':
        tone(880, 'sine', 0, 0.06, 0.12);
        break;
      case 'roar':
        noiseBurst(0, 0.35, 0.4, 100);
        tone(70, 'sawtooth', 0, 0.4, 0.22);
        tone(45, 'sine', 0, 0.45, 0.3);
        break;
      case 'death':
        tone(220, 'sawtooth', 0, 0.3, 0.2);
        tone(110, 'sine', 0.05, 0.4, 0.25);
        noiseBurst(0, 0.25, 0.2, 300);
        break;
      case 'level':
        tone(523, 'sine', 0, 0.15, 0.15);
        tone(659, 'sine', 0.1, 0.15, 0.15);
        tone(784, 'sine', 0.2, 0.15, 0.15);
        tone(1046, 'sine', 0.3, 0.25, 0.18);
        break;
      case 'lightning':
        noiseBurst(0, 0.05, 0.7, 80);
        noiseBurst(0.04, 0.2, 0.35, 400);
        tone(40, 'sawtooth', 0, 0.25, 0.35);
        break;
    }
  }

  public async playSFX(key: string, opts?: { pitch?: number; volume?: number; intensity?: number }) {
    if (!key) return;
    if (this.shouldThrottle(key, 35)) return;

    this.initContext();
    if (!this.ctx || !this.sfxGain) return;

    const resolved = resolveSfxKey(key);
    const kind = synthKindForKey(resolved || key);
    const intensity = opts?.intensity ?? 1;

    const mapKey = resolved;
    const url = mapKey ? SFX_MAP[mapKey] : null;

    // Prefer HQ samples; only use a light synth bed when no sample, or a soft
    // transient under short hits so stacked attacks stay punchy.
    if (!url) {
      this.playSynth(kind === 'none' ? 'hit' : kind, intensity * 0.85);
      return;
    }

    // Soft transient under impact-class sounds only (won't drown new samples)
    if (kind === 'hit' || kind === 'crit' || kind === 'lightning') {
      this.playSynth(kind, intensity * 0.28);
    }

    try {
      const buffer = await this.loadSound(url);
      if (!this.ctx || !this.sfxGain) return;

      const source = this.ctx.createBufferSource();
      source.buffer = buffer;
      // Slight pitch variance so repeated hits don't machine-gun
      const baseRate = opts?.pitch ?? this.rand(0.94, 1.06);
      source.playbackRate.setValueAtTime(baseRate, this.ctx.currentTime);

      const vol = this.ctx.createGain();
      const peak = Math.min(1.15, (opts?.volume ?? this.rand(0.88, 1.05)) * intensity);
      vol.gain.setValueAtTime(peak, this.ctx.currentTime);

      source.connect(vol);
      vol.connect(this.sfxGain);
      source.start(0);
    } catch (err) {
      console.error(`Failed to play SFX: ${key}`, err);
      this.playSynth(kind === 'none' ? 'hit' : kind, intensity);
    }
  }

  /** Convenience for combat damage feedback. */
  public playHit(isCrit = false, intensity = 1) {
    this.playSFX(isCrit ? 'HIT_CRITICAL' : 'HIT_NORMAL', { intensity, pitch: this.rand(0.9, 1.12) });
  }

  public playUiClick() {
    this.playSFX('CLICK', { intensity: 0.7, pitch: this.rand(0.95, 1.05) });
  }

  public async playMusic(key: string) {
    if (this.currentMusicKey === key) return;

    const url = MUSIC_MAP[key];
    if (!url) {
      console.warn(`Music key not found in mapping: ${key}`);
      return;
    }

    try {
      this.initContext();
      this.stopMusic();

      this.currentMusicKey = key;
      const buffer = await this.loadSound(url);
      if (!this.ctx || !this.bgmGain || this.currentMusicKey !== key) return;

      const source = this.ctx.createBufferSource();
      source.buffer = buffer;
      source.loop = true;
      source.connect(this.bgmGain);
      source.start(0);

      this.musicSource = source;
    } catch (err) {
      console.error(`Failed to play music: ${key}`, err);
    }
  }

  public stopMusic() {
    if (this.musicSource) {
      try {
        this.musicSource.stop();
      } catch (e) {
        // ignore
      }
      this.musicSource = null;
    }
    this.currentMusicKey = null;
  }

  public updateMusicSpeed(hpRatio: number) {
    if (this.musicSource && this.ctx) {
      const speed = hpRatio < 0.3 ? 1.25 : 1.0;
      this.musicSource.playbackRate.setValueAtTime(speed, this.ctx.currentTime);
    }
  }

  public async updateWeatherAmbient(weather: string) {
    let targetKey: string | null = null;
    if (weather === 'Chuvoso' || weather === 'Tempestade') {
      targetKey = 'rain';
    } else if (weather === 'Nevoeiro') {
      targetKey = 'wind';
    }

    if (this.currentWeatherKey === targetKey) return;

    this.currentWeatherKey = targetKey;
    this.stopWeatherAmbient();

    if (!targetKey) return;

    const url = targetKey === 'rain' ? '/audio/sfx/rain_ambient.mp3' : '/audio/sfx/wind_ambient.mp3';

    try {
      this.initContext();
      const buffer = await this.loadSound(url);
      if (!this.ctx || !this.weatherGain || this.currentWeatherKey !== targetKey) return;

      const source = this.ctx.createBufferSource();
      source.buffer = buffer;
      source.loop = true;
      source.connect(this.weatherGain);
      source.start(0);

      this.weatherSource = source;
    } catch (err) {
      console.error(`Failed to play weather ambient: ${targetKey}`, err);
    }
  }

  public stopWeatherAmbient() {
    if (this.weatherSource) {
      try {
        this.weatherSource.stop();
      } catch (e) {}
      this.weatherSource = null;
    }
  }

  public setVolume(channel: 'master' | 'bgm' | 'sfx', value: number) {
    const clamped = Math.max(0.0, Math.min(1.0, value));
    this.initContext();
    if (!this.ctx) return;

    if (channel === 'master') {
      this.masterVolume = clamped;
      this.masterGain?.gain.setValueAtTime(clamped, this.ctx.currentTime);
      localStorage.setItem('audio_master_vol', clamped.toString());
    } else if (channel === 'bgm') {
      this.bgmVolume = clamped;
      this.bgmGain?.gain.setValueAtTime(clamped, this.ctx.currentTime);
      localStorage.setItem('audio_bgm_vol', clamped.toString());
    } else if (channel === 'sfx') {
      this.sfxVolume = clamped;
      this.sfxGain?.gain.setValueAtTime(clamped, this.ctx.currentTime);
      localStorage.setItem('audio_sfx_vol', clamped.toString());
    }
  }
}

export const audioManager = new AudioManager();
export default audioManager;
