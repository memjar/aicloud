import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Protected routes
  const protectedRoutes = ['/dashboard', '/models', '/playground'];

  // Check if route needs auth
  const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));

  if (isProtectedRoute) {
    // In a real app, check cookies/session
    // For now, client-side auth is in useAuth hook
    // This is a placeholder for server-side auth when backend is ready
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/models/:path*', '/playground/:path*'],
};
