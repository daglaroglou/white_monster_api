'use client';

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion, AnimatePresence } from 'motion/react';
import { Storefront, Clock, MapPin, Moon, Sun } from '@phosphor-icons/react';
import dynamic from 'next/dynamic';
const Scene = dynamic(() => import('@/components/Scene'), { ssr: false });
import { ApiDocs } from '@/components/ApiDocs';
import { StoreIcon } from '@/components/StoreIcon';
import priceDataRaw from '../../price_history.json';
import styles from './page.module.css';

interface StoreData {
  name: string;
  price: number | null;
  available: boolean;
  history?: { timestamp: string; price: number }[];
}

interface PriceData {
  last_updated: string;
  product: string;
  currency: string;
  stores: Record<string, StoreData>;
  total?: { name: string; history: { timestamp: string; price: number }[] };
}

const data = priceDataRaw as unknown as PriceData;

const spring = { type: 'spring' as const, bounce: 0, duration: 0.7 };

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className={styles.tooltip}>
        <div className={styles.tooltipLabel}>{payload[0].payload.time}</div>
        <div className={styles.tooltipValue}>€{payload[0].value.toFixed(2)}</div>
      </div>
    );
  }
  return null;
};

function ThemeToggle() {
  const [isDark, setIsDark] = useState<boolean | null>(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [bubbles, setBubbles] = useState<{ id: number, x: number, delay: number, duration: number, size: number, color: string }[]>([]);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
  }, []);

  useEffect(() => {
    if (isDark === null) return;
    if (isDark) {
      document.documentElement.classList.add('dark');
      try { localStorage.setItem('theme', 'dark'); } catch (e) { }
    } else {
      document.documentElement.classList.remove('dark');
      try { localStorage.setItem('theme', 'light'); } catch (e) { }
    }
  }, [isDark]);

  const toggle = () => {
    if (isAnimating || isDark === null) return;
    setIsAnimating(true);

    const nextDark = !isDark;
    const targetColor = nextDark ? '#0A0A0A' : '#FBFBFA';
    const newBubbles = [];

    // Wave 1: Little amount (teaser fizz)
    for (let i = 0; i < 20; i++) {
      newBubbles.push({
        id: Date.now() + i,
        x: Math.random() * 100,
        delay: Math.random() * 0.2,
        duration: 0.7 + Math.random() * 0.3,
        size: Math.random() * 30 + 10, // pixels
        color: targetColor
      });
    }

    // Wave 2: Medium amount
    for (let i = 0; i < 50; i++) {
      newBubbles.push({
        id: Date.now() + 100 + i,
        x: Math.random() * 100,
        delay: 0.2 + Math.random() * 0.2,
        duration: 0.7 + Math.random() * 0.3,
        size: Math.random() * 60 + 30, // pixels
        color: targetColor
      });
    }

    // Wave 3: Massive amount to cover full density
    for (let i = 0; i < 150; i++) {
      newBubbles.push({
        id: Date.now() + 300 + i,
        x: Math.random() * 100,
        delay: 0.4 + Math.random() * 0.2,
        duration: 0.8 + Math.random() * 0.3,
        size: Math.random() * 150 + 100, // Huge pixels to completely paint screen
        color: targetColor
      });
    }

    setBubbles(newBubbles);

    // Swap the theme while they are fully on screen and covering it
    setTimeout(() => {
      setIsDark(!isDark);
    }, 800);

    // Clear out bubbles after they pass
    setTimeout(() => {
      setBubbles([]);
      setIsAnimating(false);
    }, 1600);
  };

  return (
    <>
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 9999, overflow: 'hidden' }}>
        <AnimatePresence>
          {bubbles.map(b => (
            <motion.div
              key={b.id}
              initial={{ y: '120vh', x: `${b.x}vw`, scale: 0.5, opacity: 1 }}
              animate={{ y: '-50vh', x: `${b.x + (Math.random() * 10 - 5)}vw`, scale: 3, opacity: 1 }}
              exit={{ opacity: 0, scale: 0 }}
              transition={{ duration: b.duration, delay: b.delay, ease: "easeIn" }}
              style={{
                position: 'absolute',
                width: `${b.size}px`,
                height: `${b.size}px`,
                borderRadius: '50%',
                backgroundColor: b.color,
              }}
            />
          ))}
        </AnimatePresence>
      </div>

      <motion.button
        onClick={toggle}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '56px',
          height: '56px',
          borderRadius: '28px',
          backgroundColor: 'var(--text-primary)',
          color: 'var(--canvas-bg)',
          border: 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          zIndex: 10000,
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
        }}
      >
        {isDark ? <Sun size={24} weight="fill" /> : <Moon size={24} weight="fill" />}
      </motion.button>
    </>
  );
}

const GithubSpinner = () => (
  <svg className={styles.spinner} viewBox="0 0 16 16" width="14" height="14" fill="currentColor">
    <path fillRule="evenodd" clipRule="evenodd" d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8z" opacity="0.25" />
    <path fillRule="evenodd" clipRule="evenodd" d="M8 0a8 8 0 0 1 8 8h-1.5a6.5 6.5 0 0 0-6.5-6.5V0z" />
  </svg>
);

function NextUpdateCountdown() {
  const [timeLeft, setTimeLeft] = useState<string>('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    const calculateTimeLeft = () => {
      const now = new Date();

      // The update runs at 8:00 AM UTC. 
      // We give it a 5-minute window to scrape, commit, and deploy.
      if (now.getUTCHours() === 8 && now.getUTCMinutes() < 5) {
        setIsRefreshing(true);
        return '';
      }

      setIsRefreshing(false);

      const nextUpdate = new Date();
      nextUpdate.setUTCHours(8, 0, 0, 0); // Updates run at 8:00 AM UTC (11 AM Greek Summer Time)

      if (now > nextUpdate) {
        // If it's already past 8 AM UTC today, next update is tomorrow
        nextUpdate.setUTCDate(nextUpdate.getUTCDate() + 1);
      }

      const diffMs = nextUpdate.getTime() - now.getTime();
      const hours = Math.floor(diffMs / (1000 * 60 * 60));
      const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const secs = Math.floor((diffMs % (1000 * 60)) / 1000);

      const parts = [];
      if (hours > 0) parts.push(`${hours}h`);
      if (mins > 0) parts.push(`${mins}m`);
      if (secs > 0 || (hours === 0 && mins === 0)) parts.push(`${secs}s`);

      return parts.join(' ');
    };

    setTimeLeft(calculateTimeLeft());
    const interval = setInterval(() => setTimeLeft(calculateTimeLeft()), 1000);
    return () => clearInterval(interval);
  }, []);

  if (!timeLeft && !isRefreshing) return null;

  return (
    <span className={`${styles.nextUpdate} ${isRefreshing ? styles.refreshing : ''}`}>
      {isRefreshing ? (
        <>
          <GithubSpinner />
          Refreshing & building...
        </>
      ) : (
        <>
          <Clock size={14} weight="bold" />
          Next update in {timeLeft}
        </>
      )}
    </span>
  );
}

export default function Home() {

  const formatTimestamp = (isoTs: string) => {
    // Basic manual formatting to prevent hydration mismatch
    const dt = new Date(isoTs);
    // Approximate Europe/Athens (UTC+2 or UTC+3). For safety, we just use UTC for UI consistency across clients
    const day = dt.getUTCDate().toString().padStart(2, '0');
    const month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][dt.getUTCMonth()];
    const hours = dt.getUTCHours().toString().padStart(2, '0');
    const minutes = dt.getUTCMinutes().toString().padStart(2, '0');
    return `${day} ${month}, ${hours}:${minutes} UTC`;
  };

  const formatShortDate = (isoTs: string) => {
    const dt = new Date(isoTs);
    const day = dt.getUTCDate().toString();
    const month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][dt.getUTCMonth()];
    return `${day} ${month}`;
  };

  const chartData = data?.total?.history?.map(pt => ({
    time: formatTimestamp(pt.timestamp),
    date: formatShortDate(pt.timestamp),
    price: pt.price
  })) || [];

  const prices = chartData.map(d => d.price);
  const minPrice = prices.length ? Math.min(...prices) : 0;
  const maxPrice = prices.length ? Math.max(...prices) : 0;

  const minTick = Math.floor(minPrice * 10) / 10;
  const maxTick = Math.ceil(maxPrice * 10) / 10;
  const yTicks = [];
  if (prices.length > 0) {
    for (let t = minTick; t <= maxTick + 0.01; t += 0.1) {
      yTicks.push(Number(t.toFixed(1)));
    }
  }

  return (
    <div className={styles.layout}>
      <ThemeToggle />
      <div className={styles.bentoGrid}>

        {/* HERO CELL */}
        <motion.div
          className={`${styles.bentoCell} ${styles.heroCell}`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.1 }}
        >
          <div className={styles.eyebrow} suppressHydrationWarning>
            <Clock size={14} weight="bold" />
            Updated {data?.last_updated ? formatTimestamp(data.last_updated) : 'Unknown'}
          </div>
          <div className={styles.titleContainer}>
            <h1 className={styles.title}>Market<br />Pricing.</h1>
          </div>
          <p className={styles.subtext}>
            Live pricing data for Monster Energy Ultra Zero across major Greek retailers.
          </p>
        </motion.div>

        {/* 3D SCENE CELL */}
        <motion.div
          className={`${styles.bentoCell} ${styles.sceneCell}`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.2 }}
        >
          {/* Subtle radial background to give depth without harsh borders */}
          <div className={styles.sceneBgLight} />
          <div className={styles.sceneBgDark} />
          <div className={styles.sceneWrapper}>
            <Scene />
          </div>
        </motion.div>

        {/* CHART CELL */}
        <motion.div
          className={`${styles.bentoCell} ${styles.chartCell}`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.3 }}
        >
          <div className={styles.chartHeader}>
            <h2 className={styles.chartTitle}>30-Day Average</h2>
            <div className={styles.chartSubtitle}>€ / 500ml</div>
          </div>
          <div className={styles.chartContainer}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 20, right: 10, left: 0, bottom: 20 }}>
                <XAxis
                  dataKey="date"
                  stroke="var(--border-strong)"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--border-strong)', strokeWidth: 1 }}
                  minTickGap={30}
                  dy={10}
                />
                <YAxis
                  domain={[minTick, maxTick]}
                  ticks={yTicks}
                  stroke="transparent"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                  tickFormatter={(value) => value.toFixed(2)}
                  width={40}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--border-strong)', strokeWidth: 1 }}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }} />
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="var(--text-primary)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: 'var(--text-primary)', stroke: 'var(--card-bg)', strokeWidth: 2 }}
                  animationDuration={1500}
                  animationEasing="ease-out"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* API DOCS */}
        <ApiDocs />

        {/* STORE CELLS */}
        {Object.entries(data?.stores || {}).map(([key, store], idx) => {
          const storeUrls: Record<string, string> = {
            masoutis: 'https://www.masoutis.gr',
            ab: 'https://www.ab.gr',
            sklavenitis: 'https://www.sklavenitis.gr',
            kritikos: 'https://kritikos-sm.gr',
            mymarket: 'https://www.mymarket.gr',
            galaxias: 'https://galaxias.shop',
            bazaar: 'https://www.bazaar-online.gr',
            marketin: 'https://www.market-in.gr',
            "24hr": 'https://www.24hr.gr'
          };

          const latestRecord = store.history && store.history.length > 0 ? store.history[store.history.length - 1] : null;
          const price = latestRecord ? latestRecord.price : null;
          const available = price !== null;

          const storeChartData = (store.history || []).map(pt => ({
            time: formatTimestamp(pt.timestamp),
            date: formatShortDate(pt.timestamp),
            price: pt.price
          }));

          const storePrices = storeChartData.map(d => d.price);
          const minP = storePrices.length ? Math.min(...storePrices) : 0;
          const maxP = storePrices.length ? Math.max(...storePrices) : 0;
          const minT = Math.floor(minP * 10) / 10;
          const maxT = Math.ceil(maxP * 10) / 10;

          return (
            <motion.div
              key={key}
              className={`${styles.bentoCell} ${styles.storeCell}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...spring, delay: 0.4 + (idx * 0.1) }}
            >
              <div className={styles.storeHeader}>
                <div className={styles.storeName}>
                  <a href={storeUrls[key] || '#'} target="_blank" rel="noopener noreferrer">
                    {store.name}
                  </a>
                </div>
                <StoreIcon storeId={key} size={32} className={styles.storeLogo} />
              </div>

              {storeChartData.length > 1 && (
                <div className={styles.storeChartContainer}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={storeChartData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                      <YAxis domain={[minT, maxT]} hide={true} />
                      <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }} />
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke="var(--text-primary)"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: 'var(--text-primary)', stroke: 'var(--card-bg)', strokeWidth: 2 }}
                        animationDuration={1500}
                        animationEasing="ease-out"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className={`${styles.storePrice} ${!available ? styles.unavailable : ''}`}>
                {available ? `€${price?.toFixed(2)}` : 'N/A'}
              </div>
            </motion.div>
          );
        })}

      </div>

      {/* FOOTER */}
      <footer className={styles.footer}>
        <div className={styles.footerLeft}>
          <a href="https://github.com/daglaroglou/white_monster_api" target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
            GitHub Repository
          </a>
          <span className={styles.footerDot}>•</span>
          <span>Designed & Built by <a href="https://dag.is-a.dev" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex' }}>daglaroglou</a></span>
        </div>
        <div className={styles.footerRight}>
          <NextUpdateCountdown />
          <span className={styles.commitSha}>
            commit {process.env.NEXT_PUBLIC_COMMIT_SHA || 'dev'}
          </span>
        </div>
      </footer>
    </div>
  );
}
