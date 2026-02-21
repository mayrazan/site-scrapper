import { useQuery, queryOptions } from '@tanstack/react-query'

import { fetchWriteups, type WriteupFilters } from '../lib/api'

export const writeupsQueryOptions = (filters: WriteupFilters) =>
  queryOptions({
    queryKey: ['writeups', filters.source, filters.year, filters.month, filters.q],
    queryFn: () => fetchWriteups(filters),
  })

export function useWriteups(filters: WriteupFilters) {
  return useQuery(writeupsQueryOptions(filters))
}
