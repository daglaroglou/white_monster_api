export interface PriceHistoryPoint {
  timestamp: string;
  price: number;
}

export interface StoreData {
  name: string;
  price: number | null;
  available: boolean;
  is_discount?: boolean;
  history?: PriceHistoryPoint[];
}

export interface PriceData {
  last_updated: string;
  product: string;
  currency: string;
  description?: string;
  stores: Record<string, StoreData>;
  total?: {
    name: string;
    history: PriceHistoryPoint[];
  };
}

