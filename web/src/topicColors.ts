// Each topic keeps one colour everywhere it appears, so readers learn to
// recognise where they are.
const COLORS: Record<string, string> = {
  cloud: "#2F5DDB",
  ai: "#7A4FD1",
  devops: "#1F8A5B",
  backend: "#B7791F",
  legacy: "#A33A3A",
};

export function topicColor(topicId: string): string {
  return COLORS[topicId] ?? "#3E5C66";
}
