import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
import QueryProvider from '../components/QueryProvider';

export const metadata: Metadata = {
  title: 'Bot Trading AI',
  description: 'Multi-agent Vietnamese stock analysis platform',
};

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
