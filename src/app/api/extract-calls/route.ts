import { NextResponse } from 'next/server'

const BACKEND = process.env.PYTHON_BACKEND_URL ?? 'http://localhost:8000'

export async function POST(request: Request) {
  try {
    const formData = await request.formData()
    const res = await fetch(`${BACKEND}/api/extract-calls`, {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json()
      return NextResponse.json({ error: err.detail ?? 'Extraction failed' }, { status: res.status })
    }
    return NextResponse.json(await res.json())
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 })
  }
}
