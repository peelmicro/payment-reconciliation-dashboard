import {
  paymentStatusStyles,
  reconciliationStatusStyles,
} from "@/lib/status-colors";

describe("reconciliationStatusStyles", () => {
  const expectedStatuses = [
    "matched",
    "matched_with_fee",
    "amount_mismatch",
    "missing_internal",
    "missing_external",
    "duplicate",
    "disputed",
  ];

  it("has an entry for every reconciliation status", () => {
    expectedStatuses.forEach((status) => {
      expect(reconciliationStatusStyles[status]).toBeDefined();
    });
  });

  it("all entries are non-empty strings", () => {
    Object.values(reconciliationStatusStyles).forEach((value) => {
      expect(typeof value).toBe("string");
      expect(value.length).toBeGreaterThan(0);
    });
  });

  it("no two statuses share the same style", () => {
    const values = Object.values(reconciliationStatusStyles);
    const unique = new Set(values);
    expect(unique.size).toBe(values.length);
  });
});

describe("paymentStatusStyles", () => {
  const expectedStatuses = [
    "succeeded",
    "pending",
    "failed",
    "refunded",
    "partially_refunded",
    "disputed",
  ];

  it("has an entry for every payment status", () => {
    expectedStatuses.forEach((status) => {
      expect(paymentStatusStyles[status]).toBeDefined();
    });
  });

  it("all entries are non-empty strings", () => {
    Object.values(paymentStatusStyles).forEach((value) => {
      expect(typeof value).toBe("string");
      expect(value.length).toBeGreaterThan(0);
    });
  });

  it("no two statuses share the same style", () => {
    const values = Object.values(paymentStatusStyles);
    const unique = new Set(values);
    expect(unique.size).toBe(values.length);
  });
});
