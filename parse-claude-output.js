/**
 * parse-claude-output.js
 * Extracts individual website files from Claude's raw text response.
 * Used inside the n8n "Parse Claude Output" Code node.
 */

/**
 * Parses Claude's response into a map of { filename → file content }.
 *
 * Supports two formats:
 *   Multi-file  — Claude separates files with <!-- FILE: filename --> markers
 *   Single-file — Claude returns a bare HTML document (fallback)
 *
 * @param  {string} rawOutput  The full text from Claude's response
 * @returns {Object}           { "index.html": "...", "style.css": "...", ... }
 */
function parseClaudeOutput(rawOutput) {
  if (!rawOutput || typeof rawOutput !== 'string') {
    throw new Error('parseClaudeOutput: rawOutput must be a non-empty string');
  }

  const files = {};

  // ── Multi-file format ────────────────────────────────────────────────────────
  // Matches <!-- FILE: filename --> followed by content up to next marker or EOF
  const fileMarkerRe = /<!--\s*FILE:\s*(\S+)\s*-->([\s\S]*?)(?=<!--\s*FILE:|$)/g;
  let m;

  while ((m = fileMarkerRe.exec(rawOutput)) !== null) {
    const filename = m[1].trim();
    const content  = m[2].trim();
    if (content.length > 0) {
      files[filename] = content;
    }
  }

  // ── Single-file fallback ─────────────────────────────────────────────────────
  if (Object.keys(files).length === 0) {
    const doctypeMatch = rawOutput.match(/<!DOCTYPE\s+html[\s\S]*/i);
    const htmlTagMatch = rawOutput.match(/<html[\s\S]*/i);
    const htmlContent  = doctypeMatch || htmlTagMatch;

    if (htmlContent) {
      files['index.html'] = htmlContent[0].trim();
    }
  }

  if (Object.keys(files).length === 0) {
    throw new Error(
      'parseClaudeOutput: could not extract any files from Claude output. ' +
      'Ensure Claude returned HTML or used <!-- FILE: --> markers.'
    );
  }

  return files;
}

// ── n8n Code node entry point ────────────────────────────────────────────────
// Paste everything below this line into the n8n Code node body.
// Remove the module.exports block at the bottom before pasting.

const rawOutput = $('Call Claude API').first().json.content[0].text;
const formData  = $('Validate Input').first().json.formData;
const recordId  = $('Build Claude Prompt').first().json.recordId;
const requestId = $('Validate Input').first().json.requestId;

const files = parseClaudeOutput(rawOutput);

return [{ json: { files, formData, recordId, requestId } }];

// ── For local testing outside n8n ────────────────────────────────────────────
if (typeof module !== 'undefined') {
  module.exports = { parseClaudeOutput };
}
