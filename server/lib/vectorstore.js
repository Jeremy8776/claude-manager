// @ts-check

const fs = require('fs');
const path = require('path');
const { DATA_DIR } = require('./config');

const DEFAULT_VECTOR_FILE = path.join(DATA_DIR, 'vectors.json');
const INDEX_STALE_FILE = path.join(DATA_DIR, 'index-stale.json');

const VECTOR_WEIGHT = 0.6;
const LEXICAL_WEIGHT = 0.4;
const LEXICAL_SKILL_WEIGHT = 0.4;
const LEXICAL_SECTION_WEIGHT = 0.3;
const LEXICAL_TEXT_WEIGHT = 0.3;

/**
 * Mark the vector index as stale. The next /api/index/status response will
 * carry { stale: true, staleReason, staleSince } so the dashboard + onboarding
 * surfaces can prompt for a rebuild. Skill-source mutations (link / unlink /
 * import / sync apply) call this — the index goes out of date the moment the
 * walked skill set changes.
 *
 * @param {string=} reason   Short reason string surfaced to the user.
 */
function markIndexStale(reason) {
  try {
    if (!fs.existsSync(path.dirname(INDEX_STALE_FILE))) {
      fs.mkdirSync(path.dirname(INDEX_STALE_FILE), { recursive: true });
    }
    fs.writeFileSync(
      INDEX_STALE_FILE,
      JSON.stringify(
        {
          stale: true,
          reason: reason || 'Skill set changed',
          since: new Date().toISOString(),
        },
        null,
        2,
      ),
      'utf8',
    );
  } catch {
    /* best-effort — stale flag is advisory, not load-bearing */
  }
}

/** Clear the stale flag (called after a successful index rebuild). */
function clearIndexStale() {
  try {
    if (fs.existsSync(INDEX_STALE_FILE)) fs.unlinkSync(INDEX_STALE_FILE);
  } catch {
    /* best-effort */
  }
}

/**
 * Read the current stale state. Returns { stale: false } when no sidecar
 * exists; otherwise the persisted shape.
 *
 * @returns {{ stale: boolean, reason?: string, since?: string }}
 */
function getIndexStale() {
  try {
    const raw = fs.readFileSync(INDEX_STALE_FILE, 'utf8');
    const parsed = JSON.parse(raw);
    if (parsed?.stale) return { stale: true, reason: parsed.reason, since: parsed.since };
  } catch {
    /* missing or unreadable — treat as not stale */
  }
  return { stale: false };
}

/**
 * @typedef {import('./chunker').SkillChunk & { vector: number[] }} VectorRecord
 * @typedef {{ version: string, updatedAt: string | null, model: string | null, records: VectorRecord[] }} VectorStore
 */

/**
 * @param {string=} filePath
 * @returns {VectorStore}
 */
function loadVectorStore(filePath = DEFAULT_VECTOR_FILE) {
  try {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return normalizeStore(data);
  } catch {
    return emptyStore();
  }
}

/**
 * @param {VectorStore} store
 * @param {string=} filePath
 */
function saveVectorStore(store, filePath = DEFAULT_VECTOR_FILE) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(normalizeStore(store), null, 2), 'utf8');
}

/**
 * @param {VectorStore} store
 * @param {VectorRecord[]} records
 * @param {string} model
 * @returns {VectorStore}
 */
function upsertVectors(store, records, model) {
  const next = normalizeStore(store);
  const byId = new Map(next.records.map((record) => [record.id, record]));
  records.forEach((record) => byId.set(record.id, record));
  next.records = Array.from(byId.values()).sort((a, b) => a.id.localeCompare(b.id));
  next.model = model;
  next.updatedAt = new Date().toISOString();
  return next;
}

/**
 * @param {VectorRecord[]} records
 * @param {string} model
 * @returns {VectorStore}
 */
function replaceVectors(records, model) {
  return {
    version: '1.0',
    updatedAt: new Date().toISOString(),
    model,
    records: [...records].sort((a, b) => a.id.localeCompare(b.id)),
  };
}

/**
 * @param {import('./vectorstore').VectorStore} store
 * @param {number[]} queryVector
 * @param {{ limit?: number, skillId?: string }=} options
 */
function searchVectors(store, queryVector, options = {}) {
  const limit = options.limit || 10;
  return normalizeStore(store)
    .records.filter((record) => !options.skillId || record.skillId === options.skillId)
    .map((record) => ({ ...record, score: cosineSimilarity(queryVector, record.vector) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

/**
 * Hybrid search: combine vector cosine score with lexical term matching.
 * Lexical boosts chunks where the query terms appear in the skill ID (weight
 * 0.4), section title (weight 0.3), or chunk text (weight 0.3). The final
 * score is 0.6 * vectorScore + 0.4 * lexicalScore.
 *
 * @param {import('./vectorstore').VectorStore} store
 * @param {number[]} queryVector
 * @param {string} query  Original query text for lexical matching.
 * @param {{ limit?: number, diversifyBySkill?: boolean }=} options
 * @returns {Array<import('./vectorstore').VectorRecord & { score: number, lexicalScore: number }>}
 */
function hybridSearch(store, queryVector, query, options = {}) {
  const limit = options.limit || 10;
  const terms = extractQueryTerms(query);
  if (!terms.length) {
    const vectorResults = searchVectors(store, queryVector, {
      limit: options.diversifyBySkill ? Infinity : limit,
    }).map((/** @type {import('./vectorstore').VectorRecord & { score: number }} */ r) => ({
      ...r,
      lexicalScore: 0,
    }));
    return limitSearchResults(vectorResults, limit, options);
  }

  const results = normalizeStore(store)
    .records.map((record) => {
      const vectorScore = cosineSimilarity(queryVector, record.vector);
      const lexicalScore = computeLexicalScore(record, terms);
      return {
        ...record,
        score: VECTOR_WEIGHT * vectorScore + LEXICAL_WEIGHT * lexicalScore,
        lexicalScore,
      };
    })
    .sort((a, b) => b.score - a.score);
  return limitSearchResults(results, limit, options);
}

/**
 * @param {Array<import('./vectorstore').VectorRecord & { score: number, lexicalScore: number }>} results
 * @param {number} limit
 * @param {{ diversifyBySkill?: boolean }} options
 * @returns {Array<import('./vectorstore').VectorRecord & { score: number, lexicalScore: number }>}
 */
function limitSearchResults(results, limit, options) {
  if (!options.diversifyBySkill) return results.slice(0, limit);

  const picked = [];
  const deferred = [];
  const seenSkills = new Set();
  for (const result of results) {
    const skillGroup = bareSkillId(result.skillId);
    if (!seenSkills.has(skillGroup)) {
      picked.push(result);
      seenSkills.add(skillGroup);
    } else {
      deferred.push(result);
    }
    if (picked.length >= limit) return picked;
  }

  for (const result of deferred) {
    if (picked.length >= limit) break;
    picked.push(result);
  }
  return picked;
}

/**
 * Source-linked skills use `<sourceId>:<skillId>`. For search result diversity,
 * group linked copies and built-in copies by their bare skill ID.
 * @param {string} skillId
 */
function bareSkillId(skillId) {
  return (
    String(skillId || '')
      .split(':')
      .pop() || String(skillId || '')
  );
}

/**
 * Strip common suffixes for loose matching, but preserve enough characters
 * to avoid false matches (e.g. "string" → "str", "rules" → "rul").
 * Minimum remaining length of 4 ensures stems like "make" stay intact.
 * @param {string} word
 */
function stripSuffix(word) {
  let stem = word;
  for (const suffix of ['ing', 'ed', 'es', 's']) {
    if (stem.endsWith(suffix) && stem.length - suffix.length >= 4) {
      stem = stem.slice(0, -suffix.length);
      break;
    }
  }
  return stem;
}

/**
 * Extract meaningful lowercase terms from a query string.
 * Removes common stopwords and short tokens.
 * @param {string} query
 * @returns {string[]}
 */
function extractQueryTerms(query) {
  const stopwords = new Set([
    'the',
    'a',
    'an',
    'is',
    'are',
    'was',
    'were',
    'be',
    'been',
    'being',
    'have',
    'has',
    'had',
    'do',
    'does',
    'did',
    'will',
    'would',
    'could',
    'should',
    'may',
    'might',
    'shall',
    'can',
    'need',
    'dare',
    'ought',
    'used',
    'to',
    'of',
    'in',
    'for',
    'on',
    'with',
    'at',
    'by',
    'from',
    'as',
    'into',
    'through',
    'during',
    'before',
    'after',
    'above',
    'below',
    'between',
    'out',
    'off',
    'over',
    'under',
    'again',
    'further',
    'then',
    'once',
    'here',
    'there',
    'when',
    'where',
    'why',
    'how',
    'all',
    'each',
    'every',
    'both',
    'few',
    'more',
    'most',
    'other',
    'some',
    'such',
    'no',
    'nor',
    'not',
    'only',
    'own',
    'same',
    'so',
    'than',
    'too',
    'very',
    'just',
    'because',
    'but',
    'and',
    'or',
    'if',
    'while',
    'that',
    'this',
    'it',
    'its',
    'i',
    'me',
    'my',
    'we',
    'our',
    'you',
    'your',
    'he',
    'him',
    'his',
    'she',
    'her',
    'they',
    'them',
    'their',
    'what',
    'which',
    'who',
    'whom',
    'about',
    'up',
  ]);
  return query
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 2 && !stopwords.has(t));
}

/**
 * Compute a lexical relevance score (0-1) for a record against query terms.
 * Matches in skillId get weight LEXICAL_SKILL_WEIGHT, section title
 * LEXICAL_SECTION_WEIGHT, chunk text LEXICAL_TEXT_WEIGHT.
 * Supports prefix matching: "files" matches "file" in "file-search".
 * @param {import('./vectorstore').VectorRecord} record
 * @param {string[]} terms
 * @returns {number}
 */
function computeLexicalScore(record, terms) {
  const skillLower = (record.skillId || '').toLowerCase();
  const sectionLower = (record.section || '').toLowerCase();
  const textLower = (record.text || '').toLowerCase();
  const textWords = new Set(textLower.split(/\s+/).filter(Boolean));
  const sectionWords = new Set(sectionLower.split(/[\s-]+/).filter(Boolean));
  const skillWords = new Set(skillLower.split(/[\s:-]+/).filter(Boolean));

  let skillHits = 0;
  let sectionHits = 0;
  let textHits = 0;

  for (const term of terms) {
    const termStem = stripSuffix(term);
    // Check full term, stemmed term, and prefix matches
    /**
     * @param {string} word
     */
    const matches = (word) =>
      word === term ||
      word === termStem ||
      word.startsWith(term) ||
      word.startsWith(termStem) ||
      (term.length > 3 && term.startsWith(word));
    /** @param {string} w */
    const matchWord = (w) => matches(w);
    const textMatch = [...textWords].some(matchWord);
    const sectionMatch = [...sectionWords].some(matchWord);
    const skillMatch = [...skillWords].some(matchWord);

    if (textMatch) textHits++;
    if (sectionMatch) sectionHits++;
    if (skillMatch) skillHits++;
  }

  const maxHits = terms.length;
  if (!maxHits) return 0;

  return (
    LEXICAL_SKILL_WEIGHT * (skillHits / maxHits) +
    LEXICAL_SECTION_WEIGHT * (sectionHits / maxHits) +
    LEXICAL_TEXT_WEIGHT * (textHits / maxHits)
  );
}

/**
 * @param {number[]} a
 * @param {number[]} b
 */
function cosineSimilarity(a, b) {
  if (!a.length || a.length !== b.length) return 0;
  let dot = 0;
  let aMag = 0;
  let bMag = 0;
  for (let i = 0; i < a.length; i += 1) {
    const av = a[i] ?? 0;
    const bv = b[i] ?? 0;
    dot += av * bv;
    aMag += av * av;
    bMag += bv * bv;
  }
  if (!aMag || !bMag) return 0;
  return dot / (Math.sqrt(aMag) * Math.sqrt(bMag));
}

function emptyStore() {
  return { version: '1.0', updatedAt: null, model: null, records: [] };
}

/**
 * @param {unknown} data
 * @returns {VectorStore}
 */
function normalizeStore(data) {
  if (!data || typeof data !== 'object') return emptyStore();
  const store = /** @type {Partial<VectorStore>} */ (data);
  return {
    version: store.version || '1.0',
    updatedAt: store.updatedAt || null,
    model: store.model || null,
    records: Array.isArray(store.records) ? store.records.filter(isVectorRecord) : [],
  };
}

/**
 * @param {unknown} value
 * @returns {value is VectorRecord}
 */
function isVectorRecord(value) {
  if (!value || typeof value !== 'object') return false;
  const record = /** @type {Partial<VectorRecord>} */ (value);
  return !!(record.id && record.skillId && record.text && Array.isArray(record.vector));
}

module.exports = {
  DEFAULT_VECTOR_FILE,
  INDEX_STALE_FILE,
  loadVectorStore,
  saveVectorStore,
  upsertVectors,
  replaceVectors,
  searchVectors,
  hybridSearch,
  cosineSimilarity,
  markIndexStale,
  clearIndexStale,
  getIndexStale,
};
