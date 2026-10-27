'use client'

import { useMemo, useRef, useState } from 'react'
import {
  type DiscoveryRequest,
  type EvidenceItem,
  type EvidenceLink,
  type EvidenceMatrixData,
  isEvidenceMatrixData,
} from '@/lib/evidence-matrix'

const STORAGE_KEY = 'logscraper-evidence-matrix-v1'

export default function EvidenceMatrix({ extractedEvidence }: { extractedEvidence: EvidenceItem[] }) {
  const [loadedEvidence, setLoadedEvidence] = useState<EvidenceItem[]>([])
  const [requests, setRequests] = useState<DiscoveryRequest[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [status, setStatus] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const selectedRequest = requests.find(request => request.id === selectedId) ?? requests[0]
  const evidence = useMemo(() => {
    const byId = new Map(loadedEvidence.map(item => [item.id, item]))
    for (const item of extractedEvidence) byId.set(item.id, item)
    return [...byId.values()]
  }, [loadedEvidence, extractedEvidence])
  const evidenceById = useMemo(() => new Map(evidence.map(item => [item.id, item])), [evidence])

  function updateRequest(id: string, update: Partial<DiscoveryRequest>) {
    setRequests(current => current.map(request => request.id === id ? { ...request, ...update } : request))
  }

  function addRequest() {
    const request: DiscoveryRequest = {
      id: crypto.randomUUID(),
      kind: 'RFA',
      number: String(requests.length + 1),
      text: '',
      evidence: [],
    }
    setRequests(current => [...current, request])
    setSelectedId(request.id)
    setStatus('')
  }

  function updateLink(evidenceId: string, update: Partial<EvidenceLink>) {
    if (!selectedRequest) return
    updateRequest(selectedRequest.id, {
      evidence: selectedRequest.evidence.map(link =>
        link.evidenceId === evidenceId ? { ...link, ...update } : link,
      ),
    })
  }

  function toggleEvidence(item: EvidenceItem, checked: boolean) {
    if (!selectedRequest) return
    const links = checked
      ? [...selectedRequest.evidence, { evidenceId: item.id, reviewed: false, note: '' }]
      : selectedRequest.evidence.filter(link => link.evidenceId !== item.id)
    updateRequest(selectedRequest.id, { evidence: links })
  }

  function saveOnDevice() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, evidence, requests }))
      setStatus('Saved in this browser on this device.')
    } catch (error) {
      setStatus(`Could not save this matrix: ${String(error)}`)
    }
  }

  function loadFromDevice() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (!saved) {
        setStatus('No saved matrix found in this browser.')
        return
      }
      const parsed: unknown = JSON.parse(saved)
      if (!isEvidenceMatrixData(parsed)) {
        setStatus('The saved file is not a valid LogScraper matrix.')
        return
      }
      setLoadedEvidence(parsed.evidence)
      setRequests(parsed.requests)
      setSelectedId(parsed.requests[0]?.id ?? null)
      setStatus('Loaded saved matrix from this browser.')
    } catch (error) {
      setStatus(`Could not load the saved matrix: ${String(error)}`)
    }
  }

  function exportMatrix() {
    const blob = new Blob([JSON.stringify({ version: 1, evidence, requests }, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'logscraper-evidence-matrix.json'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  function exportCSV() {
    const headers = [
      'Request type', 'Request number', 'Request wording', 'Linked record count',
      'Date', 'Time', 'Description', 'Extracted fact', 'Verbatim quote',
      'Extractor interpretation (not source fact)', 'Source', 'Source location / provenance',
      'Reviewed against original', 'Review note',
    ]
    const rows = requests.flatMap(request => {
      const links = request.evidence.length ? request.evidence : [null]
      return links.map(link => {
        const item = link ? evidenceById.get(link.evidenceId) : undefined
        return [
          request.kind, request.number, request.text, String(request.evidence.length),
          item?.date ?? '', item?.time ?? '', item?.description ?? '', item?.fact ?? '',
          item?.quote ?? '', item?.interpretation ?? '', item?.sourceName ?? '', item?.sourceLocation ?? '',
          link?.reviewed ? 'Yes' : 'No', link?.note ?? '',
        ]
      })
    })
    const escape = (value: string) => `"${value.replace(/"/g, '""')}"`
    const csv = [headers, ...rows].map(row => row.map(escape).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'logscraper-evidence-matrix.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  async function importMatrix(file: File) {
    try {
      const parsed: unknown = JSON.parse(await file.text())
      if (!isEvidenceMatrixData(parsed)) {
        setStatus('Import failed: this file is not a valid LogScraper matrix.')
        return
      }
      setLoadedEvidence(parsed.evidence)
      setRequests(parsed.requests)
      setSelectedId(parsed.requests[0]?.id ?? null)
      setStatus('Matrix imported. Review entries against the original evidence.')
    } catch (error) {
      setStatus(`Import failed: ${String(error)}`)
    }
  }

  function clearSavedMatrix() {
    try {
      localStorage.removeItem(STORAGE_KEY)
      setStatus('Removed the saved matrix from this browser.')
    } catch (error) {
      setStatus(`Could not remove the saved matrix: ${String(error)}`)
    }
  }

  function deleteRequest(id: string) {
    const remaining = requests.filter(request => request.id !== id)
    setRequests(remaining)
    if (selectedId === id) setSelectedId(remaining[0]?.id ?? null)
  }

  return (
    <section className="space-y-6" aria-labelledby="matrix-heading">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="matrix-heading" className="text-2xl font-semibold">RFA / RFP evidence matrix</h2>
          <p className="mt-1 max-w-3xl text-sm text-neutral-400">
            Organize extracted records against your own request wording. This tool does not draft answers or determine legal significance.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={loadFromDevice} className="rounded bg-neutral-700 px-3 py-2 text-sm hover:bg-neutral-600">Load saved</button>
          <button onClick={saveOnDevice} className="rounded bg-neutral-700 px-3 py-2 text-sm hover:bg-neutral-600">Save on this device</button>
          <button onClick={exportCSV} className="rounded bg-neutral-700 px-3 py-2 text-sm hover:bg-neutral-600">Export CSV</button>
          <button onClick={exportMatrix} className="rounded bg-neutral-700 px-3 py-2 text-sm hover:bg-neutral-600">Export JSON</button>
          <button onClick={() => fileRef.current?.click()} className="rounded bg-neutral-700 px-3 py-2 text-sm hover:bg-neutral-600">Import JSON</button>
          <button onClick={clearSavedMatrix} className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-700">Remove saved copy</button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={event => {
              const file = event.target.files?.[0]
              if (file) void importMatrix(file)
              event.currentTarget.value = ''
            }}
          />
        </div>
      </div>

      <div className="rounded border border-amber-800/70 bg-amber-950/30 p-4 text-sm text-amber-100/90">
        Verify every item against the original source before use. Dates, times, counts, quotes, and locations are shown only when available;
        extractor-generated descriptions or interpretations are not source facts. Matrices are not saved unless you choose to save or export them.
      </div>
      {status && <p role="status" className="text-sm text-neutral-300">{status}</p>}

      <div className="grid gap-6 lg:grid-cols-[minmax(220px,0.8fr)_minmax(0,2fr)]">
        <aside className="space-y-3">
          <button onClick={addRequest} className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500">
            Add RFA / RFP
          </button>
          {requests.length === 0 && (
            <p className="rounded border border-neutral-700 p-4 text-sm text-neutral-400">
              Add a request, then link relevant extracted evidence.
            </p>
          )}
          {requests.map(request => (
            <button
              key={request.id}
              onClick={() => setSelectedId(request.id)}
              className={`w-full rounded border p-3 text-left ${
                request.id === selectedRequest?.id
                  ? 'border-blue-500 bg-blue-950/40'
                  : 'border-neutral-700 bg-neutral-800/50 hover:bg-neutral-800'
              }`}
            >
              <span className="text-xs font-semibold text-blue-300">{request.kind} {request.number || '—'}</span>
              <span className="mt-1 block truncate text-sm text-neutral-300">{request.text || 'Untitled request'}</span>
              <span className="mt-1 block text-xs text-neutral-500">
                {request.evidence.length} linked occurrence{request.evidence.length === 1 ? '' : 's'}
              </span>
            </button>
          ))}
        </aside>

        {selectedRequest && (
          <div className="min-w-0 space-y-5">
            <div className="grid gap-3 sm:grid-cols-[120px_120px_minmax(0,1fr)]">
              <label className="text-xs text-neutral-400">
                Request type
                <select
                  value={selectedRequest.kind}
                  onChange={event => updateRequest(selectedRequest.id, { kind: event.target.value as 'RFA' | 'RFP' })}
                  className="mt-1 w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-2 text-sm text-white"
                >
                  <option value="RFA">RFA</option>
                  <option value="RFP">RFP</option>
                </select>
              </label>
              <label className="text-xs text-neutral-400">
                Number
                <input
                  value={selectedRequest.number}
                  onChange={event => updateRequest(selectedRequest.id, { number: event.target.value })}
                  className="mt-1 w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-2 text-sm text-white"
                />
              </label>
              <label className="text-xs text-neutral-400">
                Request wording (your text)
                <textarea
                  value={selectedRequest.text}
                  onChange={event => updateRequest(selectedRequest.id, { text: event.target.value })}
                  rows={3}
                  placeholder="Paste or type the request wording"
                  className="mt-1 w-full rounded border border-neutral-600 bg-neutral-800 px-3 py-2 text-sm text-white"
                />
              </label>
            </div>

            <section className="space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-lg font-medium">Linked occurrences</h3>
                <span className="text-sm text-neutral-400">
                  Linked records: {selectedRequest.evidence.length} · Distinct dates: {
                    new Set(selectedRequest.evidence.map(link => evidenceById.get(link.evidenceId)?.date).filter(Boolean)).size
                  }
                </span>
              </div>
              {selectedRequest.evidence.length === 0 ? (
                <p className="rounded border border-neutral-700 p-4 text-sm text-neutral-400">No records linked. Select evidence below to build the matrix.</p>
              ) : (
                <div className="space-y-3">
                  {selectedRequest.evidence.map(link => {
                    const item = evidenceById.get(link.evidenceId)
                    if (!item) return null
                    return (
                      <article key={item.id} className="rounded border border-neutral-700 bg-neutral-800/50 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{item.date || 'Date not available'}{item.time ? ` · ${item.time}` : ''}</p>
                            <p className="mt-1 text-sm text-neutral-300">{item.description || 'Event details not available'}</p>
                          </div>
                          <label className="flex items-center gap-2 text-xs text-neutral-300">
                            <input
                              type="checkbox"
                              checked={link.reviewed}
                              onChange={event => updateLink(item.id, { reviewed: event.target.checked })}
                              className="accent-green-500"
                            />
                            Reviewed against original
                          </label>
                        </div>
                        {item.fact && <p className="mt-3 text-sm text-neutral-300">{item.fact}</p>}
                        <blockquote className="mt-3 whitespace-pre-wrap border-l-2 border-neutral-600 pl-3 text-sm italic text-neutral-300">
                          {item.quote ? `“${item.quote}”` : 'No verbatim quote supplied by extraction.'}
                        </blockquote>
                        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                          <div><dt className="text-neutral-500">Source</dt><dd className="break-words text-neutral-300">{item.sourceName}</dd></div>
                          <div><dt className="text-neutral-500">Location / provenance</dt><dd className="break-words text-neutral-300">{item.sourceLocation || 'Not supplied'}</dd></div>
                        </dl>
                        {item.interpretation && (
                          <p className="mt-3 text-xs text-yellow-200/80">
                            Extractor interpretation (verify; not a source fact): {item.interpretation}
                          </p>
                        )}
                        <label className="mt-3 block text-xs text-neutral-400">
                          Review note
                          <textarea
                            value={link.note}
                            onChange={event => updateLink(item.id, { note: event.target.value })}
                            rows={2}
                            placeholder="Optional note for your review"
                            className="mt-1 w-full rounded border border-neutral-600 bg-neutral-900 px-3 py-2 text-sm text-white"
                          />
                        </label>
                        <button
                          onClick={() => toggleEvidence(item, false)}
                          className="mt-3 text-xs text-red-300 underline hover:text-red-200"
                        >
                          Unlink record
                        </button>
                      </article>
                    )
                  })}
                </div>
              )}
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-medium">Available extracted evidence</h3>
              {evidence.length === 0 ? (
                <p className="rounded border border-neutral-700 p-4 text-sm text-neutral-400">
                  Extract SMS or call records first, then link them here.
                </p>
              ) : (
                <div className="max-h-[32rem] space-y-2 overflow-y-auto rounded border border-neutral-700 p-2">
                  {evidence.map(item => {
                    const linked = selectedRequest.evidence.some(link => link.evidenceId === item.id)
                    return (
                      <label key={item.id} className="flex cursor-pointer gap-3 rounded p-3 hover:bg-neutral-800">
                        <input
                          type="checkbox"
                          checked={linked}
                          onChange={event => toggleEvidence(item, event.target.checked)}
                          className="mt-1 accent-blue-500"
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-medium">
                            {item.date || 'Date not available'}{item.time ? ` · ${item.time}` : ''} — {item.description || 'Event'}
                          </span>
                          <span className="mt-1 block truncate text-xs text-neutral-400">
                            {item.quote || item.fact || 'No source quote supplied'}
                          </span>
                          <span className="mt-1 block text-xs text-neutral-500">{item.sourceName} · {item.sourceLocation}</span>
                        </span>
                      </label>
                    )
                  })}
                </div>
              )}
            </section>
            <button
              onClick={() => deleteRequest(selectedRequest.id)}
              className="rounded border border-red-900 px-3 py-2 text-sm text-red-300 hover:bg-red-950/40"
            >
              Delete this request from the matrix
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
