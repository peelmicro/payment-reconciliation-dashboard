import { formatAmount } from "@/lib/format";

describe("formatAmount", () => {
  it("formats zero cents as 0.00", () => {
    expect(formatAmount(0)).toBe("$0.00");
  });

  it("formats 100 cents as 1.00", () => {
    expect(formatAmount(100)).toBe("$1.00");
  });

  it("formats a single cent as 0.01", () => {
    expect(formatAmount(1)).toBe("$0.01");
  });

  it("uses the provided currency symbol", () => {
    const result = formatAmount(9_999, "€");
    expect(result).toContain("€");
    expect(result).toContain("99.99");
  });

  it("defaults to dollar sign when no symbol is provided", () => {
    expect(formatAmount(500)).toMatch(/^\$/);
  });
});
