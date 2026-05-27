'use client'

import { useState, useRef, useEffect } from 'react'

const MODELS = [
  { label: 'Gemini 2.0 Flash', value: 'gemini-2.0-flash' },
  { label: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' },
  { label: 'Ollama: Hermes3', value: 'ollama/hermes3:latest' },
  { label: 'Ollama: Llama 3.2', value: 'ollama/llama3.2:latest' },
  { label: 'GPT-4o', value: 'gpt-4o' },
]

type Event = {
  date: string
  time: string
  actor: string
  event_type: string
  fact: string
  quote: string
  legal_significance: string
}

type CallEvent = {
  date: string
  time: string
  caller: string
  recipient: string
  call_type: string
  duration: string
  answered: string
  legal_significance: string
}

type Tab = 'sms' | 'calls'

export default function Home() {
  const [tab, setTab] = useState<Tab>('sms')
  const [model, setModel] = useState(MODELS[0].value)
  const [smsText, setSmsText] = useState('')
  const [callFile, setCallFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [callEvents, setCallEvents] = useState<CallEvent[]>([])
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(d => setBackendOnline(d.status === 'ok'))
      .catch(() => setBackendOnline(false))
  }, [])

  async function runSMSExtraction() {
    if (!smsText.trim()) return
    setLoading(true)
    setError(null)
    setEvents([])
    try {
      const res = await fetch('/api/extract-sms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: smsText, model }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Extraction failed')
      setEvents(data.events ?? [])
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  async function runCallExtraction() {
    if (!callFile) return
    setLoading(true)
    setError(null)
    setCallEvents([])
    try {
      const form = new FormData()
      form.append('file', callFile)
      form.append('model', model)
      const res = await fetch('/api/extract-calls', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Extraction failed')
      setCallEvents(data.events ?? [])
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  function downloadCSV(rows: object[], filename: string) {
    if (!rows.length) return
    const headers = Object.keys(rows[0])
    const lines = [
      headers.join(','),
      ...rows.map(r =>
        headers.map(h => {
          const v = String((r as Record<string, unknown>)[h] ?? '')
          return v.includes(',') || v.includes('"') ? `"${v.replace(/"/g, '""')}"` : v
        }).join(',')
      ),
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const statusDot = backendOnline === null
    ? 'bg-neutral-500'
    : backendOnline ? 'bg-green-500' : 'bg-red-500'
  const statusLabel = backendOnline === null ? 'checking…' : backendOnline ? 'backend online' : 'backend offline'

  return (
    <main className="min-h-screen bg-neutral-900 text-neutral-100 p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">LogScraper</h1>
        <span className="flex items-center gap-2 text-sm text-neutral-400">
          <span className={`w-2 h-2 rounded-full ${statusDot}`} />
          {statusLabel}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-neutral-700">
        {(['sms', 'calls'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
              tab === t ? 'bg-neutral-700 text-white' : 'text-neutral-400 hover:text-white'
            }`}
          >
            {t === 'sms' ? 'SMS Timeline' : 'Call Log'}
          </button>
        ))}
      </div>

      {/* Model selector */}
      <div className="mb-6 flex items-center gap-3">
        <label className="text-sm text-neutral-400">Model</label>
        <select
          value={model}
          onChange={e => setModel(e.target.value)}
          className="bg-neutral-800 border border-neutral-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral-400"
        >
          {MODELS.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      {/* SMS tab */}
      {tab === 'sms' && (
        <div className="space-y-4">
          <textarea
            value={smsText}
            onChange={e => setSmsText(e.target.value)}
            placeholder="Paste SMS export text here…"
            rows={10}
            className="w-full bg-neutral-800 border border-neutral-600 rounded p-3 text-sm font-mono focus:outline-none focus:border-neutral-400 resize-y"
          />
          <div className="flex gap-3 items-center">
            <button
              onClick={runSMSExtraction}
              disabled={loading || !smsText.trim() || !backendOnline}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed rounded text-sm font-medium transition-colors"
            >
              {loading ? 'Extracting…' : 'Extract Timeline'}
            </button>
            {events.length > 0 && (
              <button
                onClick={() => downloadCSV(events, 'timeline_events.csv')}
                className="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 rounded text-sm transition-colors"
              >
                Export CSV
              </button>
            )}
            {events.length > 0 && (
              <span className="text-sm text-neutral-400">{events.length} events</span>
            )}
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          {events.length > 0 && (
            <div className="overflow-x-auto rounded border border-neutral-700">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-neutral-800 text-neutral-300 text-left">
                    {['Date', 'Time', 'Actor', 'Type', 'Fact', 'Quote', 'Legal Significance'].map(h => (
                      <th key={h} className="px-3 py-2 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {events.map((e, i) => (
                    <tr key={i} className={i % 2 === 0 ? 'bg-neutral-800/40' : ''}>
                      <td className="px-3 py-2 whitespace-nowrap">{e.date}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{e.time}</td>
                      <td className="px-3 py-2 whitespace-nowrap font-medium">{e.actor}</td>
                      <td className="px-3 py-2">
                        <span className="px-2 py-0.5 rounded text-xs bg-neutral-700">{e.event_type}</span>
                      </td>
                      <td className="px-3 py-2 max-w-xs truncate" title={e.fact}>{e.fact}</td>
                      <td className="px-3 py-2 max-w-xs truncate italic text-neutral-400" title={e.quote}>{e.quote}</td>
                      <td className="px-3 py-2 max-w-xs truncate text-yellow-300/80" title={e.legal_significance}>{e.legal_significance}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Call log tab */}
      {tab === 'calls' && (
        <div className="space-y-4">
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-neutral-600 hover:border-neutral-400 rounded-lg p-10 text-center cursor-pointer transition-colors"
          >
            <p className="text-neutral-400 text-sm">
              {callFile ? callFile.name : 'Click to upload call log (.csv, .json, .xlsx, .pdf, .txt)'}
            </p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json,.xlsx,.xls,.pdf,.html,.txt"
            className="hidden"
            onChange={e => setCallFile(e.target.files?.[0] ?? null)}
          />
          <div className="flex gap-3 items-center">
            <button
              onClick={runCallExtraction}
              disabled={loading || !callFile || !backendOnline}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed rounded text-sm font-medium transition-colors"
            >
              {loading ? 'Extracting…' : 'Extract Call Events'}
            </button>
            {callEvents.length > 0 && (
              <button
                onClick={() => downloadCSV(callEvents, 'call_events.csv')}
                className="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 rounded text-sm transition-colors"
              >
                Export CSV
              </button>
            )}
            {callEvents.length > 0 && (
              <span className="text-sm text-neutral-400">{callEvents.length} events</span>
            )}
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          {callEvents.length > 0 && (
            <div className="overflow-x-auto rounded border border-neutral-700">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-neutral-800 text-neutral-300 text-left">
                    {['Date', 'Time', 'Caller', 'Recipient', 'Type', 'Duration', 'Answered', 'Legal Significance'].map(h => (
                      <th key={h} className="px-3 py-2 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {callEvents.map((e, i) => (
                    <tr key={i} className={i % 2 === 0 ? 'bg-neutral-800/40' : ''}>
                      <td className="px-3 py-2 whitespace-nowrap">{e.date}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{e.time}</td>
                      <td className="px-3 py-2">{e.caller}</td>
                      <td className="px-3 py-2">{e.recipient}</td>
                      <td className="px-3 py-2">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          e.call_type === 'MISSED' ? 'bg-red-900/60 text-red-300' :
                          e.call_type === 'INCOMING' ? 'bg-green-900/60 text-green-300' :
                          'bg-blue-900/60 text-blue-300'
                        }`}>{e.call_type}</span>
                      </td>
                      <td className="px-3 py-2">{e.duration}</td>
                      <td className="px-3 py-2">{e.answered}</td>
                      <td className="px-3 py-2 max-w-xs truncate text-yellow-300/80" title={e.legal_significance}>{e.legal_significance}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </main>
  )
}
