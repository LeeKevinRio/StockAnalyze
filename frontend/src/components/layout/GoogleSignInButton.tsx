'use client';

import { useEffect, useRef } from 'react';

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

/** Renders Google's official "Sign in with Google" button (GIS).
 *  Hidden when NEXT_PUBLIC_GOOGLE_CLIENT_ID is not configured. */
export function GoogleSignInButton({ onCredential }: { onCredential: (credential: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const cb = useRef(onCredential);
  cb.current = onCredential;

  useEffect(() => {
    if (!CLIENT_ID) return;

    function render() {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const g = (window as any).google;
      if (!g?.accounts?.id || !ref.current) return;
      g.accounts.id.initialize({
        client_id: CLIENT_ID,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        callback: (resp: any) => {
          if (resp?.credential) cb.current(resp.credential);
        },
      });
      g.accounts.id.renderButton(ref.current, {
        theme: 'filled_black',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        width: 300,
      });
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if ((window as any).google?.accounts?.id) {
      render();
      return;
    }
    const ID = 'gsi-client-script';
    let s = document.getElementById(ID) as HTMLScriptElement | null;
    if (!s) {
      s = document.createElement('script');
      s.src = 'https://accounts.google.com/gsi/client';
      s.async = true;
      s.defer = true;
      s.id = ID;
      document.head.appendChild(s);
    }
    s.addEventListener('load', render);
    return () => s?.removeEventListener('load', render);
  }, []);

  if (!CLIENT_ID) return null;
  return <div ref={ref} className="flex justify-center" />;
}

export const GOOGLE_ENABLED = !!CLIENT_ID;
