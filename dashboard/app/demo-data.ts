export type Signal = {
  id: string;
  drug: string;
  event: string;
  status: "Priority review" | "Monitor" | "Context needed";
  detector: string;
  score: number;
  lower: number;
  upper: number;
  cases: number;
  serious: number;
  quarter: string;
  trend: number[];
  reasons: string[];
};

export const signals: Signal[] = [
  {
    id: "semaglutide-ileus",
    drug: "SEMAGLUTIDE",
    event: "ILEUS",
    status: "Priority review",
    detector: "ROR + temporal",
    score: 4.82,
    lower: 2.91,
    upper: 7.98,
    cases: 37,
    serious: 31,
    quarter: "2025 Q2",
    trend: [4, 6, 7, 11, 13, 19, 24, 37],
    reasons: [
      "Lower 95% confidence bound exceeds 1",
      "Report count is 4.1 robust deviations above prior history",
      "Signal is stable at 37 target reports",
    ],
  },
  {
    id: "dupilumab-ocular",
    drug: "DUPILUMAB",
    event: "OCULAR INFECTION",
    status: "Priority review",
    detector: "PRR + temporal",
    score: 3.74,
    lower: 2.28,
    upper: 6.12,
    cases: 29,
    serious: 18,
    quarter: "2025 Q2",
    trend: [3, 5, 4, 7, 10, 12, 18, 29],
    reasons: [
      "PRR ≥ 2 with chi-square ≥ 4",
      "Quarter-over-quarter growth is 61%",
      "Serious-report proportion increased to 62%",
    ],
  },
  {
    id: "topiramate-hypersensitivity",
    drug: "TOPIRAMATE",
    event: "HYPERSENSITIVITY",
    status: "Monitor",
    detector: "ROR",
    score: 2.61,
    lower: 1.42,
    upper: 4.79,
    cases: 16,
    serious: 9,
    quarter: "2025 Q2",
    trend: [6, 8, 7, 9, 10, 11, 13, 16],
    reasons: [
      "ROR lower confidence bound exceeds 1",
      "Count growth is elevated but below change threshold",
      "No Isolation Forest anomaly in the current quarter",
    ],
  },
  {
    id: "dexmedetomidine-di",
    drug: "DEXMEDETOMIDINE",
    event: "DIABETES INSIPIDUS",
    status: "Context needed",
    detector: "Isolation Forest",
    score: 0.19,
    lower: 0.72,
    upper: 5.33,
    cases: 5,
    serious: 5,
    quarter: "2025 Q2",
    trend: [0, 1, 0, 1, 1, 2, 2, 5],
    reasons: [
      "Unusual growth and seriousness features",
      "Sparse contingency table creates a wide interval",
      "Statistical stability rule is not met",
    ],
  },
];

export const detectorMetrics = [
  { name: "Report count", recall: 0.54, precision: 0.09, burden: 80 },
  { name: "ROR", recall: 0.69, precision: 0.12, burden: 80 },
  { name: "PRR", recall: 0.65, precision: 0.11, burden: 80 },
  { name: "Isolation Forest", recall: 0.77, precision: 0.14, burden: 60 },
];
