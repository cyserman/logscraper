export type SmsEvent = {
  date: string
  time: string
  actor: string
  event_type: string
  fact: string
  quote: string
  legal_significance: string
}

export type CallEvent = {
  date: string
  time: string
  caller: string
  recipient: string
  call_type: string
  duration: string
  answered: string
  legal_significance: string
}

export type EvidenceItem = {
  id: string
  sourceName: string
  sourceLocation: string
  date: string
  time: string
  description: string
  fact: string
  quote: string
  interpretation: string
}

export type EvidenceLink = {
  evidenceId: string
  reviewed: boolean
  note: string
}

export type DiscoveryRequest = {
  id: string
  kind: 'RFA' | 'RFP'
  number: string
  text: string
  evidence: EvidenceLink[]
}

export type EvidenceMatrixData = {
  version: 1
  evidence: EvidenceItem[]
  requests: DiscoveryRequest[]
}

export function sourceLineForQuote(sourceText: string, quote: string): number | null {
  if (!quote) return null
  const matchAt = sourceText.indexOf(quote)
  if (matchAt < 0 || sourceText.indexOf(quote, matchAt + 1) !== -1) return null
  return sourceText.slice(0, matchAt).split(/\r\n|\r|\n/).length
}

function fingerprint(text: string): string {
  let hash = 2166136261
  for (let index = 0; index < text.length; index += 1) {
    hash = Math.imul(hash ^ text.charCodeAt(index), 16777619)
  }
  return (hash >>> 0).toString(16).padStart(8, '0')
}

export function createSmsEvidence(events: SmsEvent[], sourceText: string): EvidenceItem[] {
  const sourceId = fingerprint(sourceText)
  return events.map((event, index) => {
    const line = sourceLineForQuote(sourceText, event.quote)
    return {
      id: `sms-${sourceId}-${index + 1}-${line ?? 'unlocated'}`,
      sourceName: `Pasted SMS export (${sourceId})`,
      sourceLocation: line === null
        ? 'No exact source line match; check the pasted original'
        : `Line ${line} (exact quote match)`,
      date: event.date,
      time: event.time,
      description: [event.actor, event.event_type].filter(Boolean).join(' · '),
      fact: event.fact,
      quote: event.quote,
      interpretation: event.legal_significance,
    }
  })
}

export function createCallEvidence(events: CallEvent[], sourceName: string, sourceId = sourceName): EvidenceItem[] {
  return events.map((event, index) => ({
    id: `call-${encodeURIComponent(sourceId)}-${index + 1}`,
    sourceName,
    sourceLocation: `Extracted call event ${index + 1}; original source row was not returned`,
    date: event.date,
    time: event.time,
    description: [event.call_type, `${event.caller} → ${event.recipient}`].filter(Boolean).join(' · '),
    fact: [
      event.duration && `Duration: ${event.duration}`,
      event.answered && `Answered: ${event.answered}`,
    ].filter(Boolean).join(' · '),
    quote: '',
    interpretation: event.legal_significance,
  }))
}

export function isEvidenceMatrixData(value: unknown): value is EvidenceMatrixData {
  if (!value || typeof value !== 'object') return false
  const data = value as Record<string, unknown>
  if (data.version !== 1 ||
    !Array.isArray(data.evidence) ||
    !data.evidence.every(isEvidenceItem) ||
    !Array.isArray(data.requests) ||
    !data.requests.every(isDiscoveryRequest)) return false
  const evidenceIds = new Set((data.evidence as EvidenceItem[]).map(item => item.id))
  return (data.requests as DiscoveryRequest[]).every(request =>
      request.evidence.every(link => evidenceIds.has(link.evidenceId))
    )
}

function isEvidenceItem(value: unknown): value is EvidenceItem {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  return ['id', 'sourceName', 'sourceLocation', 'date', 'time', 'description', 'fact', 'quote', 'interpretation']
    .every(key => typeof item[key] === 'string')
}

function isDiscoveryRequest(value: unknown): value is DiscoveryRequest {
  if (!value || typeof value !== 'object') return false
  const request = value as Record<string, unknown>
  return typeof request.id === 'string' &&
    (request.kind === 'RFA' || request.kind === 'RFP') &&
    typeof request.number === 'string' &&
    typeof request.text === 'string' &&
    Array.isArray(request.evidence) &&
    request.evidence.every(link =>
      !!link &&
      typeof link === 'object' &&
      typeof (link as Record<string, unknown>).evidenceId === 'string' &&
      typeof (link as Record<string, unknown>).reviewed === 'boolean' &&
      typeof (link as Record<string, unknown>).note === 'string'
    )
}
