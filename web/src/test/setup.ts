import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock window.scrollTo which is not implemented in jsdom
Object.defineProperty(window, 'scrollTo', {
  value: vi.fn(),
  writable: true,
});
