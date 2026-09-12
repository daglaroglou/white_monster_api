import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "White Monster Price Tracker",
  description: "Track Monster Energy Zero Ultra 500ml prices across 9 Greek supermarkets including Masoutis, AB, Sklavenitis, Kritikos, MyMarket, Galaxias, Bazaar, Market In, and 24hr Stores.",
  keywords: ["Monster Energy", "price tracker", "API", "Greece", "supermarkets", "Ultra Zero", "24hr Stores", "Masoutis", "Sklavenitis"],
  authors: [{ name: "daglaroglou" }],
  icons: {
    icon: "https://github.com/daglaroglou/white_monster_api/blob/main/img/logo.png?raw=true"
  },
  openGraph: {
    type: "website",
    title: "White Monster Price Tracker API",
    description: "Track White Monster Energy 500ml prices across 9 Greek supermarkets including 24hr Stores.",
    url: "https://dag.is-a.dev/",
    siteName: "White Monster Price Tracker",
    images: [{
      url: "https://dag.is-a.dev/img/logo.png"
    }]
  }
};

export const viewport: Viewport = {
  themeColor: "#000000",
};

const themeScript = `
  (function() {
    try {
      var localTheme = window.localStorage.getItem('theme');
      var isDark = localTheme === 'dark' || (!localTheme && window.matchMedia('(prefers-color-scheme: dark)').matches);
      if (isDark) {
        document.documentElement.classList.add('dark');
      }
    } catch (e) {}
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
