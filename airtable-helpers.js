/**
 * airtable-helpers.js
 * Utility functions for creating and updating SiteSnap records in Airtable.
 * Used inside n8n Code nodes — paste the relevant function body into the node.
 */

/**
 * Creates a new Website Request record from the Lovable form payload.
 * @param {Object} formData  - Sanitized form data from the Validate Input node
 * @param {string} airtableApiKey - Personal access token from process.env / $env
 * @param {string} baseId        - Airtable base ID (appXXXXXXXXXXXXXX)
 * @returns {string} The created record ID
 */
async function createAirtableRecord(formData, airtableApiKey, baseId) {
  const url = `https://api.airtable.com/v0/${baseId}/Website%20Requests`;

  const fields = {
    'Full Name':               formData.fullName        || '',
    'Email Address':           formData.email           || '',
    'Business / Brand Name':   formData.businessName    || '',
    'Industry / Niche':        formData.industry        || '',
    'Website Type':            formData.websiteType     || '',
    'Pages / Sections Needed': Array.isArray(formData.pagesNeeded)
                                 ? formData.pagesNeeded
                                 : [formData.pagesNeeded].filter(Boolean),
    'Design Style':            formData.designStyle     || '',
    'Color Preferences':       formData.colorPreferences|| '',
    'Tone / Voice':            formData.tone            || '',
    'Tagline or Headline':     formData.tagline         || '',
    'Services or Offerings':   formData.services        || '',
    'About / Bio':             formData.about           || '',
    'Social Media Links':      formData.socialLinks     || '',
    'Example Sites They Like': formData.exampleSites    || '',
    'Anything Else':           formData.anythingElse    || '',
    'Plan Selected':           formData.planSelected    || '',
    'Status':                  'Generating',
  };

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${airtableApiKey}`,
      'Content-Type':  'application/json',
    },
    body: JSON.stringify({ fields }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Airtable create failed (${response.status}): ${err}`);
  }

  const data = await response.json();
  return data.id; // e.g. "recXXXXXXXXXXXXXX"
}

/**
 * Updates an existing record after the site has been deployed.
 * @param {string} recordId      - The Airtable record ID returned by createAirtableRecord
 * @param {string} siteUrl       - The live Cloudflare Pages URL
 * @param {string} status        - 'Live' | 'Failed'
 * @param {string} airtableApiKey
 * @param {string} baseId
 */
async function updateAirtableRecord(recordId, siteUrl, status, airtableApiKey, baseId) {
  const url = `https://api.airtable.com/v0/${baseId}/Website%20Requests/${recordId}`;

  const fields = { 'Status': status };
  if (siteUrl) {
    fields['Generated Site URL'] = siteUrl;
  }

  const response = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${airtableApiKey}`,
      'Content-Type':  'application/json',
    },
    body: JSON.stringify({ fields }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Airtable update failed (${response.status}): ${err}`);
  }

  return await response.json();
}

module.exports = { createAirtableRecord, updateAirtableRecord };
