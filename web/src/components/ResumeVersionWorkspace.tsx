import React, { useEffect, useMemo, useState } from 'react';
import { Download, History, Save, Trash2 } from 'lucide-react';
import { StructuredResume } from '../types/builder';
import {
  deleteResumeVersion,
  loadResumeVersions,
  ResumeVersion,
  saveResumeVersion,
  updateResumeVersion,
} from '../services/resumeVersions';
import {
  deleteCloudResumeDocument, getResumeSessionToken, loadCloudResumeDocuments,
  saveCloudResumeDocument,
} from '../services/resumeCloud';

interface ResumeVersionWorkspaceProps {
  resume: StructuredResume;
  targetRole: string;
  targetCompany: string;
  onRestore: (resume: StructuredResume) => void;
  onExport: (resume: StructuredResume, format: 'pdf' | 'docx', targetCompany: string) => void;
}

const cloneResume = (resume: StructuredResume): StructuredResume =>
  JSON.parse(JSON.stringify(resume)) as StructuredResume;

const VERSION_SECTIONS: Array<{ key: keyof StructuredResume; label: string }> = [
  { key: 'summary', label: 'Professional summary' },
  { key: 'skills', label: 'Skills' },
  { key: 'experience', label: 'Experience' },
  { key: 'projects', label: 'Projects' },
  { key: 'education', label: 'Education' },
  { key: 'certifications', label: 'Certifications' },
  { key: 'contact_info', label: 'Contact details' },
];

const serializeSection = (value: StructuredResume[keyof StructuredResume]): string =>
  typeof value === 'string' ? value : JSON.stringify(value, null, 2);

export const ResumeVersionWorkspace: React.FC<ResumeVersionWorkspaceProps> = ({
  resume,
  targetRole,
  targetCompany,
  onRestore,
  onExport,
}) => {
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [versionName, setVersionName] = useState('');
  const [editingVersionId, setEditingVersionId] = useState('');
  const [olderId, setOlderId] = useState('');
  const [newerId, setNewerId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const refreshVersions = async () => {
    try {
      const localVersions = loadResumeVersions();
      setVersions(localVersions);
      setError(null);
      const token = getResumeSessionToken();
      if (token) {
        const documents = await loadCloudResumeDocuments<ResumeVersion>(token, 'version');
        const cloudVersions = documents
          .map((item) => item.document)
          .filter((item): item is ResumeVersion =>
            Boolean(item && typeof item.id === 'string' && typeof item.name === 'string' && item.resume)
          );
        const mergedById = new Map(localVersions.map((version) => [version.id, version]));
        cloudVersions.forEach((remote) => {
          const local = mergedById.get(remote.id);
          if (!local || remote.savedAt >= local.savedAt) mergedById.set(remote.id, remote);
        });
        const merged = [...mergedById.values()].sort((a, b) => b.savedAt.localeCompare(a.savedAt));
        cloudVersions.forEach((remote) => {
          const local = localVersions.find((version) => version.id === remote.id);
          if (!local) saveResumeVersion(remote);
          else if (remote.savedAt >= local.savedAt) updateResumeVersion(remote);
        });
        setVersions(merged);
      }
    } catch (loadError: unknown) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load saved versions.');
    } finally {
      setIsLoaded(true);
    }
  };

  useEffect(() => {
    void refreshVersions();
  }, []);

  const olderVersion = versions.find((version) => version.id === olderId);
  const newerVersion = versions.find((version) => version.id === newerId);
  const differences = useMemo(() => {
    if (!olderVersion || !newerVersion || olderVersion.id === newerVersion.id) return [];
    return VERSION_SECTIONS.flatMap(({ key, label }) => {
      const before = serializeSection(olderVersion.resume[key]);
      const after = serializeSection(newerVersion.resume[key]);
      return before === after ? [] : [{ label, before, after }];
    });
  }, [olderVersion, newerVersion]);

  const handleSave = async () => {
    const cleanName = versionName.trim();
    if (!cleanName) {
      setError('Enter a name for this resume version.');
      return;
    }
    const existing = versions.find((item) => item.id === editingVersionId);
    const version: ResumeVersion = existing
      ? { ...existing, name: cleanName }
      : {
          id: typeof crypto !== 'undefined' && 'randomUUID' in crypto
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          name: cleanName,
          savedAt: new Date().toISOString(),
          targetRole,
          targetCompany,
          resume: cloneResume(resume),
        };
    try {
      const updated = existing ? updateResumeVersion(version) : saveResumeVersion(version);
      setVersions(updated);
      const token = getResumeSessionToken();
      if (token) {
        await saveCloudResumeDocument(token, {
          id: version.id, document_type: 'version', name: version.name, document: version,
        });
      }
      setNewerId(version.id);
      if (updated.length > 1 && (!olderId || olderId === version.id)) {
        setOlderId(updated[1].id);
      }
      setVersionName('');
      setEditingVersionId('');
      setError(null);
      setNotice(`${existing ? 'Renamed' : 'Saved'} “${cleanName}”${token ? ' in this browser and to your account.' : ' in this browser.'}`);
    } catch (saveError: unknown) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to save this version.');
      setNotice(null);
    }
  };

  const handleDelete = async (version: ResumeVersion) => {
    if (!window.confirm(`Delete the saved version “${version.name}”${getResumeSessionToken() ? ' from this browser and your account' : ' from this browser'}?`)) return;
    try {
      const updated = deleteResumeVersion(version.id);
      setVersions(updated);
      const token = getResumeSessionToken();
      if (token) await deleteCloudResumeDocument(token, version.id);
      if (olderId === version.id) setOlderId('');
      if (newerId === version.id) setNewerId('');
      if (editingVersionId === version.id) {
        setEditingVersionId('');
        setVersionName('');
      }
      setError(null);
      setNotice(`Deleted “${version.name}”${token ? ' from this browser and your account.' : ' from this browser.'}`);
    } catch (deleteError: unknown) {
      setError(deleteError instanceof Error ? deleteError.message : 'Unable to delete this version.');
    }
  };

  const handleSync = async (version: ResumeVersion) => {
    const token = getResumeSessionToken();
    if (!token) return;
    try {
      await saveCloudResumeDocument(token, {
        id: version.id, document_type: 'version', name: version.name, document: version,
      });
      setNotice(`Synced “${version.name}” with your account.`);
      setError(null);
    } catch (syncError: unknown) {
      setError(syncError instanceof Error ? syncError.message : 'Unable to sync this version.');
    }
  };

  const handleDuplicate = async (version: ResumeVersion) => {
    const duplicate: ResumeVersion = {
      ...version,
      id: typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: `${version.name.slice(0, 75)} copy`,
      savedAt: new Date().toISOString(),
      resume: cloneResume(version.resume),
    };
    try {
      const updated = saveResumeVersion(duplicate);
      const token = getResumeSessionToken();
      if (token) {
        await saveCloudResumeDocument(token, {
          id: duplicate.id, document_type: 'version', name: duplicate.name, document: duplicate,
        });
      }
      setVersions(updated);
      setNotice(`Duplicated “${version.name}”.`);
      setError(null);
    } catch (duplicateError: unknown) {
      setError(duplicateError instanceof Error ? duplicateError.message : 'Unable to duplicate this version.');
    }
  };

  return (
    <section className="version-workspace" aria-labelledby="resume-history-title">
      <div className="version-workspace-heading">
        <div>
          <span className="badge badge-primary"><History size={13} /> {getResumeSessionToken() ? 'Account storage enabled' : 'Browser-only history'}</span>
          <h3 id="resume-history-title">Resume versions</h3>
          <p>Save named snapshots, restore older drafts, compare changes, or export a saved version.</p>
        </div>
      </div>

      <div className="version-save-row">
        <label htmlFor="resume-version-name">Version name</label>
        <input
          id="resume-version-name"
          value={versionName}
          maxLength={80}
          placeholder="e.g. Backend Engineer — November"
          onChange={(event) => setVersionName(event.target.value)}
        />
        <button type="button" className="btn btn-primary btn-small" onClick={handleSave} disabled={!isLoaded}>
          <Save size={15} /> {editingVersionId ? 'Save version name' : 'Save current version'}
        </button>
        {editingVersionId && <button type="button" className="btn btn-secondary btn-small" onClick={() => { setEditingVersionId(''); setVersionName(''); }}>Cancel</button>}
      </div>

      {error && <p className="version-message version-error" role="alert">{error}</p>}
      {notice && <p className="version-message" role="status">{notice}</p>}

      {versions.length === 0 ? (
        <p className="version-empty">No saved versions yet. Save this draft to start a local history.</p>
      ) : (
        <>
          <div className="version-history-list">
            {versions.map((version) => (
              <article className="version-history-item" key={version.id}>
                <div>
                  <strong>{version.name}</strong>
                  <span>{version.targetRole} · {version.targetCompany}</span>
                  <time dateTime={version.savedAt}>{new Date(version.savedAt).toLocaleString()}</time>
                </div>
                <div className="version-actions">
                  <button type="button" className="btn btn-secondary btn-small" disabled={!isLoaded} onClick={() => onRestore(cloneResume(version.resume))}>
                    Restore
                  </button>
                  <button type="button" className="btn btn-secondary btn-small" disabled={!isLoaded} onClick={() => handleDuplicate(version)} aria-label={`Duplicate ${version.name}`}>
                    Duplicate
                  </button>
                  <button type="button" className="btn btn-secondary btn-small" disabled={!isLoaded} onClick={() => { setEditingVersionId(version.id); setVersionName(version.name); }} aria-label={`Rename ${version.name}`}>
                    Rename
                  </button>
                  {getResumeSessionToken() && <button type="button" className="btn btn-secondary btn-small" disabled={!isLoaded} onClick={() => handleSync(version)}>Sync</button>}
                  <button type="button" className="btn btn-secondary btn-small" disabled={!isLoaded} onClick={() => onExport(cloneResume(version.resume), 'pdf', version.targetCompany)} aria-label={`Export ${version.name} as PDF`}>
                    <Download size={14} /> PDF
                  </button>
                  <button type="button" className="btn btn-secondary btn-small" disabled={!isLoaded} onClick={() => onExport(cloneResume(version.resume), 'docx', version.targetCompany)} aria-label={`Export ${version.name} as DOCX`}>
                    <Download size={14} /> DOCX
                  </button>
                  <button type="button" className="btn btn-secondary btn-small" disabled={!isLoaded} onClick={() => handleDelete(version)} aria-label={`Delete ${version.name}`}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </article>
            ))}
          </div>

          <div className="version-compare">
            <h4>Compare versions</h4>
            <div className="version-compare-selects">
              <label>
                Older version
                <select value={olderId} onChange={(event) => setOlderId(event.target.value)}>
                  <option value="">Choose a version</option>
                  {versions.map((version) => <option value={version.id} key={version.id}>{version.name}</option>)}
                </select>
              </label>
              <label>
                Newer version
                <select value={newerId} onChange={(event) => setNewerId(event.target.value)}>
                  <option value="">Choose a version</option>
                  {versions.map((version) => <option value={version.id} key={version.id}>{version.name}</option>)}
                </select>
              </label>
            </div>
            {olderId && newerId && olderId === newerId && (
              <p className="version-empty">Choose two different versions to compare.</p>
            )}
            {olderVersion && newerVersion && olderVersion.id !== newerVersion.id && (
              differences.length ? (
                <div className="version-diff-list">
                  {differences.map((difference) => (
                    <details key={difference.label} className="version-diff">
                      <summary>{difference.label} changed</summary>
                      <div className="version-diff-columns">
                        <div><strong>{olderVersion.name}</strong><pre>{difference.before || '(empty)'}</pre></div>
                        <div><strong>{newerVersion.name}</strong><pre>{difference.after || '(empty)'}</pre></div>
                      </div>
                    </details>
                  ))}
                </div>
              ) : <p className="version-empty">These versions have no content differences.</p>
            )}
          </div>
        </>
      )}
      <p className="version-privacy-note">
        {getResumeSessionToken()
          ? 'Saved versions are encrypted in your account when explicitly synced or saved while signed in; browser copies are retained.'
          : 'Saved resume text stays in this browser’s local storage. Sign in through Career Platform to enable encrypted account sync.'}
      </p>
    </section>
  );
};
