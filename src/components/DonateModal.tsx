'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Heart,
  X,
  ArrowSquareOut,
  Copy,
  Check,
  CurrencyCircleDollar
} from '@phosphor-icons/react';
import styles from './DonateModal.module.css';

interface DonateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DonateModal({ isOpen, onClose }: DonateModalProps) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className={styles.backdrop}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className={styles.modal}
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 15 }}
            transition={{ type: 'spring', duration: 0.35, bounce: 0 }}
            onClick={e => e.stopPropagation()}
          >
            <button
              className={styles.closeButton}
              onClick={onClose}
              aria-label="Close donation modal"
            >
              <X size={20} weight="bold" />
            </button>

            <div className={styles.header}>
              <div className={styles.iconWrapper}>
                <Heart size={24} weight="fill" />
              </div>
              <h2 className={styles.title}>Support White Monster</h2>
              <p className={styles.description}>
                Help keep the automated scrapers alive and support server costs for real-time Monster Energy tracking.
              </p>
            </div>

            <div className={styles.optionsList}>
              <a
                href="https://github.com/sponsors/daglaroglou"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.optionItem}
              >
                <div className={styles.optionLeft}>
                  <div className={styles.optionIcon}>
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                    </svg>
                  </div>
                  <div className={styles.optionDetails}>
                    <span className={styles.optionName}>GitHub Sponsors</span>
                    <span className={styles.optionSubtitle}>One-time or monthly sponsorship</span>
                  </div>
                </div>
                <ArrowSquareOut size={18} color="var(--text-secondary)" />
              </a>

              <a
                href="https://paypal.me/daglaroglou"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.optionItem}
              >
                <div className={styles.optionLeft}>
                  <div className={styles.optionIcon}>
                    <CurrencyCircleDollar size={20} weight="bold" />
                  </div>
                  <div className={styles.optionDetails}>
                    <span className={styles.optionName}>PayPal</span>
                    <span className={styles.optionSubtitle}>paypal.me/daglaroglou</span>
                  </div>
                </div>
                <ArrowSquareOut size={18} color="var(--text-secondary)" />
              </a>

              <a
                href="https://revolut.me/daglaroglouc"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.optionItem}
              >
                <div className={styles.optionLeft}>
                  <div className={styles.optionIcon}>
                    <span style={{ fontWeight: 800, fontSize: '15px' }}>R</span>
                  </div>
                  <div className={styles.optionDetails}>
                    <span className={styles.optionName}>Revolut</span>
                    <span className={styles.optionSubtitle}>revolut.me/daglaroglouc</span>
                  </div>
                </div>
                <ArrowSquareOut size={18} color="var(--text-secondary)" />
              </a>
            </div>

            <div className={styles.cryptoSection}>
              <div className={styles.cryptoTitle}>Crypto Addresses</div>
              <div className={styles.cryptoRow}>
                <span className={styles.cryptoLabel}>BTC</span>
                <span className={styles.cryptoAddress} title="bc1qp62x7ehcvddyf6yw4ye5dy9uw8hllxhah3u447">
                  bc1qp62x7ehcvddyf6yw4ye5dy9uw8hllxhah3u447
                </span>
                <button
                  className={styles.copyButton}
                  onClick={() => copyToClipboard('bc1qp62x7ehcvddyf6yw4ye5dy9uw8hllxhah3u447', 'btc')}
                  title="Copy BTC address"
                >
                  {copiedKey === 'btc' ? (
                    <Check size={16} weight="bold" color="#4ade80" />
                  ) : (
                    <Copy size={16} />
                  )}
                </button>
              </div>

              <div className={styles.cryptoRow}>
                <span className={styles.cryptoLabel}>ETH</span>
                <span className={styles.cryptoAddress} title="0xcD6782ADccb748ae13a08fd2A237dABE97Df0074">
                  0xcD6782ADccb748ae13a08fd2A237dABE97Df0074
                </span>
                <button
                  className={styles.copyButton}
                  onClick={() => copyToClipboard('0xcD6782ADccb748ae13a08fd2A237dABE97Df0074', 'eth')}
                  title="Copy ETH address"
                >
                  {copiedKey === 'eth' ? (
                    <Check size={16} weight="bold" color="#4ade80" />
                  ) : (
                    <Copy size={16} />
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

