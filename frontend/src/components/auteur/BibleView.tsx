/**
 * BibleView — blueprint Section 30.2 row 4.
 * Tabbed: Characters | Locations | Wardrobe | Voice | Score | Style | Beats;
 * per-entry edit (inline, creates a new version via PATCH); version history.
 */
"use client";

import { useState } from "react";
import {
  User, MapPin, Shirt, Mic, Music, Palette, ListOrdered,
  ChevronRight, ExternalLink, BookOpen, Pencil, Check, X, Loader2,
} from "lucide-react";
import { useStudio } from "@/lib/store";
import { editBibleEntry } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import Image from "next/image";
import type { FilmBible, Reference } from "@/lib/types";

const TABS = [
  { id: "characters", label: "Characters", icon: User },
  { id: "locations", label: "Locations", icon: MapPin },
  { id: "wardrobes", label: "Wardrobe", icon: Shirt },
  { id: "voice", label: "Voice", icon: Mic },
  { id: "score", label: "Score", icon: Music },
  { id: "style", label: "Style", icon: Palette },
  { id: "beats", label: "Beats", icon: ListOrdered },
] as const;

export function BibleView() {
  const { bible, project, setView, setBible } = useStudio();
  const [editing, setEditing] = useState<{ entryId: string; field: string; value: string } | null>(null);
  const [saving, setSaving] = useState(false);

  if (!bible) {
    return <div className="p-8 text-sm text-zinc-500">No Bible yet.</div>;
  }

  async function handleSaveEdit() {
    if (!editing || !project) return;
    setSaving(true);
    try {
      const resp = await editBibleEntry(project.id, editing.entryId, editing.field, editing.value);
      setBible(resp.bible);
      setEditing(null);
    } catch (e) {
      console.error("edit failed:", e);
      setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
            <BookOpen className="h-3.5 w-3.5 text-teal-400" />
            Step 3 — Film Bible
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-zinc-100">The Film Bible</h2>
          <p className="mt-1 text-sm text-zinc-400">
            Typed, versioned, citable. Injected as context into every generation call.
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge className="border-0 bg-teal-500/15 text-teal-300">v{bible.version}</Badge>
          <span className="text-[10px] text-zinc-500">
            {bible.research_references.length} references
          </span>
        </div>
      </div>

      <div className="mb-4 rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-2.5 text-xs text-zinc-400">
        <span className="text-zinc-500">Logline:</span> {bible.logline}
      </div>

      <Tabs defaultValue="characters" className="w-full">
        <TabsList className="flex h-auto w-full flex-wrap gap-1 bg-zinc-900/60 p-1">
          {TABS.map((t) => (
            <TabsTrigger
              key={t.id}
              value={t.id}
              className="flex items-center gap-1.5 data-[state=active]:bg-teal-500/15 data-[state=active]:text-teal-300"
            >
              <t.icon className="h-3.5 w-3.5" />
              <span className="hidden text-xs sm:inline">{t.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="characters" className="mt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {bible.characters.map((c) => (
              <div key={c.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                {c.reference_image_url && !c.reference_image_url.startsWith("generated:") && (
                  <div className="relative mb-3 aspect-video overflow-hidden rounded-md border border-zinc-800">
                    <Image
                      src={c.reference_image_url}
                      alt={c.name}
                      fill
                      className="object-cover"
                      sizes="400px"
                    />
                  </div>
                )}
                <div className="flex items-baseline justify-between">
                  <EditableField
                    entryId={c.id}
                    field="name"
                    value={c.name}
                    editing={editing}
                    setEditing={setEditing}
                    onSave={handleSaveEdit}
                    saving={saving}
                    className="font-semibold text-zinc-100"
                  />
                  {c.age && <span className="text-xs text-zinc-500">age {c.age}</span>}
                </div>
                <EditableField
                  entryId={c.id}
                  field="description"
                  value={c.description}
                  editing={editing}
                  setEditing={setEditing}
                  onSave={handleSaveEdit}
                  saving={saving}
                  className="mt-1.5 text-xs text-zinc-400"
                  multiline
                />
                <dl className="mt-3 space-y-1 text-[11px]">
                  {c.voice_profile && (
                    <div>
                      <dt className="inline text-zinc-500">Voice: </dt>
                      <EditableField
                        entryId={c.id}
                        field="voice_profile"
                        value={c.voice_profile}
                        editing={editing}
                        setEditing={setEditing}
                        onSave={handleSaveEdit}
                        saving={saving}
                        className="inline text-zinc-300"
                      />
                    </div>
                  )}
                  {c.wardrobe && (
                    <div>
                      <dt className="inline text-zinc-500">Wardrobe: </dt>
                      <EditableField
                        entryId={c.id}
                        field="wardrobe"
                        value={c.wardrobe}
                        editing={editing}
                        setEditing={setEditing}
                        onSave={handleSaveEdit}
                        saving={saving}
                        className="inline text-zinc-300"
                      />
                    </div>
                  )}
                </dl>
                {c.references && c.references.length > 0 && <RefList refs={c.references} />}
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="locations" className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {bible.locations.map((l) => (
              <div key={l.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex items-baseline justify-between">
                  <h3 className="font-semibold text-zinc-100">{l.name}</h3>
                  {l.era && <Badge variant="outline" className="border-zinc-700 text-[10px] text-zinc-400">{l.era}</Badge>}
                </div>
                <p className="mt-1.5 text-xs text-zinc-400">{l.description}</p>
                {l.references && l.references.length > 0 && <RefList refs={l.references} />}
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="wardrobes" className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {bible.wardrobes.map((w) => {
              const char = bible.characters.find((c) => c.id === w.character_id);
              return (
                <div key={w.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                  <h3 className="font-semibold text-zinc-100">{w.garment}</h3>
                  <p className="mt-1 text-[11px] text-zinc-500">worn by {char?.name || "—"}</p>
                  <dl className="mt-2 space-y-0.5 text-[11px]">
                    {w.fabric && <div><dt className="inline text-zinc-500">Fabric: </dt><dd className="inline text-zinc-300">{w.fabric}</dd></div>}
                    {w.color && <div><dt className="inline text-zinc-500">Color: </dt><dd className="inline text-zinc-300">{w.color}</dd></div>}
                  </dl>
                </div>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="voice" className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {bible.voice_profiles.map((v) => {
              const char = bible.characters.find((c) => c.id === v.character_id);
              return (
                <div key={v.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                  <h3 className="font-semibold text-zinc-100">{v.voice_name}</h3>
                  <p className="mt-1 text-[11px] text-zinc-500">voice of {char?.name || "—"}</p>
                  <dl className="mt-2 space-y-0.5 text-[11px]">
                    <div><dt className="inline text-zinc-500">Model: </dt><dd className="inline font-mono text-teal-300">{v.voice_model}</dd></div>
                    {v.description && <div><dt className="inline text-zinc-500">Tone: </dt><dd className="inline text-zinc-300">{v.description}</dd></div>}
                  </dl>
                </div>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="score" className="mt-4">
          <div className="grid gap-3">
            {bible.score_motifs.map((m) => (
              <div key={m.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                <h3 className="font-semibold text-zinc-100">{m.name}</h3>
                <p className="mt-1 text-[11px] text-zinc-500">Lyria 2 prompt</p>
                <p className="mt-1 rounded bg-zinc-950/50 px-2 py-1.5 font-mono text-[11px] text-amber-200/80">{m.prompt}</p>
                <dl className="mt-2 space-y-0.5 text-[11px]">
                  {m.instrument && <div><dt className="inline text-zinc-500">Instrument: </dt><dd className="inline text-zinc-300">{m.instrument}</dd></div>}
                  {m.mood && <div><dt className="inline text-zinc-500">Mood: </dt><dd className="inline text-zinc-300">{m.mood}</dd></div>}
                </dl>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="style" className="mt-4">
          <div className="grid gap-3">
            {bible.style_anchors.map((s) => (
              <div key={s.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                <dl className="space-y-2 text-xs">
                  <div><dt className="text-zinc-500">Color grade</dt><dd className="text-zinc-200">{s.color_grade}</dd></div>
                  <div><dt className="text-zinc-500">Aspect ratio</dt><dd className="font-mono text-teal-300">{s.aspect_ratio}</dd></div>
                  {s.photographic_aesthetic && <div><dt className="text-zinc-500">Aesthetic</dt><dd className="text-zinc-300">{s.photographic_aesthetic}</dd></div>}
                  {s.mood && <div><dt className="text-zinc-500">Mood</dt><dd className="text-zinc-300">{s.mood}</dd></div>}
                </dl>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="beats" className="mt-4">
          <ol className="space-y-2">
            {bible.story_beats.map((b) => (
              <li key={b.id} className="flex gap-3 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-teal-500/15 font-mono text-xs font-bold text-teal-300">
                  {b.order}
                </span>
                <p className="text-sm text-zinc-300">{b.description}</p>
              </li>
            ))}
          </ol>
        </TabsContent>
      </Tabs>

      <div className="mt-8 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <span className="text-xs text-zinc-400">
          Bible v{bible.version} · {bible.characters.length} characters · {bible.locations.length} locations · {bible.story_beats.length} beats
        </span>
        <button
          onClick={() => setView("shots")}
          className="inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400"
        >
          Generate shots
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function RefList({ refs }: { refs: Reference[] }) {
  return (
    <div className="mt-3 border-t border-zinc-800 pt-2">
      <div className="mb-1 text-[10px] uppercase tracking-wide text-zinc-500">Citations</div>
      <div className="space-y-0.5">
        {refs.map((r, i) => (
          <a
            key={r.id || i}
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-[10px] text-teal-400/70 transition hover:text-teal-300"
          >
            <ExternalLink className="h-2.5 w-2.5" />
            <span className="truncate">{r.title}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

interface EditableFieldProps {
  entryId: string;
  field: string;
  value: string;
  editing: { entryId: string; field: string; value: string } | null;
  setEditing: (e: { entryId: string; field: string; value: string } | null) => void;
  onSave: () => void;
  saving: boolean;
  className?: string;
  multiline?: boolean;
}

function EditableField({
  entryId, field, value, editing, setEditing, onSave, saving, className, multiline,
}: EditableFieldProps) {
  const isEditing = editing?.entryId === entryId && editing?.field === field;
  const editValue = isEditing ? editing!.value : value;

  if (isEditing) {
    return (
      <span className={`inline-flex items-center gap-1 ${className || ""}`}>
        {multiline ? (
          <textarea
            autoFocus
            value={editValue}
            onChange={(e) => setEditing({ entryId, field, value: e.target.value })}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSave(); if (e.key === "Escape") setEditing(null); }}
            rows={2}
            className="w-full resize-none rounded border border-teal-500/50 bg-zinc-950 px-1.5 py-0.5 text-xs text-zinc-100 outline-none"
          />
        ) : (
          <input
            autoFocus
            value={editValue}
            onChange={(e) => setEditing({ entryId, field, value: e.target.value })}
            onKeyDown={(e) => { if (e.key === "Enter") onSave(); if (e.key === "Escape") setEditing(null); }}
            className="rounded border border-teal-500/50 bg-zinc-950 px-1.5 py-0.5 text-xs text-zinc-100 outline-none"
          />
        )}
        <button
          onClick={onSave}
          disabled={saving}
          className="grid h-5 w-5 place-items-center rounded bg-teal-500 text-zinc-950 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
        </button>
        <button
          onClick={() => setEditing(null)}
          disabled={saving}
          className="grid h-5 w-5 place-items-center rounded border border-zinc-700 text-zinc-400"
        >
          <X className="h-3 w-3" />
        </button>
      </span>
    );
  }

  return (
    <span
      onClick={() => setEditing({ entryId, field, value })}
      className={`group inline cursor-pointer rounded hover:bg-zinc-800/50 ${className || ""}`}
    >
      {value}
      <Pencil className="ml-1 inline h-2.5 w-2.5 text-zinc-600 opacity-0 transition group-hover:opacity-100" />
    </span>
  );
}
