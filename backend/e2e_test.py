import urllib.request
import json
import time

BASE = "http://127.0.0.1:8000"


def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


# ── /search ──────────────────────────────────────────────────────────────────
print("=== POST /search ===")
t = time.perf_counter()
res = post("/search", {"query": "Why did Stripe payouts fail?", "top_k": 3})
print(f"  totalMatches : {res['totalMatches']}")
for m in res["matches"]:
    print(f"  [{m['source']}] {m['title'][:65]}  score={m['relevanceScore']}")
    print(f"         reason: {m['matchReason']}")
print(f"  Elapsed: {(time.perf_counter() - t) * 1000:.0f}ms")

print()

# ── /analyze ─────────────────────────────────────────────────────────────────
print("=== POST /analyze ===")
t = time.perf_counter()
res = post("/analyze", {"query": "Why did Stripe payouts fail?"})
print(f"  rootCause       : {res['rootCause']}")
print(f"  confidenceScore : {res['confidenceScore']}")
print(f"  recommendedAction: {res['recommendedAction'][:90]}...")
print(f"  evidenceCount   : {res['supportingEvidenceCount']}")
print(f"  Elapsed: {(time.perf_counter() - t) * 1000:.0f}ms")

print()

# ── /challenge ───────────────────────────────────────────────────────────────
print("=== POST /challenge ===")
t = time.perf_counter()
res = post("/challenge", {"query": "Why did Stripe payouts fail?"})
ch = res["challenge"]
print(f"  riskLevel           : {ch['riskLevel']}")
print(f"  confidenceAdjustment: {ch['confidenceAdjustment']}")
print(f"  alternativeHypothesis: {ch['alternativeHypothesis'][:90]}...")
print(f"  recommendedNextCheck : {ch['recommendedNextCheck'][:90]}...")
print(f"  Elapsed: {(time.perf_counter() - t) * 1000:.0f}ms")

print()
print("All endpoints verified successfully via real Gemini on imaction project.")
