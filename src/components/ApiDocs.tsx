'use client';
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Copy, Check, TerminalWindow, BracketsCurly } from '@phosphor-icons/react';
import styles from './ApiDocs.module.css';

export function ApiDocs() {
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [activeTab, setActiveTab] = useState<'fetch' | 'python' | 'curl'>('fetch');

  const apiUrl = "https://dag.is-a.dev/prices.json";

  const handleCopy = () => {
    navigator.clipboard.writeText(apiUrl);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const codeSnippets = {
    fetch: (
      <>
        <span className={styles.method}>fetch</span>(<span className={styles.string}>'{apiUrl}'</span>)
        <br />
        {'  '}.<span className={styles.method}>then</span>(<span className={styles.variable}>response</span> =&gt; <span className={styles.variable}>response</span>.<span className={styles.method}>json</span>())
        <br />
        {'  '}.<span className={styles.method}>then</span>(<span className={styles.variable}>data</span> =&gt; <span className={styles.variable}>console</span>.<span className={styles.method}>log</span>(<span className={styles.variable}>data</span>));
      </>
    ),
    python: (
      <>
        <span className={styles.keyword}>import</span> requests
        <br />
        <span className={styles.variable}>response</span> = requests.<span className={styles.method}>get</span>(<span className={styles.string}>'{apiUrl}'</span>)
        <br />
        <span className={styles.variable}>prices</span> = <span className={styles.variable}>response</span>.<span className={styles.method}>json</span>()
      </>
    ),
    curl: (
      <>
        <span className={styles.keyword}>curl</span> <span className={styles.string}>{apiUrl}</span>
      </>
    )
  };

  return (
    <motion.div
      className={styles.apiContainer}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
    >
      <div className={styles.apiHeader}>
        <div className={styles.apiTitle}>
          <BracketsCurly size={20} weight="bold" />
          <h2>API Endpoint</h2>
        </div>
        <div className={styles.apiEndpointBox}>
          <span className={styles.methodText}>GET</span>
          <code className={styles.url}>{apiUrl}</code>
          <button className={styles.copyBtn} onClick={handleCopy} title="Copy URL">
            {copiedUrl ? <Check size={18} weight="bold" color="var(--success-color, #4ade80)" /> : <Copy size={18} />}
          </button>
        </div>
      </div>

      <div className={styles.apiContent}>
        <div className={styles.tabs}>
          {(['fetch', 'python', 'curl'] as const).map(tab => (
            <button
              key={tab}
              className={`${styles.tabBtn} ${activeTab === tab ? styles.activeTab : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'fetch' ? 'JavaScript' : tab === 'python' ? 'Python' : 'cURL'}
            </button>
          ))}
        </div>
        <div className={styles.codeBlock}>
          <TerminalWindow size={16} className={styles.codeIcon} />
          <pre>
            <code>{codeSnippets[activeTab]}</code>
          </pre>
        </div>
      </div>
    </motion.div>
  );
}
