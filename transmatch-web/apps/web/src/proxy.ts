import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "tm_session";

// Optimistic check only: without a session cookie there is nothing to show, so
// go straight to the login page. The API validates the session on every call.
export function proxy(request: NextRequest) {
  const signedIn = request.cookies.has(SESSION_COOKIE);
  const onLogin = request.nextUrl.pathname === "/login";
  if (!signedIn && !onLogin) return NextResponse.redirect(new URL("/login", request.url));
  if (signedIn && onLogin) return NextResponse.redirect(new URL("/", request.url));
  return NextResponse.next();
}

export const config = {
  // Pages only: API calls (file uploads included) and static assets pass straight through
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\.(?:png|svg|ico)$).*)"],
};
