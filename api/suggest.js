/* Khaana — AI dish suggestions (Vercel serverless function).
 *
 * The Anthropic API key lives here, in a Vercel environment variable, and never
 * reaches the browser. The browser posts a validated pantry payload; this
 * function builds the prompt itself.
 *
 * Deliberately NOT a general-purpose Claude proxy: it accepts no free-form
 * prompt text. Everything the model sees is assembled here from ingredient ids
 * and enum-checked filters, so a stranger who finds this endpoint can only ask
 * "what can I cook with these ingredients", not run arbitrary inference on the
 * account's key.
 */

const MODEL = 'claude-opus-5';
const ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages';

const MAX_INGREDIENTS = 60;
const MAX_ID_LENGTH = 40;
const ID_PATTERN = /^[a-z0-9-]+$/;

const DIETS = new Set([
  'vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free', 'no-onion-garlic',
]);
const EQUIPMENT = new Set([
  'stovetop', 'pressure-cooker', 'steamer', 'blender', 'oven', 'kadhai', 'tawa',
]);
const SKILLS = new Set(['easy', 'moderate', 'advanced']);

/* The shape we force the model into, so the client never parses prose. */
const SCHEMA = {
  type: 'object',
  properties: {
    suggestions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          region: { type: 'string' },
          summary: { type: 'string' },
          usesFromPantry: { type: 'array', items: { type: 'string' } },
          alsoNeeds: { type: 'array', items: { type: 'string' } },
          approxMinutes: { type: 'integer' },
          difficulty: { type: 'string', enum: ['easy', 'moderate', 'advanced'] },
          note: { type: 'string' },
        },
        required: [
          'name', 'region', 'summary', 'usesFromPantry',
          'alsoNeeds', 'approxMinutes', 'difficulty', 'note',
        ],
        additionalProperties: false,
      },
    },
  },
  required: ['suggestions'],
  additionalProperties: false,
};

function cleanIdList(value, allowed) {
  if (!Array.isArray(value)) return [];
  const out = [];
  for (const raw of value.slice(0, MAX_INGREDIENTS)) {
    if (typeof raw !== 'string') continue;
    const id = raw.trim().toLowerCase();
    if (!id || id.length > MAX_ID_LENGTH || !ID_PATTERN.test(id)) continue;
    if (allowed && !allowed.has(id)) continue;
    if (!out.includes(id)) out.push(id);
  }
  return out;
}

function buildPrompt(input) {
  const lines = [
    'A home cook has the following ingredients available:',
    input.ingredients.join(', ') || '(nothing specified)',
    '',
    'They already have basic staples: salt, cooking oil, water and sugar.',
  ];

  if (input.diets.length) {
    lines.push('', 'Dietary requirements that must be respected: ' + input.diets.join(', ') + '.');
  }
  if (input.maxMinutes) {
    lines.push('', 'They have about ' + input.maxMinutes + ' minutes.');
  }
  if (input.skill) {
    lines.push('', 'Their cooking confidence is: ' + input.skill + '.');
  }
  if (input.equipment.length) {
    lines.push('', 'Equipment they own: ' + input.equipment.join(', ') + '.');
  }
  if (input.exclude.length) {
    lines.push(
      '',
      'Khaana already has its own recipes for these dishes, so do NOT suggest them: ' +
        input.exclude.join(', ') + '.'
    );
  }

  lines.push(
    '',
    'Suggest up to 5 Indian dishes they could realistically cook. Prefer dishes that',
    'use a lot of what they already have. Be honest in "alsoNeeds" about what is',
    'genuinely missing — do not pretend a dish is makeable when it is not. Use the',
    '"note" field for the single most useful piece of practical advice for that dish',
    '(a technique cue, a common mistake, or a substitution that works).'
  );

  return lines.join('\n');
}

const SYSTEM = [
  'You suggest Indian home-cooking ideas for Khaana, a site about regional Indian cuisine.',
  'You are the exploratory tier: your suggestions sit alongside a small set of carefully',
  'written recipes and are clearly labelled to readers as AI-generated ideas rather than',
  'tested recipes. Because of that, be accurate and honest rather than impressive.',
  '',
  'Name real, recognised dishes from actual Indian regional traditions — do not invent',
  'fusion dishes or make up regional attributions. If the pantry genuinely does not',
  'support many dishes, return fewer suggestions rather than padding the list.',
  'Keep "summary" to one sentence. Keep "note" to one sentence.',
].join('\n');

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Use POST.' });
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    // Misconfiguration, not a user error — say so plainly rather than failing opaquely.
    return res.status(503).json({
      error: 'AI suggestions are not configured on this deployment.',
    });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = null; }
  }
  if (!body || typeof body !== 'object') {
    return res.status(400).json({ error: 'Expected a JSON body.' });
  }

  const input = {
    ingredients: cleanIdList(body.ingredients, null).map(function (id) {
      return id.replace(/-/g, ' ');
    }),
    diets: cleanIdList(body.diets, DIETS),
    equipment: cleanIdList(body.equipment, EQUIPMENT),
    exclude: cleanIdList(body.exclude, null).map(function (id) {
      return id.replace(/-/g, ' ');
    }),
    skill: SKILLS.has(body.skill) ? body.skill : null,
    maxMinutes: Number.isInteger(body.maxMinutes) && body.maxMinutes > 0 && body.maxMinutes <= 600
      ? body.maxMinutes
      : null,
  };

  if (input.ingredients.length === 0) {
    return res.status(400).json({ error: 'Tick at least one ingredient first.' });
  }

  try {
    const upstream = await fetch(ANTHROPIC_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: MODEL,
        // Thinking is on by default on this model and max_tokens caps thinking
        // plus response text together, so leave headroom above the JSON itself.
        max_tokens: 8000,
        output_config: {
          effort: 'low',
          format: { type: 'json_schema', schema: SCHEMA },
        },
        system: SYSTEM,
        messages: [{ role: 'user', content: buildPrompt(input) }],
      }),
    });

    if (!upstream.ok) {
      const detail = await upstream.text();
      console.error('Anthropic error', upstream.status, detail.slice(0, 500));
      const status = upstream.status === 429 ? 429 : 502;
      return res.status(status).json({
        error: upstream.status === 429
          ? 'Too many requests right now — try again in a moment.'
          : 'The suggestion service is unavailable right now.',
      });
    }

    const data = await upstream.json();

    // A safety decline returns HTTP 200 with an empty/partial content array,
    // so check stop_reason before reading content.
    if (data.stop_reason === 'refusal') {
      return res.status(200).json({ suggestions: [], refused: true });
    }

    const textBlock = (data.content || []).find(function (b) { return b.type === 'text'; });
    if (!textBlock) {
      return res.status(502).json({ error: 'Empty response from the suggestion service.' });
    }

    let parsed;
    try {
      parsed = JSON.parse(textBlock.text);
    } catch (e) {
      console.error('Unparseable model output', textBlock.text.slice(0, 500));
      return res.status(502).json({ error: 'Could not read the suggestion response.' });
    }

    res.setHeader('cache-control', 'no-store');
    return res.status(200).json({ suggestions: parsed.suggestions || [] });
  } catch (err) {
    console.error('suggest handler failed', err);
    return res.status(502).json({ error: 'The suggestion service is unavailable right now.' });
  }
}
