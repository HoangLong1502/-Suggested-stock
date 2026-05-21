import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
import QueryProvider from '../components/QueryProvider';
import AppNavbar from '../components/layout/AppNavbar';

export const metadata: Metadata = {
  title: 'Bot Trading AI',
  description: 'Multi-agent Vietnamese stock analysis platform',
};

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return (
    <html lang="vi" className="min-h-full bg-[#08101e] text-slate-100 antialiased">
      <body className="min-h-screen bg-[#08101e] text-slate-100 antialiased">
        <QueryProvider>
          <AppNavbar />
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
