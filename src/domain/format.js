export function round(value, decimals = 1) {
  return Number(value.toFixed(decimals));
}

export function clip(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

export function formatPercent(value) {
  return `${Math.round(value * 100)}%`;
}

export function formatWindow(value) {
  const words = value.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
