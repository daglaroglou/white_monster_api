import React from 'react';
import { Storefront } from '@phosphor-icons/react';
import {
  SklavenitisIcon,
  MasoutisIcon,
  AbIcon,
  GalaxiasIcon,
  MymarketIcon,
  MarketinIcon,
  KritikosIcon,
  BazaarIcon,
  Store24hstoresIcon
} from './icons';

interface StoreIconProps {
  storeId: string;
  className?: string;
  size?: number | string;
}

export function StoreIcon({ storeId, className, size = 24 }: StoreIconProps) {
  switch (storeId) {
    case 'sklavenitis': return <SklavenitisIcon size={size} className={className} />;
    case 'masoutis': return <MasoutisIcon size={size} className={className} />;
    case 'ab': return <AbIcon size={size} className={className} />;
    case 'galaxias': return <GalaxiasIcon size={size} className={className} />;
    case 'mymarket': return <MymarketIcon size={size} className={className} />;
    case 'marketin': return <MarketinIcon size={size} className={className} />;
    case 'kritikos': return <KritikosIcon size={size} className={className} />;
    case 'bazaar': return <BazaarIcon size={size} className={className} />;
    case '24hr': return <Store24hstoresIcon size={size} className={className} />;
    default: return <Storefront size={size} className={className} weight="duotone" />;
  }
}
