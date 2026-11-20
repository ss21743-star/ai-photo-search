// Photo Album frontend – uses the API Gateway generated SDK (apigClient.js)
const API_KEY = 'AbEX2ExMDh6AY9wQwNuAd4aajpPoaqdl2euDiaDI';
const apigClient = apigClientFactory.newClient({ apiKey: API_KEY });

const $ = (id) => document.getElementById(id);

// ---------- Search: GET /search?q= ----------
$('search-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = $('search-input').value.trim();
  if (!q) return;
  $('search-status').textContent = 'Searching…';
  $('results').innerHTML = '';
  try {
    const res = await apigClient.searchGet({ q: q }, {}, {});
    const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
    const results = (data && data.results) || [];
    $('search-status').textContent = results.length
      ? `${results.length} photo${results.length > 1 ? 's' : ''} found for “${q}”`
      : `No photos found for “${q}”`;
    results.forEach(addResult);
  } catch (err) {
    console.error(err);
    $('search-status').textContent = 'Search failed – see console for details.';
  }
});

function addResult(photo) {
  const fig = document.createElement('figure');
  const img = document.createElement('img');
  img.src = photo.url;
  img.alt = (photo.labels || []).join(', ');
  img.loading = 'lazy';
  const cap = document.createElement('figcaption');
  (photo.labels || []).forEach((l) => {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = l;
    cap.appendChild(tag);
  });
  fig.appendChild(img);
  fig.appendChild(cap);
  $('results').appendChild(fig);
}

// ---------- Upload: PUT /photos/{object} with x-amz-meta-customLabels ----------
$('upload-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = $('file-input').files[0];
  if (!file) return;
  const labels = $('labels-input').value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .join(', ');
  const key = `${Date.now()}-${file.name.replace(/[^A-Za-z0-9._-]/g, '_')}`;

  $('upload-status').textContent = 'Uploading…';
  try {
    await apigClient.photosObjectPut(
      {
        object: key,
        'Content-Type': file.type || 'image/jpeg',
        'x-amz-meta-customLabels': labels,
      },
      file,
      {}
    );
    $('upload-status').textContent =
      `Uploaded ${file.name}${labels ? ` with labels: ${labels}` : ''}. It will appear in search in a few seconds.`;
    $('upload-form').reset();
  } catch (err) {
    console.error(err);
    $('upload-status').textContent = 'Upload failed – see console for details.';
  }
});
