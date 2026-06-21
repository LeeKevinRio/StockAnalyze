'use client';

import { useState, useEffect, useCallback } from 'react';
import { authAPI } from '@/lib/api';

const TOKEN_KEY = 'auth_token';
const EMAIL_KEY = 'auth_email';
const EVENT = 'auth-change';

function emit() {
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(EVENT));
}

/** Browser-stored JWT auth state. */
export function useAuth() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => {
      setToken(localStorage.getItem(TOKEN_KEY));
      setEmail(localStorage.getItem(EMAIL_KEY));
    };
    sync();
    window.addEventListener('storage', sync);
    window.addEventListener(EVENT, sync);
    return () => {
      window.removeEventListener('storage', sync);
      window.removeEventListener(EVENT, sync);
    };
  }, []);

  const save = (t: string, e: string) => {
    localStorage.setItem(TOKEN_KEY, t);
    localStorage.setItem(EMAIL_KEY, e);
    emit();
  };

  const login = useCallback(async (e: string, pw: string) => {
    const r = await authAPI.login(e, pw);
    save(r.access_token, r.email);
  }, []);

  const register = useCallback(async (e: string, pw: string) => {
    const r = await authAPI.register(e, pw);
    save(r.access_token, r.email);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
    emit();
  }, []);

  return { token, email, loggedIn: !!token, login, register, logout };
}
