/*!
 * hxt.js
 * MIT © Gemmina Intelligence LLC
 *
 * Reference implementation for the .hxt format.
 * Runs in Node.js and modern browsers with no external dependencies.
 */

const HXT_VERSION = "0.1.0";
const MARKER_BEGIN = "<!--hxt:begin-->";
const MARKER_END = "<!--hxt:end-->";
const AI_BULK_THRESHOLD_CHARS = 500;
const AI_BULK_THRESHOLD_MS = 2000;
const SEMVER_RE = /^\d+\.\d+\.\d+$/;
const ISO_UTC_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const SHORT_HASH_RE = /^[0-9a-f]{16}$/;
const STATE_HASH_RE = /^sha256:[0-9a-f]{64}$/;

async function crystallize(currentText, authorType = "auto", prevLedger = null, options = {}) {
  const prevLength = Number.isInteger(options.prevLength) ? options.prevLength : 0;
  const elapsedMs = Number.isInteger(options.elapsedMs) ? options.elapsedMs : 9999;
  const nowMs = Number.isInteger(options.nowMs) ? options.nowMs : Date.now();
  const cleanText = stripHxtBlock(String(currentText));
  const delta = cleanText.length - prevLength;
  const type = resolveAuthorType(authorType, delta, elapsedMs);
  const fullHash = await sha256Full(cleanText);
  const isoNow = isoFromMs(nowMs);

  const step = {
    t: Math.floor(nowMs / 1000),
    type,
    delta,
    hash: fullHash.slice(0, 16)
  };

  const previousSteps = Array.isArray(prevLedger && prevLedger.ledger) ? prevLedger.ledger.slice() : [];
  const steps = previousSteps.concat(step);
  const ledger = {
    hxt_version: HXT_VERSION,
    genesis: prevLedger && typeof prevLedger.genesis === "string" ? prevLedger.genesis : isoNow,
    ledger: steps,
    final_seal: {
      sealed_at: isoNow,
      human_touch: computeHumanTouch(steps),
      state_hash: `sha256:${fullHash}`,
      step_count: steps.length
    }
  };

  const block = `${MARKER_BEGIN}\n${JSON.stringify(ledger, null, 2)}\n${MARKER_END}`;
  return cleanText ? `${cleanText}\n\n${block}` : block;
}

function inspect(fileContent) {
  const parts = extractHxtParts(String(fileContent));
  if (!parts) {
    return null;
  }

  try {
    return {
      ledger: JSON.parse(parts.jsonText),
      bodyText: parts.bodyText
    };
  } catch {
    return null;
  }
}

async function verify(fileContent) {
  const parts = extractHxtParts(String(fileContent));
  if (!parts) {
    return malformed("Required hxt markers were not found.");
  }

  let ledger;
  try {
    ledger = JSON.parse(parts.jsonText);
  } catch {
    return malformed("Ledger JSON could not be parsed.");
  }

  const schemaError = validateLedgerSchema(ledger);
  if (schemaError) {
    return malformed(schemaError);
  }

  const expectedHumanTouch = computeHumanTouch(ledger.ledger);
  if (ledger.final_seal.human_touch !== expectedHumanTouch) {
    return malformed("final_seal.human_touch does not match the ledger.");
  }

  const fullHash = await sha256Full(parts.bodyText);
  const shortHash = fullHash.slice(0, 16);
  const expectedStateHash = `sha256:${fullHash}`;
  const lastStep = ledger.ledger[ledger.ledger.length - 1];

  if (lastStep.hash !== shortHash) {
    return tampered("Last step hash does not match document content.", shortHash, lastStep.hash);
  }

  if (ledger.final_seal.state_hash !== expectedStateHash) {
    return tampered("state_hash does not match document content.", expectedStateHash, ledger.final_seal.state_hash);
  }

  return {
    valid: true,
    status: "ok",
    version: ledger.hxt_version,
    genesis: ledger.genesis,
    sealed_at: ledger.final_seal.sealed_at,
    step_count: ledger.final_seal.step_count,
    human_touch: ledger.final_seal.human_touch
  };
}

function summary(fileContent) {
  const parsed = inspect(String(fileContent));
  if (!parsed) {
    return null;
  }

  const ledger = parsed.ledger;
  const steps = Array.isArray(ledger.ledger) ? ledger.ledger : [];
  const humanTouch = typeof ledger.final_seal?.human_touch === "number" ? ledger.final_seal.human_touch : 0;

  return {
    version: ledger.hxt_version,
    genesis: ledger.genesis,
    sealed_at: ledger.final_seal && ledger.final_seal.sealed_at,
    step_count: steps.length,
    ai_steps: steps.filter((step) => step.type === "AI").length,
    human_steps: steps.filter((step) => step.type === "HUMAN").length,
    human_touch: humanTouch,
    label: humanTouchLabel(humanTouch)
  };
}

function stripHxtBlock(text) {
  const begin = text.indexOf(MARKER_BEGIN);
  if (begin === -1) {
    return text;
  }
  return text.slice(0, begin).trimEnd();
}

function extractHxtParts(fileContent) {
  const begin = fileContent.indexOf(MARKER_BEGIN);
  const end = fileContent.indexOf(MARKER_END);

  if (begin === -1 || end === -1 || end < begin) {
    return null;
  }

  return {
    bodyText: fileContent.slice(0, begin).trimEnd(),
    jsonText: fileContent.slice(begin + MARKER_BEGIN.length, end).trim()
  };
}

function resolveAuthorType(authorType, delta, elapsedMs) {
  if (authorType === "auto") {
    return Math.abs(delta) > AI_BULK_THRESHOLD_CHARS && elapsedMs < AI_BULK_THRESHOLD_MS ? "AI" : "HUMAN";
  }

  if (authorType === "AI" || authorType === "HUMAN") {
    return authorType;
  }

  throw new Error('authorType must be "AI", "HUMAN", or "auto".');
}

function computeHumanTouch(steps) {
  const total = steps.reduce((sum, step) => sum + Math.abs(step.delta), 0);
  if (total === 0) {
    return 0.0;
  }

  const human = steps
    .filter((step) => step.type === "HUMAN")
    .reduce((sum, step) => sum + Math.abs(step.delta), 0);

  return Math.round((human / total) * 1000) / 1000;
}

function humanTouchLabel(score) {
  if (score >= 0.7) {
    return "Sincere";
  }
  if (score >= 0.4) {
    return "Assisted";
  }
  if (score >= 0.1) {
    return "AI-heavy";
  }
  return "AI-generated";
}

function isoFromMs(nowMs) {
  return new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function isIsoUtcString(value) {
  return typeof value === "string" && ISO_UTC_RE.test(value) && !Number.isNaN(Date.parse(value));
}

function validateLedgerSchema(ledger) {
  if (!isPlainObject(ledger)) {
    return "Ledger root must be an object.";
  }
  if (!SEMVER_RE.test(String(ledger.hxt_version || ""))) {
    return "hxt_version must be a semantic version string.";
  }
  if (!isIsoUtcString(ledger.genesis)) {
    return "genesis must be an ISO 8601 UTC timestamp.";
  }
  if (!Array.isArray(ledger.ledger) || ledger.ledger.length === 0) {
    return "ledger must be a non-empty array.";
  }
  if (!isPlainObject(ledger.final_seal)) {
    return "final_seal must be an object.";
  }

  for (const step of ledger.ledger) {
    if (!isPlainObject(step)) {
      return "Each ledger step must be an object.";
    }
    if (!Number.isInteger(step.t)) {
      return "Each step.t must be an integer.";
    }
    if (step.type !== "AI" && step.type !== "HUMAN") {
      return 'Each step.type must be "AI" or "HUMAN".';
    }
    if (!Number.isInteger(step.delta)) {
      return "Each step.delta must be an integer.";
    }
    if (!SHORT_HASH_RE.test(String(step.hash || ""))) {
      return "Each step.hash must be 16 lowercase hex characters.";
    }
  }

  const seal = ledger.final_seal;
  if (!isIsoUtcString(seal.sealed_at)) {
    return "final_seal.sealed_at must be an ISO 8601 UTC timestamp.";
  }
  if (typeof seal.human_touch !== "number" || !Number.isFinite(seal.human_touch) || seal.human_touch < 0 || seal.human_touch > 1) {
    return "final_seal.human_touch must be a number between 0 and 1.";
  }
  if (!STATE_HASH_RE.test(String(seal.state_hash || ""))) {
    return 'final_seal.state_hash must look like "sha256:<64 hex chars>".';
  }
  if (!Number.isInteger(seal.step_count)) {
    return "final_seal.step_count must be an integer.";
  }
  if (seal.step_count !== ledger.ledger.length) {
    return "final_seal.step_count does not match ledger length.";
  }

  return null;
}

function malformed(reason) {
  return { valid: false, status: "malformed", reason };
}

function tampered(reason, expected, found) {
  return { valid: false, status: "tampered", reason, expected, found };
}

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function sha256Full(text) {
  if (globalThis.crypto && globalThis.crypto.subtle) {
    const bytes = new TextEncoder().encode(text);
    const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  if (typeof require === "function") {
    const crypto = require("crypto");
    return crypto.createHash("sha256").update(text, "utf8").digest("hex");
  }

  throw new Error("No SHA-256 implementation is available in this environment.");
}

const api = {
  HXT_VERSION,
  MARKER_BEGIN,
  MARKER_END,
  crystallize,
  inspect,
  verify,
  summary
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = api;
}

if (typeof globalThis !== "undefined") {
  globalThis.HXT = api;
}
