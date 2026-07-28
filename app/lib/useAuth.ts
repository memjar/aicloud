import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export function useAuth() {
  const router = useRouter();

  useEffect(() => {
    const auth = typeof window !== 'undefined' ? localStorage.getItem('aicloud_auth') : null;

    if (!auth) {
      router.push('/login');
    }
  }, [router]);

  const logout = () => {
    localStorage.removeItem('aicloud_auth');
    router.push('/login');
  };

  const getUser = () => {
    if (typeof window === 'undefined') return null;
    const auth = localStorage.getItem('aicloud_auth');
    return auth ? JSON.parse(auth) : null;
  };

  return { logout, getUser };
}
