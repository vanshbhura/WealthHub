// Indian Number System & Currency Formatters conforming to Prompt 4 Sections 33 & 34

/**
 * Format number into Indian currency format: ₹8,42,650
 * Positive: +₹12,430 (when showSign: true)
 * Negative: -₹4,230
 * Zero: ₹0
 * Missing (null / undefined): "—"
 */
export function formatINR(amount, options = { showSymbol: true, showSign: false, fallback: "—" }) {
  if (amount === undefined || amount === null || (typeof amount === 'number' && isNaN(amount))) {
    return options.fallback !== undefined ? options.fallback : "—";
  }

  const num = Number(amount);
  if (isNaN(num)) return options.fallback !== undefined ? options.fallback : "—";

  if (Math.abs(num) < 0.0001) {
    const symbol = options.showSymbol !== false ? "₹" : "";
    return `${symbol}0`;
  }

  const isNegative = num < 0;
  const absAmount = Math.round(Math.abs(num));

  // Convert to Indian format (lakhs, crores)
  const numStr = absAmount.toString();
  let lastThree = numStr.substring(numStr.length - 3);
  const otherNumbers = numStr.substring(0, numStr.length - 3);
  if (otherNumbers !== '') {
    lastThree = ',' + lastThree;
  }
  const formatted = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + lastThree;

  const symbol = options.showSymbol !== false ? "₹" : "";
  let sign = "";

  if (isNegative) {
    sign = "-";
  } else if (options.showSign && num > 0) {
    sign = "+";
  }

  return `${sign}${symbol}${formatted}`;
}

/**
 * Format percentage: +1.48%, -0.72%, 0.00%, or "—" if missing
 */
export function formatPercent(percent, showSign = true, fallback = "—") {
  if (percent === undefined || percent === null || (typeof percent === 'number' && isNaN(percent))) {
    return fallback;
  }
  const num = Number(percent);
  if (isNaN(num)) return fallback;

  if (Math.abs(num) < 0.0001) {
    return "0.00%";
  }

  const sign = num > 0 && showSign ? "+" : (num < 0 ? "-" : "");
  return `${sign}${Math.abs(num).toFixed(2)}%`;
}

/**
 * Format relative time or freshness string based on timestamp and freshness status
 */
export function formatFreshness(timestamp, freshnessStatus = null) {
  if (freshnessStatus === 'REALTIME') return "Live sync";
  if (!timestamp) return "Awaiting update";

  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return "Awaiting update";

    const diffMs = Date.now() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Updated just now";
    if (diffMins < 60) return `Updated ${diffMins} min ago`;
    if (diffHours < 24) return `Updated ${diffHours} hr${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays === 1) return "Updated yesterday";
    if (diffDays < 7) return `Updated ${diffDays} days ago`;
    return `Updated ${date.toLocaleDateString()}`;
  } catch (e) {
    return "Awaiting update";
  }
}
