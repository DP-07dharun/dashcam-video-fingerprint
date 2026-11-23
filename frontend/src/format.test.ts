import { describe, expect, it } from "vitest";
import { formatBytes, formatDuration, formatPercent, shortHash } from "./format";

describe("format helpers", () => {
  it("formats byte sizes", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });

  it("formats durations", () => {
    expect(formatDuration(5)).toBe("0:05");
    expect(formatDuration(75.5)).toBe("1:15.5");
    expect(formatDuration(3725)).toBe("1:02:05");
    expect(formatDuration(-2)).toBe("-0:02");
  });

  it("formats percentages", () => {
    expect(formatPercent(1)).toBe("100%");
    expect(formatPercent(0.8333)).toBe("83.3%");
  });

  it("shortens long hashes only", () => {
    expect(shortHash("abcd")).toBe("abcd");
    expect(shortHash("a".repeat(64))).toBe(`${"a".repeat(10)}…aaaa`);
  });
});
