/**
 * Global application wrapper for BU MET Autograder
 * Initializes providers, layouts, and global styles
 */

import React from 'react';
import Head from 'next/head';
import { CacheProvider } from '@emotion/react';
import { SessionProvider } from 'next-auth/react';
import createEmotionCache from '../utils/createEmotionCache';
import { ThemeProvider } from '../ThemeContext';
import Layout from '../components/Layout';
import { APP_CONFIG } from '../config';
import '../styles/globals.css';

// Client-side emotion cache
const clientSideEmotionCache = createEmotionCache();

export default function MyApp({
  Component,
  emotionCache = clientSideEmotionCache,
  pageProps: { session, ...pageProps },
}) {
  // Check if the current page should use the layout
  const getLayout = Component.getLayout || ((page) => <Layout>{page}</Layout>);

  // Pages that don't need the main layout (login, error pages, etc.)
  const noLayoutPages = ['login', '404', '500', 'terms', 'privacy'];
  const pathName = Component.displayName || '';
  const useLayout = !noLayoutPages.some(page => pathName.includes(page));

  return (
    <CacheProvider value={emotionCache}>
      <Head>
        <title>{APP_CONFIG.appName}</title>
        <meta name="viewport" content="initial-scale=1, width=device-width" />
        <meta name="description" content="AI-based autograding tool for BU MET courses" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <SessionProvider session={session}>
        <ThemeProvider>
          {useLayout ? getLayout(<Component {...pageProps} />) : <Component {...pageProps} />}
        </ThemeProvider>
      </SessionProvider>
    </CacheProvider>
  );
}