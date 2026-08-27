const AUTH_KEY = "sf_auth";

export interface AuthUser {
  username: string;
}

export function getAuth(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setAuth(user: AuthUser): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem(AUTH_KEY);
}

async function sha256(text: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

const VALID_USER_HASH = process.env.NEXT_PUBLIC_AUTH_USER_HASH || "";
const VALID_PASS_HASH = process.env.NEXT_PUBLIC_AUTH_PASS_HASH || "";

export async function validateCredentials(
  username: string,
  password: string
): Promise<boolean> {
  const [uHash, pHash] = await Promise.all([sha256(username), sha256(password)]);
  return uHash === VALID_USER_HASH && pHash === VALID_PASS_HASH;
}