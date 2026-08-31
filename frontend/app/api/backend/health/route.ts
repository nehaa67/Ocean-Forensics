const BACKEND_URL = process.env.BACKEND_API_URL ?? 'http://localhost:8000';
export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/health`, {
      cache: 'no-store',
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: { 'content-type': 'application/json' },
    });
  } catch {
    return Response.json({ status: 'offline' }, { status: 503 });
  }
}
