// Dates shown as "2 Nov 2026" and "2 Nov 2026, 7:55 pm" in the reader's own time zone.
export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export const formatDateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
