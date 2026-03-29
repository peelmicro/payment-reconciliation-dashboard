export function formatAmount(cents: number, symbol: string = "$"): string {
  return `${symbol}${(cents / 100).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
