import { NextResponse } from 'next/server'

const BACKEND = process.env.PYTHON_BACKEND_URL ?? 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/health`, { cache: 'no-store' })
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ status: 'offline' }, { status: 503 })
  }
}
