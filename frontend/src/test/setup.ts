import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  clear: vi.fn(),
  removeItem: vi.fn(),
  length: 0,
  key: vi.fn(() => null),
};
window.localStorage = localStorageMock as any;

// Mock AudioContext and related Web Audio APIs
class MockAudioNode {
  connect = vi.fn();
  disconnect = vi.fn();
}

class MockGainNode extends MockAudioNode {
  gain = {
    setValueAtTime: vi.fn(),
    exponentialRampToValueAtTime: vi.fn(),
    linearRampToValueAtTime: vi.fn(),
  };
}

class MockAudioBufferSourceNode extends MockAudioNode {
  buffer = null;
  loop = false;
  playbackRate = {
    setValueAtTime: vi.fn(),
  };
  start = vi.fn();
  stop = vi.fn();
}

class MockOscillatorNode extends MockAudioNode {
  type = 'sine';
  frequency = { setValueAtTime: vi.fn() };
  start = vi.fn();
  stop = vi.fn();
}

class MockBiquadFilterNode extends MockAudioNode {
  type = 'highpass';
  frequency = { value: 0 };
}

class MockAudioContext {
  state = 'suspended';
  currentTime = 0;
  sampleRate = 44100;
  destination = {};
  createGain = vi.fn(() => new MockGainNode());
  createBufferSource = vi.fn(() => new MockAudioBufferSourceNode());
  createOscillator = vi.fn(() => new MockOscillatorNode());
  createBiquadFilter = vi.fn(() => new MockBiquadFilterNode());
  createBuffer = vi.fn((channels: number, length: number, sampleRate: number) => ({
    getChannelData: () => new Float32Array(length),
    length,
    sampleRate,
    numberOfChannels: channels,
  }));
  decodeAudioData = vi.fn(() => Promise.resolve({}));
  resume = vi.fn(() => {
    this.state = 'running';
    return Promise.resolve();
  });
}

// Wrap it as a spy constructor
const MockAudioContextSpy = vi.fn().mockImplementation(function() {
  return new MockAudioContext();
});

window.AudioContext = MockAudioContextSpy as any;
(window as any).webkitAudioContext = MockAudioContextSpy as any;

// Mock fetch for audio loading
globalThis.fetch = vi.fn(() =>
  Promise.resolve({
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
  } as any)
);
