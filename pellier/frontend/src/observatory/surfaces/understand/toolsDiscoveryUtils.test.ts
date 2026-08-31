import { describe, expect, it } from 'vitest';
import type { Tool } from '../../types';
import {
  discoveryQueryForTool,
  filterTools,
} from './toolsDiscoveryUtils';

const sampleTools: Tool[] = [
  {
    numeral: 1,
    functionName: 'search_products',
    description: 'Semantic product search',
    status: 'shipped',
    mutationType: 'read',
    signature: 'def search_products(query: str) -> str',
    usedBy: ['search_agent'],
    invocationCount: 100,
    version: '1.0',
  },
  {
    numeral: 9,
    functionName: 'initiate_return',
    description: 'Process a customer return with audit',
    status: 'exercise',
    mutationType: 'write',
    signature: 'def initiate_return(order_id: str) -> str',
    usedBy: ['personalization_agent'],
    invocationCount: 0,
    version: '0.1',
  },
];

describe('toolsDiscoveryUtils', () => {
  it('filters by status and mutation type', () => {
    expect(filterTools(sampleTools, 'shipped')).toHaveLength(1);
    expect(filterTools(sampleTools, 'exercise')).toHaveLength(1);
    expect(filterTools(sampleTools, 'write')).toHaveLength(1);
    expect(filterTools(sampleTools, 'read')).toHaveLength(1);
  });

  it('builds preset discovery queries per tool', () => {
    expect(discoveryQueryForTool(sampleTools[0])).toContain('find products');
    expect(discoveryQueryForTool(sampleTools[1])).toContain('return');
  });
});
