import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const { message, sessionId } = body;

        const pythonApiUrl = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000/api/chat';
        const apiKey = process.env.APP_API_KEY || 'smartwaiter-dev-key';

        console.log(`Proxying to Backend: ${pythonApiUrl}`);

        const response = await fetch(pythonApiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify({ message, session_id: sessionId }),
        });

        if (!response.ok) {
            console.error(`Backend Error: ${response.status} ${response.statusText}`);
            return NextResponse.json(
                { error: `Backend Error: ${response.statusText}` },
                { status: response.status }
            );
        }

        if (!response.body) {
            return NextResponse.json({ error: "No response body" }, { status: 500 });
        }

        // Proxy the stream
        return new NextResponse(response.body, {
            headers: {
                'Content-Type': 'text/plain',
                'Transfer-Encoding': 'chunked'
            }
        });

    } catch (error: any) {
        console.error("Proxy Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
