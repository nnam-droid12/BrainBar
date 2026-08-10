# Verifying available Gemini model IDs

Vertex AI's Model Garden naming (and which models are GA vs. preview, and which
location serves them) changes over time and differs per project/allowlist, so don't
trust a model ID string from memory or documentation search — verify it against the
actual project before pinning it in `agents/config.py`.

Quickest check: call `generateContent` directly and read the HTTP status.

```bash
TOKEN=$(gcloud auth print-access-token)
PROJECT=your-gcp-project-id

for MODEL in gemini-2.5-pro gemini-2.5-flash; do
  curl -s -o /dev/null -w "%{http_code} $MODEL\n" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "https://us-central1-aiplatform.googleapis.com/v1/projects/$PROJECT/locations/us-central1/publishers/google/models/$MODEL:generateContent" \
    -d '{"contents":[{"role":"user","parts":[{"text":"hi"}]}]}'
done
```

`200` means the model ID is real and callable on that project/location; `404` means
either the ID is wrong or it isn't available in that location/allowlist yet.

As of this build, on this project: `gemini-2.5-pro` and `gemini-2.5-flash` are GA on
the regional `us-central1` endpoint (pinned as the defaults in `agents/config.py`).
`gemini-3.1-pro-preview` and `gemini-3-flash-preview` also resolve, but only on the
`global` location and only as preview models — re-run this check periodically and
move to the non-preview Gemini 3 IDs (and set `GOOGLE_CLOUD_LOCATION=global`) once
they reach GA.
