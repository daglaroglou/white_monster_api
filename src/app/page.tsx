'use client';

import { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'motion/react';
import { Clock, Moon, Sun, Tag, Heart } from '@phosphor-icons/react';
import dynamic from 'next/dynamic';
const Scene = dynamic(() => import('@/components/Scene'), { ssr: false });
import { ApiDocs } from '@/components/ApiDocs';
import { StoreIcon } from '@/components/StoreIcon';
import { LoadingScreen } from '@/components/LoadingScreen';
import { DonateModal } from '@/components/DonateModal';
import { PriceData } from '@/types';
import priceDataRaw from '../../data/price_history.json';
import styles from './page.module.css';

const data = priceDataRaw as unknown as PriceData;

const springTransition = {
  type: 'spring' as const,
  damping: 26,
  stiffness: 280,
  mass: 0.8
};

  interface TooltipPayloadItem {
    value: number;
    payload: {
      time: string;
      price: number;
    };
  }

  interface CustomTooltipProps {
    active?: boolean;
    payload?: TooltipPayloadItem[];
  }

  const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
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
    const [bubbles, setBubbles] = useState<{ id: number; x: number; endX: number; delay: number; duration: number; size: number; scale: number; color: string }[]>([]);

    useEffect(() => {
      setIsDark(document.documentElement.classList.contains('dark'));
    }, []);

    useEffect(() => {
      if (isDark === null) return;
      if (isDark) {
        document.documentElement.classList.add('dark');
        try { localStorage.setItem('theme', 'dark'); } catch { }
      } else {
        document.documentElement.classList.remove('dark');
        try { localStorage.setItem('theme', 'light'); } catch { }
      }
    }, [isDark]);

    const toggle = () => {
      if (isAnimating || isDark === null) return;
      setIsAnimating(true);

      const nextDark = !isDark;
      const targetColor = nextDark ? '#0A0A0A' : '#FBFBFA';
      const newBubbles = [];

      // Wave 1: Little amount (teaser fizz)
      for (let i = 0; i < 12; i++) {
        const x = Math.random() * 100;
        newBubbles.push({
          id: i,
          x,
          endX: x + (Math.random() * 10 - 5),
          delay: Math.random() * 0.18,
          duration: 0.75 + Math.random() * 0.25,
          size: Math.random() * 30 + 15,
          scale: 2.5,
          color: targetColor
        });
      }

      // Wave 2: Medium amount
      for (let i = 0; i < 24; i++) {
        const x = Math.random() * 100;
        newBubbles.push({
          id: 12 + i,
          x,
          endX: x + (Math.random() * 10 - 5),
          delay: 0.18 + Math.random() * 0.18,
          duration: 0.75 + Math.random() * 0.25,
          size: Math.random() * 60 + 35,
          scale: 3,
          color: targetColor
        });
      }

      // Wave 3: Massive amount to cover full density
      for (let i = 0; i < 44; i++) {
        const x = Math.random() * 100;
        newBubbles.push({
          id: 36 + i,
          x,
          endX: x + (Math.random() * 10 - 5),
          delay: 0.35 + Math.random() * 0.2,
          duration: 0.8 + Math.random() * 0.25,
          size: Math.random() * 180 + 120, // Huge bubbles
          scale: 3.5, // 3.5x expansion ensures 100% viewport coverage
          color: targetColor
        });
      }

      setBubbles(newBubbles);

      // Swap the theme while they are fully on screen and covering it
      setTimeout(() => {
        setIsDark(!isDark);
      }, 780);

      // Clear out bubbles after they pass
      setTimeout(() => {
        setBubbles([]);
        setIsAnimating(false);
      }, 1500);
    };

    return (
      <>
        {bubbles.length > 0 && (
          <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 9999, overflow: 'hidden' }}>
            {bubbles.map(b => (
              <div
                key={b.id}
                className={styles.screenWipeBubble}
                style={{
                  left: `${b.x}vw`,
                  width: `${b.size}px`,
                  height: `${b.size}px`,
                  backgroundColor: b.color,
                  '--end-x': `${b.endX - b.x}vw`,
                  '--scale': b.scale,
                  animationDuration: `${b.duration}s`,
                  animationDelay: `${b.delay}s`,
                } as React.CSSProperties}
              />
            ))}
          </div>
        )}

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
          aria-label="Toggle theme"
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

        if (now.getUTCHours() === 8 && now.getUTCMinutes() < 5) {
          setIsRefreshing(true);
          return '';
        }

        setIsRefreshing(false);

        const nextUpdate = new Date();
        nextUpdate.setUTCHours(8, 0, 0, 0);

        if (now > nextUpdate) {
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
    const [isDonateOpen, setIsDonateOpen] = useState(false);

    const formatTimestamp = (isoTs: string) => {
      const dt = new Date(isoTs);
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

    // Calculate live market intelligence stats
    const activeStores = Object.entries(data?.stores || {}).filter(([_, s]) => {
      const latest = s.history && s.history.length > 0 ? s.history[s.history.length - 1] : null;
      return latest && latest.price !== null;
    });

    const activePrices = activeStores.map(([_, s]) => {
      const latest = s.history![s.history!.length - 1];
      return latest.price;
    });

    const lowestPrice = activePrices.length ? Math.min(...activePrices) : null;
    const lowestPriceStores = activeStores
      .filter(([_, s]) => s.history![s.history!.length - 1].price === lowestPrice)
      .map(([_, s]) => s.name);

    const currentAverage = activePrices.length
      ? Number((activePrices.reduce((a, b) => a + b, 0) / activePrices.length).toFixed(2))
      : null;

    return (
      <div className={styles.layout}>
        {data?.description && (
          <>
            <div className={styles.marqueeContainerLeft}>
              <div className={styles.marqueeTextVertical} suppressHydrationWarning>
                {data.description} &bull; {data.description} &bull; {data.description} &bull;
              </div>
            </div>
            <div className={styles.marqueeContainerRight}>
              <div className={styles.marqueeTextVertical} suppressHydrationWarning>
                {data.description} &bull; {data.description} &bull; {data.description} &bull;
              </div>
            </div>
          </>
        )}
        <LoadingScreen />
        <ThemeToggle />
        <div className={styles.bentoGrid}>

          {/* HERO CELL */}
          <motion.div
            className={`${styles.bentoCell} ${styles.heroCell}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springTransition, delay: 0.05 }}
          >
            <div className={styles.eyebrow} suppressHydrationWarning>
              <span className={styles.liveIndicator}>
                <span className={styles.liveDot} />
                <span className={styles.livePing} />
              </span>
              <span className={styles.liveText}>Live Tracker</span>
              <span className={styles.dotSeparator}>•</span>
              <Clock size={13} weight="bold" />
              <span>Updated {data?.last_updated ? formatTimestamp(data.last_updated) : 'Unknown'}</span>
            </div>

            <div className={styles.titleContainer}>
              <h1 className={styles.title}>Market<br />Pricing.</h1>
            </div>
            <p className={styles.subtext}>
              Real-time price intelligence for Monster Energy Ultra Zero 500ml across major Greek retail chains.
            </p>

            <div className={styles.heroStats}>
              <div className={styles.heroStatItem}>
                <span className={styles.heroStatLabel}>Lowest Price</span>
                <span className={styles.heroStatValue}>
                  {lowestPrice !== null ? `€${lowestPrice.toFixed(2)}` : 'N/A'}
                </span>
                {lowestPriceStores.length > 0 && (
                  <span className={styles.heroStatSub}>
                    {lowestPriceStores.slice(0, 2).join(', ')}
                  </span>
                )}
              </div>
              <div className={styles.heroStatDivider} />
              <div className={styles.heroStatItem}>
                <span className={styles.heroStatLabel}>Market Avg</span>
                <span className={styles.heroStatValue}>
                  {currentAverage !== null ? `€${currentAverage.toFixed(2)}` : 'N/A'}
                </span>
                <span className={styles.heroStatSub}>Active stores</span>
              </div>
              <div className={styles.heroStatDivider} />
              <div className={styles.heroStatItem}>
                <span className={styles.heroStatLabel}>Retailers</span>
                <span className={styles.heroStatValue}>
                  {activeStores.length}
                </span>
                <span className={styles.heroStatSub}>Tracked live</span>
              </div>
            </div>
          </motion.div>

          {/* 3D SCENE CELL */}
          <motion.div
            className={`${styles.bentoCell} ${styles.sceneCell}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springTransition, delay: 0.1 }}
          >
            <div className={styles.sceneBgLight} />
            <div className={styles.sceneBgDark} />
            <div className={styles.sceneWrapper}>
              <Scene />
            </div>
          </motion.div>

          {/* CHART CELL */}
          <motion.div
            className={`${styles.bentoCell} ${styles.chartCell}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springTransition, delay: 0.15 }}
          >
            <div className={styles.chartHeader}>
              <h2 className={styles.chartTitle}>30-Day Average</h2>
              <div className={styles.chartSubtitle}>€ / 500ml</div>
            </div>
            <div className={styles.chartContainer}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 15, right: 8, left: -15, bottom: 10 }}>
                  <defs>
                    <linearGradient id="mainChartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--text-primary)" stopOpacity={0.14} />
                      <stop offset="95%" stopColor="var(--text-primary)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
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
                  <Area
                    type="monotone"
                    dataKey="price"
                    stroke="var(--text-primary)"
                    strokeWidth={2.5}
                    fill="url(#mainChartGradient)"
                    dot={false}
                    activeDot={{ r: 5, fill: 'var(--text-primary)', stroke: 'var(--card-bg)', strokeWidth: 2.5 }}
                  />
                </AreaChart>
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
              halkiadakis: 'https://www.xalkiadakis.gr',
              bazaar: 'https://www.bazaar-online.gr',
              marketin: 'https://www.market-in.gr',
              synka: 'https://synka-sm.gr',
              "24hr": 'https://www.24hr.gr'
            };

            const latestRecord = store.history && store.history.length > 0 ? store.history[store.history.length - 1] : null;
            const price = latestRecord ? latestRecord.price : null;
            const available = price !== null;
            const isLowest = price !== null && lowestPrice !== null && price === lowestPrice;

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
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springTransition, delay: 0.12 + (idx * 0.035) }}
              >
                <div className={styles.storeHeader}>
                  <div className={styles.storeName}>
                    <a href={storeUrls[key] || '#'} target="_blank" rel="noopener noreferrer">
                      {store.name}
                    </a>
                  </div>
                  <StoreIcon storeId={key} size={32} className={styles.storeLogo} />
                </div>

                {storeChartData.length > 1 ? (
                  <div className={styles.storeChartContainer}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={storeChartData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                        <defs>
                          <linearGradient id={`sparkline-${key}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--text-primary)" stopOpacity={0.14} />
                            <stop offset="100%" stopColor="var(--text-primary)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <YAxis domain={[minT, maxT]} hide={true} />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }} />
                        <Area
                          type="monotone"
                          dataKey="price"
                          stroke="var(--text-primary)"
                          strokeWidth={1.8}
                          fill={`url(#sparkline-${key})`}
                          dot={false}
                          activeDot={{ r: 4, fill: 'var(--text-primary)', stroke: 'var(--card-bg)', strokeWidth: 2 }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className={styles.storeChartPlaceholder}>
                    <span>No historical trend</span>
                  </div>
                )}

                <div className={styles.priceRow}>
                  <div className={`${styles.storePrice} ${!available ? styles.unavailable : ''}`}>
                    {available ? `€${price?.toFixed(2)}` : 'N/A'}
                    {store.is_discount && <Tag className={styles.discountTag} weight="duotone" />}
                  </div>
                  {isLowest && <span className={styles.lowestPricePill}>Lowest</span>}
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
            <button
              type="button"
              className={styles.donateButton}
              onClick={() => setIsDonateOpen(true)}
              title="Support the project"
            >
              <Heart size={16} weight="fill" className={styles.donateHeart} />
              Donate
            </button>
            <span className={styles.footerDot}>•</span>
            <span>Designed & Built by <a href="https://dag.is-a.dev" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex' }}>daglaroglou</a></span>
            <span className={styles.footerDot}>•</span>
            <a href="mailto:contact@dag.is-a.dev">contact@dag.is-a.dev</a>
          </div>
          <div className={styles.footerRight}>
            <NextUpdateCountdown />
            <span className={styles.commitSha}>
              commit {process.env.NEXT_PUBLIC_COMMIT_SHA?.slice(0, 7) || 'dev'}
            </span>
          </div>
        </footer>

        <DonateModal isOpen={isDonateOpen} onClose={() => setIsDonateOpen(false)} />
      </div>
    );
  }
