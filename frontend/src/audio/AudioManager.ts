import { SFX_MAP } from './sfx_map';
import { MUSIC_MAP } from './music_map';

class AudioManager {
  private ctx: AudioContext | null = null;
  private musicSource: AudioBufferSourceNode | null = null;
  private currentMusicKey: string | null = null;

  // Gain nodes for mixing
  private masterGain: GainNode | null = null;
  private bgmGain: GainNode | null = null;
  private sfxGain: GainNode | null = null;

  // Volume channels (ranges 0.0 to 1.0)
  private masterVolume: number = 0.8;
  private bgmVolume: number = 0.6;
  private sfxVolume: number = 0.8;

  // Cache loaded audio buffers
  private bufferCache: Map<string, AudioBuffer> = new Map();

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

      // Chain: BGM/SFX -> BGM/SFX Gain -> Master Gain -> destination
      this.masterGain = this.ctx.createGain();
      this.bgmGain = this.ctx.createGain();
      this.sfxGain = this.ctx.createGain();

      this.masterGain.gain.setValueAtTime(this.masterVolume, this.ctx.currentTime);
      this.bgmGain.gain.setValueAtTime(this.bgmVolume, this.ctx.currentTime);
      this.sfxGain.gain.setValueAtTime(this.sfxVolume, this.ctx.currentTime);

      this.bgmGain.connect(this.masterGain);
      this.sfxGain.connect(this.masterGain);
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

  public async playSFX(key: string) {
    const url = SFX_MAP[key];
    if (!url) {
      console.warn(`SFX key not found in mapping: ${key}`);
      return;
    }

    try {
      this.initContext();
      if (!this.ctx || !this.sfxGain) return;
      const buffer = await this.loadSound(url);
      const source = this.ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(this.sfxGain);
      source.start(0);
    } catch (err) {
      console.error(`Failed to play SFX: ${key}`, err);
    }
  }

  public async playMusic(key: string) {
    if (this.currentMusicKey === key) return; // Already playing

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
        // Source might not have started or already stopped
      }
      this.musicSource = null;
    }
    this.currentMusicKey = null;
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
