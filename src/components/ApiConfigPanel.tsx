import { useState } from "react";
import { createPortal } from "react-dom";
import {
  Settings, X, CheckCircle, AlertCircle, Wifi, WifiOff,
  Plus, Trash2, Eye, EyeOff, ToggleLeft, ToggleRight, GripVertical,
} from "lucide-react";
import { ApiConfig, ApiGroup } from "@/types/device";

interface Props {
  config: ApiConfig | null;
  onSave: (config: ApiConfig | null) => void;
  apiError?: string;
  usingMock: boolean;
}

function newGroup(): ApiGroup {
  return { id: crypto.randomUUID(), name: "", url: "", token: "", enabled: true };
}

export default function ApiConfigPanel({ config, onSave, apiError, usingMock }: Props) {
  const [open, setOpen] = useState(false);

  // Local editing state — initialise from saved config
  const [groups, setGroups] = useState<ApiGroup[]>(() => {
    if (config?.groups?.length) return config.groups.map((g) => ({ ...g, token: g.token ?? "" }));
    // Migrate legacy single-URL config
    if (config?.url) return [{ id: crypto.randomUUID(), name: "Default", url: config.url, token: config.token ?? "", enabled: true }];
    return [newGroup()];
  });

  const [showTokens, setShowTokens] = useState<Record<string, boolean>>({});

  // ── Group mutations ────────────────────────────────────────────────────────
  const updateGroup = (id: string, patch: Partial<ApiGroup>) =>
    setGroups((gs) => gs.map((g) => (g.id === id ? { ...g, ...patch } : g)));

  const addGroup = () => setGroups((gs) => [...gs, newGroup()]);

  const removeGroup = (id: string) =>
    setGroups((gs) => gs.length > 1 ? gs.filter((g) => g.id !== id) : gs);

  const toggleGroup = (id: string) =>
    updateGroup(id, { enabled: !groups.find((g) => g.id === id)?.enabled });

  const toggleToken = (id: string) =>
    setShowTokens((s) => ({ ...s, [id]: !s[id] }));

  // ── Save ──────────────────────────────────────────────────────────────────
  const handleSave = () => {
    const cleaned = groups.map((g) => ({
      ...g,
      name: g.name.trim() || `Group ${groups.indexOf(g) + 1}`,
      url: g.url.trim(),
      token: g.token?.trim() || undefined,
    }));
    const hasAny = cleaned.some((g) => g.url && g.enabled);
    if (!hasAny) { onSave(null); setOpen(false); return; }
    // Keep legacy url field pointing at first enabled group for backward compat
    const first = cleaned.find((g) => g.url && g.enabled);
    onSave({ url: first?.url ?? "", token: first?.token, groups: cleaned });
    setOpen(false);
  };

  const handleClear = () => {
    setGroups([newGroup()]);
    onSave(null);
    setOpen(false);
  };

  const enabledCount = groups.filter((g) => g.enabled && g.url.trim()).length;

  return (
    <>
      {/* ── Header status + button ── */}
      <div className="flex items-center gap-2 ml-auto">
        {config?.groups?.length ? (
          apiError ? (
            <span className="flex items-center gap-1 text-xs text-destructive cursor-help max-w-[200px]" title={apiError}>
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">API error – showing mock</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-green-500">
              <CheckCircle className="w-3.5 h-3.5" />
              {config.groups.filter((g) => g.enabled).length} group{config.groups.filter((g) => g.enabled).length !== 1 ? "s" : ""} live
            </span>
          )
        ) : config?.url ? (
          apiError ? (
            <span className="flex items-center gap-1 text-xs text-destructive cursor-help max-w-[200px]" title={apiError}>
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">API error – showing mock</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-green-500">
              <CheckCircle className="w-3.5 h-3.5" />
              Live API
            </span>
          )
        ) : (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <WifiOff className="w-3.5 h-3.5" />
            Mock data
          </span>
        )}

        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-border rounded-md bg-card hover:bg-muted transition-colors"
        >
          <Settings className="w-3.5 h-3.5" />
          API Settings
        </button>
      </div>

      {/* ── Modal ── */}
      {open && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">

            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
              <div className="flex items-center gap-2">
                <Wifi className="w-5 h-5 text-primary" />
                <h2 className="font-semibold text-foreground">API Groups</h2>
                <span className="text-xs text-muted-foreground ml-1">
                  {enabledCount} active
                </span>
              </div>
              <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable group list */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
              {groups.map((g, idx) => (
                <div
                  key={g.id}
                  className={`rounded-lg border transition-colors ${
                    g.enabled ? "border-border bg-background" : "border-border/50 bg-muted/30 opacity-60"
                  }`}
                >
                  {/* Group header row */}
                  <div className="flex items-center gap-2 px-3 pt-3 pb-2">
                    <GripVertical className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0" />

                    <input
                      value={g.name}
                      onChange={(e) => updateGroup(g.id, { name: e.target.value })}
                      placeholder={`Group ${idx + 1}`}
                      className="flex-1 text-sm font-semibold bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none"
                    />

                    {/* Enable toggle */}
                    <button
                      onClick={() => toggleGroup(g.id)}
                      className={`transition-colors ${g.enabled ? "text-primary" : "text-muted-foreground"}`}
                      title={g.enabled ? "Disable group" : "Enable group"}
                    >
                      {g.enabled
                        ? <ToggleRight className="w-5 h-5" />
                        : <ToggleLeft className="w-5 h-5" />}
                    </button>

                    {/* Delete */}
                    <button
                      onClick={() => removeGroup(g.id)}
                      className="text-muted-foreground hover:text-destructive transition-colors"
                      title="Remove group"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* URL + token fields */}
                  <div className="px-3 pb-3 space-y-2">
                    <input
                      type="url"
                      value={g.url}
                      onChange={(e) => updateGroup(g.id, { url: e.target.value })}
                      placeholder="https://your-api.example.com/locations"
                      className="w-full text-xs px-3 py-2 rounded-md border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                    />
                    <div className="relative">
                      <input
                        type={showTokens[g.id] ? "text" : "password"}
                        value={g.token ?? ""}
                        onChange={(e) => updateGroup(g.id, { token: e.target.value })}
                        placeholder="Bearer token (optional)"
                        className="w-full text-xs px-3 py-2 pr-8 rounded-md border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                      />
                      <button
                        onClick={() => toggleToken(g.id)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showTokens[g.id] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Add group button */}
              <button
                onClick={addGroup}
                className="w-full flex items-center justify-center gap-2 py-2.5 border border-dashed border-border rounded-lg text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add API Group
              </button>

              {/* Format hint */}
              <div className="bg-muted/50 rounded-lg p-3 text-xs text-muted-foreground">
                <p className="font-medium text-foreground mb-1">Expected JSON format:</p>
                <pre className="font-mono text-[11px] leading-relaxed overflow-auto">{`{
  "locations": [
    {
      "device_id": "...",
      "device_name": "Motive.li-001",
      "geometry": { "coordinates": [lng, lat] },
      "online": true,
      "last_heard": "2025-01-01T00:00:00Z"
    }
  ]
}`}</pre>
              </div>

              {apiError && (
                <div className="flex items-start gap-2 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-3 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span className="break-all">{apiError}</span>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex gap-2 px-6 py-4 border-t border-border shrink-0">
              <button
                onClick={handleClear}
                className="text-xs px-3 py-2 rounded-md border border-border text-muted-foreground hover:bg-muted transition-colors"
              >
                Use Mock Data
              </button>
              <button
                onClick={handleSave}
                className="flex-1 text-xs px-3 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity"
              >
                Save & Connect
              </button>
            </div>
          </div>
        </div>
      , document.body)}
    </>
  );
}
