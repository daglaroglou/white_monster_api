'use client';

import { useProgress } from '@react-three/drei';
import { motion, AnimatePresence } from 'motion/react';
import { useEffect, useState } from 'react';
import Image from 'next/image';

export function LoadingScreen() {
  const { progress } = useProgress();
  const [mounted, setMounted] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [displayProgress, setDisplayProgress] = useState(0);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    setDisplayProgress((prev) => Math.max(prev, Math.round(progress)));
  }, [progress]);

  useEffect(() => {
    const handleSceneRendered = () => {
      setDisplayProgress(100);
      // Give it a brief moment to show 100% before fading out
      setTimeout(() => setIsLoaded(true), 400);
    };

    window.addEventListener('scene-rendered', handleSceneRendered);
    return () => window.removeEventListener('scene-rendered', handleSceneRendered);
  }, []);

  if (!mounted) return null;

  return (
    <AnimatePresence>
      {!isLoaded && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            backgroundColor: 'var(--canvas-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
          }}
        >
          <div style={{ position: 'relative', width: 100, height: 100 }}>
            {/* Empty Silhouette (Background) */}
            <div style={{ position: 'absolute', inset: 0, opacity: 0.15, filter: 'grayscale(100%)' }}>
              <Image
                src="/img/monster.png"
                alt="Loading..."
                fill
                style={{ objectFit: 'contain' }}
                priority
              />
            </div>
            
            {/* Filled Can (Liquid Fill Animation) */}
            <motion.div
              animate={{ clipPath: ['inset(100% 0 0 0)', 'inset(0% 0 0 0)', 'inset(100% 0 0 0)'] }}
              transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
              style={{ position: 'absolute', inset: 0 }}
            >
              <Image
                src="/img/monster.png"
                alt="Loading..."
                fill
                style={{ objectFit: 'contain' }}
                priority
              />
            </motion.div>
          </div>
          <div style={{
            marginTop: 24,
            fontFamily: 'var(--font-geist-mono)',
            color: 'var(--text-secondary)',
            fontSize: '14px',
            fontWeight: 500,
            letterSpacing: '0.05em'
          }}>
            {displayProgress}%
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
