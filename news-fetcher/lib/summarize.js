import { spawn } from 'node:child_process';

const SUMMARY_MODEL = 'claude-haiku-4-5-20251001';
const SUMMARY_TIMEOUT_MS = 60_000;
const SUMMARY_MAX_BUDGET_USD = '0.10';

const PROMPT_PREFIX = `Summarize the following AI/ML news item in ONE sentence (max 25 words). Neutral, factual, no marketing fluff, no "this article", no editorializing. Output ONLY the sentence — no preamble, no quotes.

Item:
`;

export async function summarize(item) {
  const body = item.abstract || item.description || item.title;
  const prompt = `${PROMPT_PREFIX}Source: ${item.source_name}\nTitle: ${item.title}\n${body && body !== item.title ? `Body: ${body.slice(0, 1500)}\n` : ''}`;

  return await new Promise((resolve, reject) => {
    const args = [
      '-p',
      '--no-session-persistence',
      '--model', SUMMARY_MODEL,
      '--max-budget-usd', SUMMARY_MAX_BUDGET_USD,
    ];
    const child = spawn('claude', args, { stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '', err = '';
    const timer = setTimeout(() => { child.kill('SIGTERM'); reject(new Error('summarize timeout')); }, SUMMARY_TIMEOUT_MS);
    child.stdout.on('data', d => out += d);
    child.stderr.on('data', d => err += d);
    child.on('error', e => { clearTimeout(timer); reject(e); });
    child.on('close', code => {
      clearTimeout(timer);
      if (code !== 0) return reject(new Error(`claude exited ${code}: ${err.slice(0, 300)}`));
      const text = out.trim().replace(/^["'`]|["'`]$/g, '').replace(/\s+/g, ' ');
      if (!text) return reject(new Error('empty summary'));
      resolve(text);
    });
    child.stdin.end(prompt);
  });
}
