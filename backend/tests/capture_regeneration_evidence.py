#!/usr/bin/env python3
"""
Capture a real regeneration before/after on the deployed backend.

Creates a project, builds the bible, generates shot 1, runs the consistency
check (BEFORE), then calls POST /regenerate (which re-runs generate + check),
and captures the AFTER scores. Writes the evidence to
docs/regeneration-evidence.json for the README Proof section.

This proves the closed-loop architecture is real, not theoretical.
"""
import requests, time, json, sys
from pathlib import Path

BASE = "https://auteur-dev-jbkbgthudq-uc.a.run.app"
LOGLINE = "A noir detective in 1920s Shanghai hunts a ghost from his past."

def step(n, msg): print(f"\n[{n}] {msg}")

# 1. Create project
step(1, "create project")
r = requests.post(f"{BASE}/api/projects", json={"logline": LOGLINE}, timeout=30)
assert r.status_code == 200, r.text
pid = r.json()["project_id"]
print(f"  project: {pid}")

# 2. Build bible (~40s)
step(2, "build bible (Parallel Search + Gemini 3.1 Pro)")
t0 = time.time()
r = requests.post(f"{BASE}/api/projects/{pid}/build-bible", timeout=120)
print(f"  bible built in {round(time.time()-t0,1)}s, refs={r.json().get('references_count',0)}")

# 3. Get shots
step(3, "get shots")
r = requests.get(f"{BASE}/api/projects/{pid}/shots", timeout=30)
shots = r.json()["shots"]
shot = shots[0]
sid = shot["id"]
print(f"  shot 1: {sid} (order={shot['order']})")

# 4. Generate shot (Veo + Chirp + Lyria) — ~90s
step(4, "generate shot 1 (Veo + Chirp + Lyria)")
t0 = time.time()
r = requests.post(f"{BASE}/api/projects/{pid}/shots/{sid}/generate", json={"bible_version": 1}, timeout=300)
gen1 = r.json()
print(f"  generated in {round(time.time()-t0,1)}s, modalities: {[(k,v.get('status')) for k,v in gen1.get('modalities',{}).items()]}")

# 5. Check consistency (BEFORE)
step(5, "consistency check (BEFORE regeneration)")
r = requests.post(f"{BASE}/api/projects/{pid}/shots/check-all", timeout=120)
before = r.json()
before_shot = next((s for s in before["shots"] if s["shot_id"] == sid), before["shots"][0])
print(f"  BEFORE: overall={before_shot.get('overall')}, drift={before_shot.get('drift_score')}, verdict={before_shot.get('recommendation')}")

# 6. Regenerate (re-runs generate + check — ~90s)
step(6, "regenerate shot 1 (re-runs generate + consistency check)")
t0 = time.time()
r = requests.post(f"{BASE}/api/projects/{pid}/shots/{sid}/regenerate", json={"reason": "drift above threshold", "bible_version": 1}, timeout=300)
regen = r.json()
print(f"  regenerated in {round(time.time()-t0,1)}s")
after_check = regen.get("consistency", {})
print(f"  AFTER:  overall={after_check.get('overall')}, drift={after_check.get('drift_score')}, verdict={after_check.get('recommendation')}")

# 7. Write the evidence
evidence = {
    "project_id": pid,
    "shot_id": sid,
    "logline": LOGLINE,
    "before": {
        "overall": before_shot.get("overall"),
        "drift_score": before_shot.get("drift_score"),
        "recommendation": before_shot.get("recommendation"),
        "per_attribute": {
            "face_identity": before_shot.get("face_identity"),
            "age_appearance": before_shot.get("age_appearance"),
            "beard_facial_hair": before_shot.get("beard_facial_hair"),
            "wardrobe": before_shot.get("wardrobe"),
        },
    },
    "after": {
        "overall": after_check.get("overall"),
        "drift_score": after_check.get("drift_score"),
        "recommendation": after_check.get("recommendation"),
        "per_attribute": {
            "face_identity": after_check.get("face_identity"),
            "age_appearance": after_check.get("age_appearance"),
            "beard_facial_hair": after_check.get("beard_facial_hair"),
            "wardrobe": after_check.get("wardrobe"),
        },
    },
    "threshold": 0.25,
    "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "note": "Real before/after from the deployed backend. The regenerate endpoint re-runs the generation pipeline (Veo + Chirp + Lyria with the Bible injected) and then re-runs the Consistency Check Agent, so the before/after scores are from two independent Veo 3.1 generations of the same shot with the same Bible context.",
}
out = Path(__file__).resolve().parents[2] / "docs" / "regeneration-evidence.json"
out.write_text(json.dumps(evidence, indent=2))
print(f"\n[7] evidence written to {out}")
print(f"\n{'='*60}")
print(f"BEFORE: overall={before_shot.get('overall')} drift={before_shot.get('drift_score')} [{before_shot.get('recommendation')}]")
print(f"AFTER:  overall={after_check.get('overall')} drift={after_check.get('drift_score')} [{after_check.get('recommendation')}]")
print(f"{'='*60}")
