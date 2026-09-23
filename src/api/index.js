import { api } from './client';
import { authApi } from './auth';
import { platformsApi } from './platforms';
import { assetsApi } from './assets';
import { portfolioApi } from './portfolio';
import { transactionsApi } from './transactions';
import { connectionsApi } from './connections';
import { importsApi } from './imports';
import { accountAggregatorApi } from './accountAggregator';

export {
  api,
  authApi,
  platformsApi,
  assetsApi,
  portfolioApi,
  transactionsApi,
  connectionsApi,
  importsApi,
  accountAggregatorApi,
};

// Canonical API aliases
export const platformApi = platformsApi;
export const assetApi = assetsApi;
export const transactionApi = transactionsApi;
export const connectionApi = connectionsApi;
export const importApi = importsApi;
export const aaApi = accountAggregatorApi;
