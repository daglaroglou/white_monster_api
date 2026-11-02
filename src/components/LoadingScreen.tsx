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
      setTimeout(() => setIsLoaded(true), 350);
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
          exit={{ opacity: 0, scale: 1.02 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            backgroundColor: 'var(--canvas-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            backdropFilter: 'blur(20px)',
          }}
        >
          <div style={{ position: 'relative', width: 110, height: 110 }}>
            {/* Ambient Glow */}
            <div
              style={{
                position: 'absolute',
                inset: -20,
                background: 'radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%)',
                filter: 'blur(16px)',
                pointerEvents: 'none'
              }}
            />

            {/* Silhouette (Background) */}
            <div style={{ position: 'absolute', inset: 0, opacity: 0.12, filter: 'grayscale(100%)' }}>
              <Image
                src="/white_monster_api/img/monster.png"
                alt="Loading..."
                fill
                style={{ objectFit: 'contain' }}
                priority
              />
            </div>
            
            {/* Filled Can (Liquid Fill Animation tied to real progress) */}
            <motion.div
              style={{
                position: 'absolute',
                inset: 0,
                clipPath: `inset(${100 - displayProgress}% 0 0 0)`,
                transition: 'clip-path 0.3s ease-out'
              }}
            >
              <Image
                src="/white_monster_api/img/monster.png"
                alt="Loading Fill"
                fill
                style={{ objectFit: 'contain' }}
                priority
              />
            </motion.div>
          </div>

          {/* Progress Bar & Counter */}
          <div style={{ marginTop: 28, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 120,
                height: 3,
                borderRadius: 3,
                backgroundColor: 'var(--border-subtle)',
                overflow: 'hidden',
                position: 'relative'
              }}
            >
              <motion.div
                style={{
                  height: '100%',
                  width: `${displayProgress}%`,
                  backgroundColor: 'var(--text-primary)',
                  borderRadius: 3,
                  transition: 'width 0.25s ease-out'
                }}
              />
            </div>
            <span
              style={{
                fontFamily: 'var(--font-geist-mono)',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: 500,
                letterSpacing: '0.08em'
              }}
            >
              {displayProgress}%
            </span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
