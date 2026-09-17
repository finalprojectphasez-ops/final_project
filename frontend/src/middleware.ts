import { NextResponse, type NextRequest } from 'next/server'

// Supabase middleware placeholder - auth will be wired up after npm install
export async function middleware(_request: NextRequest) {
    return NextResponse.next()
}

export const config = {
    matcher: [
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
}
