import assert from 'node:assert/strict'
import test from 'node:test'
import {
  createCallEvidence,
  createSmsEvidence,
  isEvidenceMatrixData,
  sourceLineForQuote,
} from './evidence-matrix.ts'

test('finds a line only for a unique exact quote match', () => {
  assert.equal(sourceLineForQuote('header\nunique quote\nfooter', 'unique quote'), 2)
  assert.equal(sourceLineForQuote('first\nrepeat\nrepeat', 'repeat'), null)
  assert.equal(sourceLineForQuote('text', 'missing'), null)
  assert.equal(sourceLineForQuote('aaa', 'aa'), null)
})

test('SMS evidence keeps extracted details and qualifies uncertain provenance', () => {
  const [located, unlocated] = createSmsEvidence([
    {
      date: '2026-03-01',
      time: '9:15 AM',
      actor: 'Alex',
      event_type: 'CALL_INITIATED',
      fact: 'Alex asked to call',
      quote: 'Can we talk?',
      legal_significance: 'Extractor note',
    },
    {
      date: '',
      time: '',
      actor: '',
      event_type: '',
      fact: '',
      quote: 'not present',
      legal_significance: '',
    },
  ], 'SMS export\nCan we talk?')

  assert.equal(located.date, '2026-03-01')
  assert.equal(located.time, '9:15 AM')
  assert.equal(located.quote, 'Can we talk?')
  assert.equal(located.sourceLocation, 'Line 2 (exact quote match)')
  assert.match(unlocated.sourceLocation, /No exact source line match/)
  assert.equal(unlocated.date, '')
})

test('call provenance does not claim an original source row', () => {
  const [call] = createCallEvidence([{
    date: '2026-03-02',
    time: '',
    caller: 'Alex',
    recipient: 'Sam',
    call_type: 'MISSED',
    duration: '0',
    answered: 'NO',
    legal_significance: '',
  }], 'calls.csv')

  assert.equal(call.sourceName, 'calls.csv')
  assert.match(call.sourceLocation, /original source row was not returned/)
  assert.equal(call.time, '')
})

test('validates matrix shape and rejects links to missing evidence', () => {
  const request = {
    id: 'request-1',
    kind: 'RFA',
    number: '1',
    text: 'Request wording',
    evidence: [{ evidenceId: 'item-1', reviewed: false, note: '' }],
  }
  const evidence = [{
    id: 'item-1',
    sourceName: 'sms',
    sourceLocation: 'Line 1',
    date: '',
    time: '',
    description: '',
    fact: '',
    quote: '',
    interpretation: '',
  }]

  assert.equal(isEvidenceMatrixData({ version: 1, evidence, requests: [request] }), true)
  assert.equal(isEvidenceMatrixData({ version: 1, evidence: [], requests: [request] }), false)
  assert.equal(isEvidenceMatrixData({ version: 2, evidence, requests: [request] }), false)
})
