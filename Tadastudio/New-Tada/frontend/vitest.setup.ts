import "@testing-library/dom";
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Provide Jest compatibility for existing tests that use jest.fn()
// @ts-expect-error - Jest compatibility layer
globalThis.jest = vi;
