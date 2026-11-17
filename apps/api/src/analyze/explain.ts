import type { Assessment, Criterion, CriterionBasis, CriterionRole, ParamId } from "../scoring/index.js";

/**
 * Explanation of an assessment: which criteria make the site relevant, which make it less relevant, which
 * decide the outcome, what is missing and what the numbers rest on. Built only from the assessment and the
 * criteria definitions: it adds no information, it orders what is already there.
 */
export type ExplainedCriterion = {
  param: ParamId;
  /** Points added to the total (out of 100). */
  contribution: number;
  /** Points lost compared with a perfect score on this criterion. */
  loss: number;
  role?: CriterionRole;
  basis?: CriterionBasis;
  rationale?: string;
};

export type Explanation = {
  /** Criteria scoring 0.7 or more, largest contribution first. */
  strengths: ExplainedCriterion[];
  /** Criteria scoring under 0.7, largest loss first. */
  weaknesses: ExplainedCriterion[];
  /** Required criteria the site fails: they decide the outcome whatever the total. */
  decisive: ParamId[];
  /** Criteria with no data: neither counted for nor against the site. */
  missing: ParamId[];
  /** Values carrying a data-quality flag. */
  flagged: { param: ParamId; flags: string[] }[];
  /** Share of the total (0 to 1) resting on criteria whose numbers are expert judgements, not measurements. */
  expertShare: number;
};

const STRENGTH_THRESHOLD = 0.7;
const round1 = (x: number): number => Math.round(x * 10) / 10;

export function explain(assessment: Assessment, criteria: Criterion[]): Explanation {
  const strengths: ExplainedCriterion[] = [];
  const weaknesses: ExplainedCriterion[] = [];
  const flagged: { param: ParamId; flags: string[] }[] = [];
  let expert = 0;
  let known = 0;
  assessment.criteria.forEach((score, i) => {
    const definition = criteria[i];
    if (score.verdict === "missing") return;
    known += score.maxContribution;
    if (definition.basis !== "lunar_measurement" && definition.basis !== "mission_requirement") expert += score.maxContribution;
    if (score.flags) flagged.push({ param: score.param, flags: score.flags });
    const item: ExplainedCriterion = {
      param: score.param,
      contribution: round1(score.contribution),
      loss: round1(score.maxContribution - score.contribution),
      ...(definition.role ? { role: definition.role } : {}),
      ...(definition.basis ? { basis: definition.basis } : {}),
      ...(definition.rationale ? { rationale: definition.rationale } : {}),
    };
    (score.score >= STRENGTH_THRESHOLD ? strengths : weaknesses).push(item);
  });
  strengths.sort((a, b) => b.contribution - a.contribution);
  weaknesses.sort((a, b) => b.loss - a.loss);
  return {
    strengths,
    weaknesses,
    decisive: assessment.failed,
    missing: assessment.missing,
    flagged,
    expertShare: known > 0 ? Math.round((100 * expert) / known) / 100 : 0,
  };
}
